#!/usr/bin/env python3
"""Verify the complete rusty_v8 release before generating trusted pin files.

The input is the recursive download-artifact directory containing 14 release
pairs. Generated pins must be kept outside that directory so the input remains
an exact set of 42 files. Only the Python standard library is required.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


SANDBOX_PROFILE = "ptrcomp_sandbox_release"
ARCHITECTURES = ("aarch64", "x86_64")
UNIX_PLATFORMS = ("apple-darwin", "unknown-linux-gnu", "unknown-linux-musl")


class VerificationError(ValueError):
    """The downloaded files do not constitute the expected release."""


@dataclass(frozen=True)
class ReleasePair:
    profile: str
    target: str

    @property
    def archive(self) -> str:
        if self.target.endswith("-pc-windows-msvc"):
            return f"rusty_v8_{self.profile}_{self.target}.lib.gz"
        return f"librusty_v8_{self.profile}_{self.target}.a.gz"

    @property
    def binding(self) -> str:
        return f"src_binding_{self.profile}_{self.target}.rs"

    @property
    def manifest(self) -> str:
        return f"rusty_v8_{self.profile}_{self.target}.sha256"


def expected_pairs() -> list[ReleasePair]:
    pairs = [
        ReleasePair(profile, f"{arch}-{platform}")
        for arch in ARCHITECTURES
        for platform in UNIX_PLATFORMS
        for profile in ("release", SANDBOX_PROFILE)
    ]
    pairs.extend(
        ReleasePair(SANDBOX_PROFILE, f"{arch}-pc-windows-msvc")
        for arch in ARCHITECTURES
    )
    return pairs


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release_files(dist: Path, expected: set[str]) -> dict[str, Path]:
    if not dist.is_dir():
        raise VerificationError(f"release directory does not exist: {dist}")

    files: dict[str, Path] = {}
    for path in sorted(dist.rglob("*")):
        if path.is_symlink():
            raise VerificationError(f"symbolic links are not allowed: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise VerificationError(f"release asset must be a regular file: {path}")
        if path.name in files:
            raise VerificationError(
                f"duplicate asset basename {path.name}: {files[path.name]}, {path}"
            )
        files[path.name] = path

    missing = sorted(expected - files.keys())
    extra = sorted(files.keys() - expected)
    problems = []
    if missing:
        problems.append("missing release assets: " + ", ".join(missing))
    if extra:
        problems.append("unexpected release assets: " + ", ".join(extra))
    if problems:
        raise VerificationError("; ".join(problems))
    return files


def verify_pair(pair: ReleasePair, files: dict[str, Path]) -> dict[str, str]:
    manifest_bytes = files[pair.manifest].read_bytes()
    try:
        lines = manifest_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise VerificationError(f"{pair.manifest}: invalid UTF-8") from error
    if len(lines) != 2:
        raise VerificationError(f"{pair.manifest}: expected exactly two checksum lines")

    entries: dict[str, str] = {}
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if match is None:
            raise VerificationError(f"{pair.manifest}: invalid checksum line: {line!r}")
        digest, name = match.groups()
        if name in entries or name not in {pair.archive, pair.binding}:
            raise VerificationError(
                f"{pair.manifest}: must list exactly {pair.archive} and {pair.binding}"
            )
        entries[name] = digest

    verified = {}
    for name in (pair.archive, pair.binding):
        actual = sha256_file(files[name])
        if entries[name] != actual:
            raise VerificationError(
                f"{pair.manifest}: checksum mismatch for {name}: "
                f"expected {entries[name]}, got {actual}"
            )
        verified[name] = actual
    verified[pair.manifest] = hashlib.sha256(manifest_bytes).hexdigest()
    return verified


def bazel_artifact_sources() -> list[tuple[str, str]]:
    # Preserve the names/order in third_party/v8/rusty_v8_<version>.sha256.
    # Windows http_file keeps the release downloaded_file_path alias while
    # fetching the ptrcomp_sandbox_release archive from the release URL.
    sources = []
    for arch in ARCHITECTURES:
        target = f"{arch}-pc-windows-msvc"
        sources.append(
            (
                f"rusty_v8_release_{target}.lib.gz",
                ReleasePair(SANDBOX_PROFILE, target).archive,
            )
        )
    for arch in ARCHITECTURES:
        for platform in ("apple-darwin", "unknown-linux-gnu"):
            pair = ReleasePair(SANDBOX_PROFILE, f"{arch}-{platform}")
            sources.extend(((pair.archive, pair.archive), (pair.binding, pair.binding)))
    return sources


def verify_release(dist: Path, output_dir: Path, version: str) -> list[Path]:
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version) is None:
        raise VerificationError("version must have the form MAJOR.MINOR.PATCH")
    dist = dist.resolve()
    output_dir = output_dir.resolve()
    if output_dir == dist or dist in output_dir.parents:
        raise VerificationError("--output-dir must be outside --dist")

    pairs = expected_pairs()
    expected = {
        name for pair in pairs for name in (pair.archive, pair.binding, pair.manifest)
    }
    files = release_files(dist, expected)
    verified: dict[str, str] = {}
    for pair in pairs:
        verified.update(verify_pair(pair, files))

    # Generate pins only after every pair has passed verification, including
    # release-profile and musl files that have no current Bazel http_file pin.
    prefix = f"rusty_v8_{version.replace('.', '_')}"
    aggregate = output_dir / f"{prefix}_release_manifests.sha256"
    bazel_pins = output_dir / f"{prefix}.sha256"
    sandbox_manifests = sorted(
        pair.manifest for pair in pairs if pair.profile == SANDBOX_PROFILE
    )
    aggregate_text = "".join(
        f"{verified[name]}  {name}\n" for name in sandbox_manifests
    )
    bazel_text = "".join(
        f"{verified[source]}  {name}\n" for name, source in bazel_artifact_sources()
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate.write_text(aggregate_text, encoding="utf-8", newline="\n")
    bazel_pins.write_text(bazel_text, encoding="utf-8", newline="\n")
    return [aggregate, bazel_pins]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dist",
        type=Path,
        required=True,
        help="recursive downloaded release artifact directory",
    )
    parser.add_argument(
        "--version", required=True, help="release version, e.g. 150.4.0"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="trusted pin output directory, outside --dist",
    )
    args = parser.parse_args()
    try:
        pins = verify_release(args.dist, args.output_dir, args.version)
    except (OSError, VerificationError) as error:
        parser.exit(1, f"error: {error}\n")
    print("Verified 14 release pairs (42 assets). Wrote trusted pins:")
    for path in pins:
        print(path)


if __name__ == "__main__":
    main()
