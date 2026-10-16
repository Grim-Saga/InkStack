#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT = Path(__file__).with_name("verify_rusty_v8_release.py")
SANDBOX = "ptrcomp_sandbox_release"
UNIX_TARGETS = (
    "aarch64-apple-darwin",
    "aarch64-unknown-linux-gnu",
    "aarch64-unknown-linux-musl",
    "x86_64-apple-darwin",
    "x86_64-unknown-linux-gnu",
    "x86_64-unknown-linux-musl",
)
WINDOWS_TARGETS = ("aarch64-pc-windows-msvc", "x86_64-pc-windows-msvc")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class VerifyRustyV8ReleaseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dist = Path(self.temp.name) / "dist"
        self.output = Path(self.temp.name) / "trusted-pins"
        self.assets: dict[str, Path] = {}
        pairs = [
            (profile, target)
            for target in UNIX_TARGETS
            for profile in ("release", SANDBOX)
        ]
        pairs.extend((SANDBOX, target) for target in WINDOWS_TARGETS)
        for index, (profile, target) in enumerate(pairs):
            folder = self.dist / f"artifact-{index}" / "nested"
            folder.mkdir(parents=True)
            archive = (
                f"rusty_v8_{profile}_{target}.lib.gz"
                if target in WINDOWS_TARGETS
                else f"librusty_v8_{profile}_{target}.a.gz"
            )
            binding = f"src_binding_{profile}_{target}.rs"
            manifest = f"rusty_v8_{profile}_{target}.sha256"
            lines = []
            for name in (archive, binding):
                data = f"fixture bytes for {name}\n".encode()
                path = folder / name
                path.write_bytes(data)
                self.assets[name] = path
                lines.append(f"{digest(data)}  {name}\n")
            path = folder / manifest
            path.write_text("".join(lines), encoding="utf-8")
            self.assets[manifest] = path

    def run_verifier(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--dist",
                str(self.dist),
                "--version",
                "150.4.0",
                "--output-dir",
                str(self.output),
                *args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_rejected(self, expected_message: str) -> None:
        result = self.run_verifier()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(expected_message, result.stderr)
        self.assertFalse(self.output.exists(), "invalid inputs must not write pins")

    def test_recursive_release_emits_verified_sandbox_and_bazel_pins(self) -> None:
        result = self.run_verifier()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("14 release pairs (42 assets)", result.stdout)
        aggregate = self.output / "rusty_v8_150_4_0_release_manifests.sha256"
        expected_manifests = sorted(
            f"rusty_v8_{SANDBOX}_{target}.sha256"
            for target in (*UNIX_TARGETS, *WINDOWS_TARGETS)
        )
        self.assertEqual(
            aggregate.read_text(),
            "".join(
                f"{digest(self.assets[name].read_bytes())}  {name}\n"
                for name in expected_manifests
            ),
        )

        # Windows http_file downloaded_file_path deliberately keeps the release
        # alias while its downloaded bytes come from a sandbox release archive.
        expected_aliases = [
            (
                "rusty_v8_release_aarch64-pc-windows-msvc.lib.gz",
                "rusty_v8_ptrcomp_sandbox_release_aarch64-pc-windows-msvc.lib.gz",
            ),
            (
                "rusty_v8_release_x86_64-pc-windows-msvc.lib.gz",
                "rusty_v8_ptrcomp_sandbox_release_x86_64-pc-windows-msvc.lib.gz",
            ),
        ]
        for target in (
            "aarch64-apple-darwin",
            "aarch64-unknown-linux-gnu",
            "x86_64-apple-darwin",
            "x86_64-unknown-linux-gnu",
        ):
            for name in (
                f"librusty_v8_{SANDBOX}_{target}.a.gz",
                f"src_binding_{SANDBOX}_{target}.rs",
            ):
                expected_aliases.append((name, name))
        self.assertEqual(
            (self.output / "rusty_v8_150_4_0.sha256").read_text(),
            "".join(
                f"{digest(self.assets[source].read_bytes())}  {alias}\n"
                for alias, source in expected_aliases
            ),
        )
        self.assertEqual(len(list(self.output.iterdir())), 2)
        self.assertEqual(len(list(self.dist.rglob("*.*"))), 42)
        # Keeping generated pins separate permits verification of the same
        # downloaded release again without exemptions from the exact file set.
        self.assertEqual(self.run_verifier().returncode, 0)

    def test_missing_asset_is_rejected(self) -> None:
        self.assets["librusty_v8_release_x86_64-unknown-linux-musl.a.gz"].unlink()
        self.assert_rejected("missing release assets")

    def test_extra_asset_is_rejected(self) -> None:
        (self.dist / "unexpected.txt").write_text("extra")
        self.assert_rejected("unexpected release assets")

    def test_duplicate_basename_in_another_artifact_is_rejected(self) -> None:
        original = self.assets["src_binding_release_aarch64-apple-darwin.rs"]
        (self.dist / original.name).write_bytes(original.read_bytes())
        self.assert_rejected("duplicate asset basename")

    def test_windows_release_archive_cannot_replace_sandbox_archive(self) -> None:
        original = self.assets[
            "rusty_v8_ptrcomp_sandbox_release_aarch64-pc-windows-msvc.lib.gz"
        ]
        original.rename(
            original.with_name("rusty_v8_release_aarch64-pc-windows-msvc.lib.gz")
        )
        self.assert_rejected("missing release assets")

    def test_tampered_archive_or_binding_is_rejected(self) -> None:
        for name in (
            "librusty_v8_release_aarch64-unknown-linux-musl.a.gz",
            "src_binding_ptrcomp_sandbox_release_x86_64-pc-windows-msvc.rs",
        ):
            with self.subTest(name=name):
                original = self.assets[name].read_bytes()
                self.assets[name].write_bytes(original + b"tampered")
                self.assert_rejected("checksum mismatch")
                self.assets[name].write_bytes(original)

    def test_each_manifest_must_have_exactly_two_lines(self) -> None:
        manifest = self.assets["rusty_v8_release_aarch64-unknown-linux-musl.sha256"]
        original = manifest.read_text()
        for content in (original.splitlines(keepends=True)[0], original + "\n"):
            with self.subTest(content=content):
                manifest.write_text(content)
                self.assert_rejected("exactly two checksum lines")

    def test_manifest_must_name_its_own_archive_and_binding_once(self) -> None:
        manifest = self.assets["rusty_v8_release_aarch64-apple-darwin.sha256"]
        original = manifest.read_text()
        first, second = original.splitlines(keepends=True)
        for content in (
            first + first,
            original.replace(
                "src_binding_release_aarch64-apple-darwin.rs",
                "../src_binding_release_aarch64-apple-darwin.rs",
            ),
            original.replace(
                "src_binding_release_aarch64-apple-darwin.rs",
                "src_binding_release_x86_64-apple-darwin.rs",
            ),
        ):
            with self.subTest(content=content):
                manifest.write_text(content)
                self.assert_rejected("must list exactly")

    def test_manifest_digest_must_be_sha256_hex(self) -> None:
        manifest = self.assets["rusty_v8_release_aarch64-apple-darwin.sha256"]
        manifest.write_text("z" + manifest.read_text()[1:])
        self.assert_rejected("invalid checksum line")

    def test_symlink_assets_and_directories_are_rejected(self) -> None:
        link = self.dist / "linked-artifact"
        link.symlink_to(
            self.assets["src_binding_release_aarch64-apple-darwin.rs"].parent,
            target_is_directory=True,
        )
        self.assert_rejected("symbolic links are not allowed")

    def test_output_must_be_outside_the_release_tree(self) -> None:
        for output in (self.dist, self.dist / "pins"):
            with self.subTest(output=output):
                result = self.run_verifier("--output-dir", str(output))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("outside --dist", result.stderr)
        self.assertFalse((self.dist / "pins").exists())

    def test_version_cannot_escape_the_output_directory(self) -> None:
        result = self.run_verifier("--version", "../150.4.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("version must have the form", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
