import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codex_package import v8
from codex_package.targets import TARGET_SPECS, TargetSpec


class FetchInkStackV8ArtifactsTest(unittest.TestCase):
    version = "150.4.0"

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    @contextmanager
    def release(
        self,
        target: str,
        *,
        line_ending: bytes = b"\n",
        trusted_digest: str | None = None,
        trusted_name: str | None = None,
        create_pins: bool = True,
    ) -> Iterator[tuple[TargetSpec, MagicMock, str]]:
        spec = TARGET_SPECS[target]
        profile = v8.V8_ARTIFACT_PROFILE
        archive_name = (
            f"rusty_v8_{profile}_{target}.lib.gz"
            if spec.is_windows
            else f"librusty_v8_{profile}_{target}.a.gz"
        )
        binding_name = f"src_binding_{profile}_{target}.rs"
        manifest_name = f"rusty_v8_{profile}_{target}.sha256"
        archive = b"trusted V8 archive"
        binding = b"trusted V8 binding"
        manifest = (
            line_ending.join(
                (
                    f"{hashlib.sha256(archive).hexdigest()}  {archive_name}".encode(),
                    f"{hashlib.sha256(binding).hexdigest()}  {binding_name}".encode(),
                )
            )
            + line_ending
        )
        payloads = {
            manifest_name: manifest,
            archive_name: archive,
            binding_name: binding,
        }

        if create_pins:
            pins = (
                self.root / "third_party/v8/rusty_v8_150_4_0_release_manifests.sha256"
            )
            pins.parent.mkdir(parents=True)
            digest = trusted_digest or hashlib.sha256(manifest).hexdigest()
            name = trusted_name or manifest_name
            pins.write_bytes(f"{digest}  {name}".encode() + line_ending)

        def download(_url: str, destination: Path) -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payloads[destination.name])

        with (
            patch.object(v8, "REPO_ROOT", self.root),
            patch.object(v8, "download_file", side_effect=download) as download_file,
        ):
            yield spec, download_file, manifest_name

    def test_fetches_artifacts_after_authenticating_manifest(self) -> None:
        with self.release("x86_64-unknown-linux-gnu") as (
            spec,
            download,
            manifest_name,
        ):
            artifacts = v8.fetch_inkstack_v8_artifacts(
                spec, version=self.version, cache_root=self.root / "cache"
            )

            self.assertEqual(artifacts.archive.read_bytes(), b"trusted V8 archive")
            self.assertEqual(artifacts.binding.read_bytes(), b"trusted V8 binding")
            self.assertEqual(download.call_args_list[0].args[1].name, manifest_name)
            self.assertEqual(download.call_count, 3)
            for call in download.call_args_list:
                self.assertEqual(
                    call.args[0],
                    "https://github.com/Grim-Saga/InkStack/releases/download/"
                    f"rusty-v8-v150.4.0/{call.args[1].name}",
                )

    def test_authenticates_windows_manifest_with_crlf(self) -> None:
        with self.release("x86_64-pc-windows-msvc", line_ending=b"\r\n") as (
            spec,
            download,
            _manifest_name,
        ):
            artifacts = v8.fetch_inkstack_v8_artifacts(
                spec, version=self.version, cache_root=self.root / "cache"
            )

            self.assertEqual(artifacts.archive.read_bytes(), b"trusted V8 archive")
            self.assertEqual(artifacts.binding.read_bytes(), b"trusted V8 binding")
            self.assertEqual(download.call_count, 3)

    def test_rejects_tampered_manifest_before_downloading_artifacts(self) -> None:
        with self.release("x86_64-unknown-linux-gnu", trusted_digest="0" * 64) as (
            spec,
            download,
            manifest_name,
        ):
            with self.assertRaisesRegex(
                RuntimeError, "does not match its trusted SHA-256"
            ):
                v8.fetch_inkstack_v8_artifacts(
                    spec, version=self.version, cache_root=self.root / "cache"
                )

            download.assert_called_once()
            self.assertEqual(download.call_args.args[1].name, manifest_name)

    def test_rejects_missing_manifest_pin_before_downloading_artifacts(self) -> None:
        with self.release(
            "x86_64-unknown-linux-gnu", trusted_name="another-target.sha256"
        ) as (spec, download, manifest_name):
            with self.assertRaisesRegex(RuntimeError, "has no trusted SHA-256"):
                v8.fetch_inkstack_v8_artifacts(
                    spec, version=self.version, cache_root=self.root / "cache"
                )

            download.assert_called_once()
            self.assertEqual(download.call_args.args[1].name, manifest_name)

    def test_rejects_missing_pin_file_before_downloading_artifacts(self) -> None:
        with self.release("x86_64-unknown-linux-gnu", create_pins=False) as (
            spec,
            download,
            manifest_name,
        ):
            with self.assertRaises(FileNotFoundError):
                v8.fetch_inkstack_v8_artifacts(
                    spec, version=self.version, cache_root=self.root / "cache"
                )

            download.assert_called_once()
            self.assertEqual(download.call_args.args[1].name, manifest_name)

    def test_verified_cache_needs_no_network(self) -> None:
        with self.release("x86_64-unknown-linux-gnu") as (spec, download, _):
            first = v8.fetch_inkstack_v8_artifacts(
                spec, version=self.version, cache_root=self.root / "cache"
            )
            download.reset_mock()
            download.side_effect = AssertionError("unexpected network request")

            second = v8.fetch_inkstack_v8_artifacts(
                spec, version=self.version, cache_root=self.root / "cache"
            )
            self.assertEqual(second, first)
            download.assert_not_called()

    def test_missing_or_corrupt_manifest_refresh_retains_valid_artifacts(self) -> None:
        with self.release("x86_64-unknown-linux-gnu") as (spec, download, name):
            artifacts = v8.fetch_inkstack_v8_artifacts(
                spec, version=self.version, cache_root=self.root / "cache"
            )
            manifest = artifacts.archive.parent / name
            expected = manifest.read_bytes()
            for contents in (None, b"corrupt"):
                with self.subTest(contents=contents):
                    if contents is None:
                        manifest.unlink()
                    else:
                        manifest.write_bytes(contents)
                    download.reset_mock()
                    refreshed = v8.fetch_inkstack_v8_artifacts(
                        spec, version=self.version, cache_root=self.root / "cache"
                    )
                    self.assertEqual(refreshed, artifacts)
                    self.assertEqual(manifest.read_bytes(), expected)
                    download.assert_called_once()
                    self.assertEqual(download.call_args.args[1], manifest)

    def test_cached_manifest_still_authenticates_both_artifacts(self) -> None:
        with self.release("x86_64-unknown-linux-gnu") as (spec, download, _):
            artifacts = v8.fetch_inkstack_v8_artifacts(
                spec, version=self.version, cache_root=self.root / "cache"
            )
            artifacts.archive.write_bytes(b"corrupt archive")
            artifacts.binding.write_bytes(b"corrupt binding")
            download.reset_mock()
            repaired = v8.fetch_inkstack_v8_artifacts(
                spec, version=self.version, cache_root=self.root / "cache"
            )
            self.assertEqual(repaired, artifacts)
            self.assertEqual(
                (repaired.archive.read_bytes(), repaired.binding.read_bytes()),
                (b"trusted V8 archive", b"trusted V8 binding"),
            )
            self.assertEqual(
                [call.args[1] for call in download.call_args_list],
                [artifacts.archive, artifacts.binding],
            )

    def test_changed_repository_pin_rejects_old_cache_and_bad_refresh(self) -> None:
        with self.release("x86_64-unknown-linux-gnu") as (spec, download, name):
            artifacts = v8.fetch_inkstack_v8_artifacts(
                spec, version=self.version, cache_root=self.root / "cache"
            )
            pins = (
                self.root / "third_party/v8/rusty_v8_150_4_0_release_manifests.sha256"
            )
            pins.write_text(f"{'0' * 64}  {name}\n")
            download.reset_mock()
            with self.assertRaisesRegex(
                RuntimeError, "does not match its trusted SHA-256"
            ):
                v8.fetch_inkstack_v8_artifacts(
                    spec, version=self.version, cache_root=self.root / "cache"
                )
            download.assert_called_once()
            self.assertEqual(
                download.call_args.args[1], artifacts.archive.parent / name
            )
            self.assertFalse((artifacts.archive.parent / name).exists())
            self.assertEqual(artifacts.archive.read_bytes(), b"trusted V8 archive")
            self.assertEqual(artifacts.binding.read_bytes(), b"trusted V8 binding")

    @unittest.skipIf(sys.platform == "win32", "requires unprivileged symlinks")
    def test_symlink_manifest_is_replaced_without_writing_through_link(self) -> None:
        actual_download = v8.download_file
        with self.release("x86_64-unknown-linux-gnu") as (spec, download, name):
            artifacts = v8.fetch_inkstack_v8_artifacts(
                spec, version=self.version, cache_root=self.root / "cache"
            )
            manifest = artifacts.archive.parent / name
            expected = manifest.read_bytes()
            backing = manifest.with_suffix(".original")
            manifest.rename(backing)
            manifest.symlink_to(backing)
            download.reset_mock()
            download.side_effect = actual_download

            def gh_download(command, **_kwargs):
                destination = Path(command[command.index("--dir") + 1])
                (destination / manifest.name).write_bytes(expected)

            with patch("subprocess.run", side_effect=gh_download):
                refreshed = v8.fetch_inkstack_v8_artifacts(
                    spec, version=self.version, cache_root=self.root / "cache"
                )
            self.assertEqual(refreshed, artifacts)
            self.assertFalse(manifest.is_symlink())
            self.assertEqual(
                (manifest.read_bytes(), backing.read_bytes()), (expected, expected)
            )
            download.assert_called_once()

    def test_interrupted_refresh_preserves_cache(self) -> None:
        actual_download = v8.download_file

        with self.release("x86_64-unknown-linux-gnu") as (spec, download, name):
            artifacts = v8.fetch_inkstack_v8_artifacts(
                spec, version=self.version, cache_root=self.root / "cache"
            )
            manifest = artifacts.archive.parent / name
            manifest.write_bytes(b"stale manifest")
            download.reset_mock()
            download.side_effect = actual_download

            def interrupted_download(command, **_kwargs):
                destination = Path(command[command.index("--dir") + 1])
                (destination / manifest.name).write_bytes(b"partial")
                raise subprocess.CalledProcessError(1, command)

            with (
                patch("subprocess.run", side_effect=interrupted_download),
                self.assertRaises(subprocess.CalledProcessError),
            ):
                v8.fetch_inkstack_v8_artifacts(
                    spec, version=self.version, cache_root=self.root / "cache"
                )
            self.assertEqual(manifest.read_bytes(), b"stale manifest")
            self.assertEqual(artifacts.archive.read_bytes(), b"trusted V8 archive")
            self.assertEqual(artifacts.binding.read_bytes(), b"trusted V8 binding")
            self.assertFalse(list(manifest.parent.glob("*.tmp")))

    def test_source_and_paired_overrides_do_not_touch_cache(self) -> None:
        spec = TARGET_SPECS["x86_64-unknown-linux-gnu"]
        for environ in (
            {"V8_FROM_SOURCE": "1"},
            {
                "RUSTY_V8_ARCHIVE": "archive.a",
                "RUSTY_V8_SRC_BINDING_PATH": "binding.rs",
            },
        ):
            with (
                self.subTest(environ=environ),
                patch.object(
                    v8,
                    "fetch_inkstack_v8_artifacts",
                    side_effect=AssertionError("unexpected fetch"),
                ) as fetch,
            ):
                self.assertEqual(
                    v8.resolve_inkstack_v8_cargo_env(spec, environ=environ), {}
                )
                fetch.assert_not_called()


class DownloadPrivateV8ArtifactTest(unittest.TestCase):
    url = (
        "https://github.com/Grim-Saga/InkStack/releases/download/"
        "rusty-v8-v150.4.0/"
        "librusty_v8_ptrcomp_sandbox_release_x86_64-unknown-linux-gnu.a.gz"
    )
    filename = "librusty_v8_ptrcomp_sandbox_release_x86_64-unknown-linux-gnu.a.gz"

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.destination = self.root / "cache" / self.filename
        self.destination.parent.mkdir()
        self.destination.write_bytes(b"existing cached bytes")
        # On the old implementation this guard produces a red result without
        # allowing an unauthenticated real request to escape the test process.
        unauthenticated = patch.object(
            v8,
            "urlopen",
            create=True,
            side_effect=AssertionError("V8 download must authenticate with gh"),
        )
        unauthenticated.start()
        self.addCleanup(unauthenticated.stop)

    def test_authenticated_fetch_uses_fixed_repo_and_atomically_replaces_cache(
        self,
    ) -> None:
        staged_directories = []

        def gh_download(command, **kwargs):
            self.assertEqual(
                command[:8],
                [
                    "gh",
                    "release",
                    "download",
                    "rusty-v8-v150.4.0",
                    "--repo",
                    "Grim-Saga/InkStack",
                    "--pattern",
                    self.filename,
                ],
            )
            self.assertEqual(command[8], "--dir")
            self.assertEqual(len(command), 10)
            self.assertEqual(kwargs, {"check": True, "timeout": 120})
            self.assertEqual(os.environ["GH_TOKEN"], "test-github-token")
            self.assertEqual(self.destination.read_bytes(), b"existing cached bytes")
            staging = Path(command[9])
            self.assertEqual(staging.parent, self.destination.parent)
            (staging / self.filename).write_bytes(b"authenticated download bytes")
            staged_directories.append(staging)

        with (
            patch.dict(os.environ, {"GH_TOKEN": "test-github-token"}),
            patch("subprocess.run", side_effect=gh_download),
        ):
            v8.download_file(self.url, self.destination)
        self.assertEqual(self.destination.read_bytes(), b"authenticated download bytes")
        self.assertEqual(len(staged_directories), 1)
        self.assertFalse(staged_directories[0].exists())
        self.assertEqual(list(self.destination.parent.iterdir()), [self.destination])

    def test_failed_authenticated_download_preserves_cache_and_removes_partial_file(
        self,
    ) -> None:
        def failed_download(command, **_kwargs):
            staging = Path(command[command.index("--dir") + 1])
            (staging / self.filename).write_bytes(b"partial failed download")
            raise subprocess.CalledProcessError(1, command)

        with (
            patch("subprocess.run", side_effect=failed_download),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            v8.download_file(self.url, self.destination)
        self.assertEqual(self.destination.read_bytes(), b"existing cached bytes")
        self.assertEqual(list(self.destination.parent.iterdir()), [self.destination])

    def test_missing_gh_or_timeout_preserves_cache(self) -> None:
        for error in (
            FileNotFoundError("gh"),
            subprocess.TimeoutExpired(["gh"], timeout=120),
        ):
            with (
                self.subTest(error=error),
                patch("subprocess.run", side_effect=error),
                self.assertRaises(type(error)),
            ):
                v8.download_file(self.url, self.destination)
            self.assertEqual(self.destination.read_bytes(), b"existing cached bytes")
            self.assertEqual(
                list(self.destination.parent.iterdir()), [self.destination]
            )

    def test_rejects_untrusted_repositories_and_nonliteral_asset_patterns(self) -> None:
        for url in (
            self.url.replace("Grim-Saga/InkStack", "openai/codex"),
            self.url.replace(self.filename, "../../archive.gz"),
            self.url.replace(self.filename, "*.a.gz"),
            self.url + "?download=1",
            self.url + "#fragment",
        ):
            with (
                self.subTest(url=url),
                patch("subprocess.run") as download,
                self.assertRaisesRegex(ValueError, "trusted V8 release URL"),
            ):
                v8.download_file(url, self.destination)
            download.assert_not_called()
        self.assertEqual(self.destination.read_bytes(), b"existing cached bytes")


if __name__ == "__main__":
    unittest.main()
