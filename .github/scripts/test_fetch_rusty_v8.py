#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPT = Path(__file__).with_name("fetch_rusty_v8.py")
PROFILE = "ptrcomp_sandbox_release"


class FetchRustyV8Test(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "checkout"
        self.cache = Path(self.temp.name) / "cache root"
        self.github_env = Path(self.temp.name) / "github-env"
        (self.root / "inkstack-rs").mkdir(parents=True)
        (self.root / "inkstack-rs/Cargo.lock").write_text(
            'version = 4\n[[package]]\nname = "v8"\nversion = "150.4.0"\n',
            encoding="utf-8",
        )

    def stage_cached_pair(self, target: str) -> tuple[Path, Path]:
        directory = self.cache / f"rusty-v8-150.4.0-{target}"
        directory.mkdir(parents=True)
        archive_name = (
            f"rusty_v8_{PROFILE}_{target}.lib.gz"
            if target.endswith("-pc-windows-msvc")
            else f"librusty_v8_{PROFILE}_{target}.a.gz"
        )
        archive = directory / archive_name
        binding = directory / f"src_binding_{PROFILE}_{target}.rs"
        archive.write_bytes(b"fixture archive bytes")
        binding.write_bytes(b"// fixture binding\n")
        manifest = directory / f"rusty_v8_{PROFILE}_{target}.sha256"
        manifest.write_text(
            "".join(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
                for path in (archive, binding)
            ),
            encoding="utf-8",
        )
        pins = self.root / "third_party/v8"
        pins.mkdir(parents=True, exist_ok=True)
        (pins / "rusty_v8_150_4_0_release_manifests.sha256").write_text(
            f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  {manifest.name}\n",
            encoding="utf-8",
        )
        return archive, binding

    def run_helper(
        self, *args: str, machine: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["INKSTACK_REPO_ROOT"] = str(self.root)
        # A fully verified cache must work without any GitHub credentials.
        env.pop("GH_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)
        command = [sys.executable, str(SCRIPT), *args]
        if machine is not None:
            code = """
import runpy
import sys
from unittest.mock import patch

helper = sys.argv.pop(1)
machine = sys.argv.pop(1)
with patch('platform.machine', return_value=machine):
    runpy.run_path(helper, run_name='__main__')
"""
            command = [sys.executable, "-c", code, str(SCRIPT), machine, *args]
        return subprocess.run(
            command,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_cli_emits_verified_pair_and_distdir_with_space_in_cache_path(self) -> None:
        for target in ("x86_64-unknown-linux-gnu", "aarch64-pc-windows-msvc"):
            with self.subTest(target=target):
                archive, binding = self.stage_cached_pair(target)
                self.github_env.write_text("EXISTING=value\n", encoding="utf-8")
                result = self.run_helper(
                    "--target",
                    target,
                    "--cache-root",
                    str(self.cache),
                    "--github-env",
                    str(self.github_env),
                    "--bazel",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(self.github_env.exists(), result.stdout)
                self.assertEqual(
                    self.github_env.read_text(),
                    "EXISTING=value\n"
                    f"RUSTY_V8_ARCHIVE={archive}\n"
                    f"RUSTY_V8_SRC_BINDING_PATH={binding}\n"
                    f"BAZEL_DISTDIR={archive.parent}\n",
                )

    def test_bazel_source_platforms_do_not_fetch_or_export_artifacts(self) -> None:
        for target in (
            "x86_64-unknown-linux-musl",
            "aarch64-unknown-linux-musl",
        ):
            with self.subTest(target=target):
                result = self.run_helper(
                    "--target",
                    target,
                    "--cache-root",
                    str(self.cache),
                    "--github-env",
                    str(self.github_env),
                    "--bazel",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("source", result.stdout)
                self.assertFalse(self.cache.exists())
                self.assertFalse(self.github_env.exists())

    def test_bazel_os_labels_prefetch_the_native_architecture_pair(self) -> None:
        for label, machine, target in (
            ("Linux", "AMD64", "x86_64-unknown-linux-gnu"),
            ("Linux", "aarch64", "aarch64-unknown-linux-gnu"),
            ("macOS", "x86_64", "x86_64-apple-darwin"),
            ("macOS", "ARM64", "aarch64-apple-darwin"),
            ("Windows", "AMD64", "x86_64-pc-windows-msvc"),
            ("Windows", "arm64", "aarch64-pc-windows-msvc"),
        ):
            with self.subTest(label=label, machine=machine):
                archive, binding = self.stage_cached_pair(target)
                self.github_env.unlink(missing_ok=True)
                result = self.run_helper(
                    "--target",
                    label,
                    "--cache-root",
                    str(self.cache),
                    "--github-env",
                    str(self.github_env),
                    "--bazel",
                    machine=machine,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(self.github_env.exists(), result.stdout)
                self.assertEqual(
                    self.github_env.read_text(),
                    f"RUSTY_V8_ARCHIVE={archive}\n"
                    f"RUSTY_V8_SRC_BINDING_PATH={binding}\n"
                    f"BAZEL_DISTDIR={archive.parent}\n",
                )

    def test_bazel_os_label_rejects_unknown_architecture_before_export(self) -> None:
        result = self.run_helper(
            "--target",
            "Linux",
            "--cache-root",
            str(self.cache),
            "--github-env",
            str(self.github_env),
            "--bazel",
            machine="riscv64",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported host architecture", result.stderr)
        self.assertIn("riscv64", result.stderr)
        self.assertFalse(self.cache.exists())
        self.assertFalse(self.github_env.exists())

    def test_bazel_gnullvm_prefetches_msvc_native_fallback_pair(self) -> None:
        for arch in ("x86_64", "aarch64"):
            with self.subTest(arch=arch):
                archive, binding = self.stage_cached_pair(f"{arch}-pc-windows-msvc")
                self.github_env.unlink(missing_ok=True)
                result = self.run_helper(
                    "--target",
                    f"{arch}-pc-windows-gnullvm",
                    "--cache-root",
                    str(self.cache),
                    "--github-env",
                    str(self.github_env),
                    "--bazel",
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(self.github_env.exists(), result.stdout)
                self.assertEqual(
                    self.github_env.read_text(),
                    f"RUSTY_V8_ARCHIVE={archive}\n"
                    f"RUSTY_V8_SRC_BINDING_PATH={binding}\n"
                    f"BAZEL_DISTDIR={archive.parent}\n",
                )

    def test_cargo_musl_target_still_exports_the_verified_release(self) -> None:
        archive, binding = self.stage_cached_pair("aarch64-unknown-linux-musl")
        result = self.run_helper(
            "--target",
            "aarch64-unknown-linux-musl",
            "--cache-root",
            str(self.cache),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"RUSTY_V8_ARCHIVE={archive}", result.stdout)
        self.assertIn(f"RUSTY_V8_SRC_BINDING_PATH={binding}", result.stdout)

    def test_invalid_target_does_not_write_environment(self) -> None:
        result = self.run_helper(
            "--target",
            "typo-target",
            "--github-env",
            str(self.github_env),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported", result.stderr)
        self.assertFalse(self.github_env.exists())

    def test_invalid_manifest_never_exports_environment(self) -> None:
        archive, _binding = self.stage_cached_pair("x86_64-unknown-linux-gnu")
        manifest = (
            archive.parent / f"rusty_v8_{PROFILE}_x86_64-unknown-linux-gnu.sha256"
        )
        manifest.write_text(
            manifest.read_text().replace("src_binding_", "../src_binding_"),
            encoding="utf-8",
        )
        (
            self.root / "third_party/v8/rusty_v8_150_4_0_release_manifests.sha256"
        ).write_text(
            f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  {manifest.name}\n",
            encoding="utf-8",
        )
        result = self.run_helper(
            "--target",
            "x86_64-unknown-linux-gnu",
            "--cache-root",
            str(self.cache),
            "--github-env",
            str(self.github_env),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unexpected V8 checksum artifact", result.stderr)
        self.assertNotIn("RUSTY_V8_ARCHIVE=", result.stdout)
        self.assertFalse(self.github_env.exists())

    def test_help_works_without_repository_environment_or_downloads(self) -> None:
        env = os.environ.copy()
        env.pop("INKSTACK_REPO_ROOT", None)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--bazel", result.stdout)
        self.assertFalse(self.cache.exists())

    def test_download_timeout_fails_without_traceback_or_environment(self) -> None:
        code = """
import pathlib
import runpy
import subprocess
import sys
from unittest.mock import patch

helper = pathlib.Path(sys.argv.pop(1))
sys.path.insert(0, str(helper.parents[2] / 'scripts'))
with patch('inkstack_package.v8.fetch_inkstack_v8_artifacts',
           side_effect=subprocess.TimeoutExpired(['gh', 'release', 'download'], 120)):
    runpy.run_path(str(helper), run_name='__main__')
"""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                code,
                str(SCRIPT),
                "--target",
                "x86_64-unknown-linux-gnu",
                "--github-env",
                str(self.github_env),
            ],
            env={**os.environ, "INKSTACK_REPO_ROOT": str(self.root)},
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("timed out", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(self.github_env.exists())


if __name__ == "__main__":
    unittest.main()
