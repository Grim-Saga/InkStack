#!/usr/bin/env python3
"""Fetch a checksum-verified InkStack V8 pair for Cargo or Bazel consumers."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BAZEL_SOURCE_TARGETS = {
    "x86_64-unknown-linux-musl",
    "aarch64-unknown-linux-musl",
}
BAZEL_NATIVE_TARGET_SUFFIXES = {
    "Linux": "unknown-linux-gnu",
    "macOS": "apple-darwin",
    "Windows": "pc-windows-msvc",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Rust target triple")
    parser.add_argument(
        "--cache-root", type=Path, help="verified artifact cache directory"
    )
    parser.add_argument(
        "--github-env",
        type=Path,
        help="append overrides to this GitHub environment file",
    )
    parser.add_argument(
        "--bazel",
        action="store_true",
        help="skip platforms that Bazel builds from source",
    )
    args = parser.parse_args()

    target = args.target
    if args.bazel and target in BAZEL_NATIVE_TARGET_SUFFIXES:
        machine = platform.machine()
        arch = {
            "x86_64": "x86_64",
            "amd64": "x86_64",
            "aarch64": "aarch64",
            "arm64": "aarch64",
        }.get(machine.lower())
        if arch is None:
            parser.error(f"Unsupported host architecture for {target}: {machine}")
        target = f"{arch}-{BAZEL_NATIVE_TARGET_SUFFIXES[target]}"
    if args.bazel and target.endswith("-pc-windows-gnullvm"):
        # Keyless Windows CI falls back to a native MSVC build. Prefetch its
        # pair even when the requested keyed build normally uses source V8.
        target = target.removesuffix("-pc-windows-gnullvm") + "-pc-windows-msvc"
    if args.bazel and target in BAZEL_SOURCE_TARGETS:
        print(
            f"Bazel builds V8 from source for {args.target}; no release download needed."
        )
        return

    # Use the same downloader and trusted pins as local package builds. This
    # entry point also works before the package CLI has configured its root.
    sys.path.insert(0, str(ROOT / "scripts"))
    os.environ.setdefault("INKSTACK_REPO_ROOT", str(ROOT))
    from codex_package.targets import TARGET_SPECS
    from codex_package.v8 import fetch_inkstack_v8_artifacts

    spec = TARGET_SPECS.get(target)
    if spec is None:
        parser.error(f"Unsupported V8 release target: {args.target}")

    try:
        pair = fetch_inkstack_v8_artifacts(
            spec,
            cache_root=args.cache_root.resolve() if args.cache_root else None,
        )
        overrides = {
            "RUSTY_V8_ARCHIVE": str(pair.archive.resolve()),
            "RUSTY_V8_SRC_BINDING_PATH": str(pair.binding.resolve()),
            "BAZEL_DISTDIR": str(pair.archive.parent.resolve()),
        }
        text = "".join(f"{name}={value}\n" for name, value in overrides.items())
        if args.github_env:
            with args.github_env.open("a", encoding="utf-8", newline="\n") as output:
                output.write(text)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f"error: {error}\n")
    print(text, end="")


if __name__ == "__main__":
    main()
