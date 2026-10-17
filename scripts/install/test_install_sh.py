#!/usr/bin/env python3

"""Regression tests for the InkStack standalone installer release contract.

All network access is intercepted by a fake curl executable: every request
URL is recorded and every response is served from local fixtures. The
installer must only ever contact Grim-Saga/InkStack release infrastructure,
must never select a non-application release (such as the V8 dependency
release) for a "latest" request, and must verify every download against a
published SHA-256 digest.
"""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import textwrap
import unittest


INSTALL_SCRIPT = Path(__file__).with_name("install.sh")
PS_INSTALL_SCRIPT = Path(__file__).with_name("install.ps1")
VERSION = "0.142.5"
MISMATCH_VERSION = "0.145.0"
V8_RELEASE_TAG = "rusty-v8-v150.4.0"
API_BASE = "https://api.github.com/repos/Grim-Saga/InkStack"
DOWNLOAD_BASE = "https://github.com/Grim-Saga/InkStack/releases/download"

FORBIDDEN_DISTRIBUTION_REFERENCES = (
    "releases.openai.com",
    "openai/codex",
    "api.github.com/repos/openai",
)


class InstallShTest(unittest.TestCase):
    def test_explicit_release_resolves_from_inkstack_metadata(self) -> None:
        result, requests = run_installer(VERSION)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            requests,
            [
                f"{API_BASE}/releases/tags/rust-v{VERSION}",
                f"{DOWNLOAD_BASE}/rust-v{VERSION}/inkstack-package_SHA256SUMS",
            ],
        )
        self.assertIn(f"Resolved version: {VERSION}", result.stdout)
        assert_only_inkstack_urls(requests)

    def test_metadata_fetch_failure_is_not_reported_as_missing_assets(self) -> None:
        result, requests = run_installer(VERSION, api_failure=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(requests, [f"{API_BASE}/releases/tags/rust-v{VERSION}"])
        self.assertIn(
            f"Could not fetch GitHub release metadata for InkStack {VERSION}",
            result.stderr,
        )
        self.assertNotIn("does not provide the required release assets", result.stderr)

    def test_alpha_hotfix_release_is_valid(self) -> None:
        version = "0.145.0-alpha.23.1"
        result, requests = run_installer(
            version, metadata_json=release_metadata(version=version)
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            requests,
            [
                f"{API_BASE}/releases/tags/rust-v{version}",
                f"{DOWNLOAD_BASE}/rust-v{version}/inkstack-package_SHA256SUMS",
            ],
        )
        self.assertIn(f"Resolved version: {version}", result.stdout)

    def test_latest_scans_release_list_and_skips_v8_dependency_release(self) -> None:
        result, requests = run_installer(
            "latest",
            list_metadata_json=releases_list_json(
                v8_dependency_release(),
                application_release(),
            ),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            requests,
            [
                f"{API_BASE}/releases?per_page=100&page=1",
                f"{API_BASE}/releases/tags/rust-v{VERSION}",
                f"{DOWNLOAD_BASE}/rust-v{VERSION}/inkstack-package_SHA256SUMS",
            ],
        )
        self.assertIn(f"Resolved version: {VERSION}", result.stdout)
        assert_only_inkstack_urls(requests)
        self.assertNotIn(V8_RELEASE_TAG, " ".join(requests))

    def test_latest_fails_cleanly_without_application_releases(self) -> None:
        result, requests = run_installer(
            "latest",
            list_metadata_json=releases_list_json(v8_dependency_release()),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(requests, [f"{API_BASE}/releases?per_page=100&page=1"])
        self.assertIn(
            "No compatible InkStack application release is available",
            result.stderr,
        )
        self.assertNotIn("Downloading InkStack CLI", result.stdout)

    def test_latest_paginates_past_unrelated_releases(self) -> None:
        result, requests = run_installer(
            "latest",
            list_metadata_json=releases_list_json(
                *[v8_dependency_release() for _ in range(100)]
            ),
            list_metadata_json_page2=releases_list_json(application_release()),
        )

        self.assertIn(f"Resolved version: {VERSION}", result.stdout)
        self.assertEqual(
            requests[:2],
            [
                f"{API_BASE}/releases?per_page=100&page=1",
                f"{API_BASE}/releases?per_page=100&page=2",
            ],
        )
        assert_only_inkstack_urls(requests)

    def test_latest_with_empty_release_list_fails_cleanly(self) -> None:
        result, requests = run_installer("latest", list_metadata_json="[]")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(requests, [f"{API_BASE}/releases?per_page=100&page=1"])
        self.assertIn(
            "No compatible InkStack application release is available",
            result.stderr,
        )

    def test_application_release_missing_package_asset_is_rejected(self) -> None:
        metadata = json.loads(release_metadata())
        metadata["assets"] = [
            asset for asset in metadata["assets"] if ".tar.gz" not in asset["name"]
        ]
        result, requests = run_installer(
            VERSION, metadata_json=json.dumps(metadata)
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(requests, [f"{API_BASE}/releases/tags/rust-v{VERSION}"])
        self.assertIn("does not provide the required release assets", result.stderr)

    def test_metadata_tag_mismatch_is_rejected(self) -> None:
        result, requests = run_installer(
            VERSION, metadata_json=release_metadata(version=MISMATCH_VERSION)
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(requests, [f"{API_BASE}/releases/tags/rust-v{VERSION}"])
        self.assertIn(
            f"did not match requested InkStack version {VERSION}", result.stderr
        )

    def test_json_like_strings_and_nested_fields_do_not_define_assets(self) -> None:
        result, requests = run_installer(
            VERSION, metadata_json=release_metadata_with_decoys()
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(requests, [f"{API_BASE}/releases/tags/rust-v{VERSION}"])
        self.assertIn("does not provide the required release assets", result.stderr)

    def test_compact_metadata_is_independent_of_field_order(self) -> None:
        result, requests = run_installer(
            VERSION, metadata_json=release_metadata(compact=True, reorder=True)
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(
            requests,
            [
                f"{API_BASE}/releases/tags/rust-v{VERSION}",
                f"{DOWNLOAD_BASE}/rust-v{VERSION}/inkstack-package_SHA256SUMS",
            ],
        )
        self.assertIn(f"Resolved version: {VERSION}", result.stdout)

    def test_corrupt_archive_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path, checksum_path, metadata_json = create_package_release(root)

            result, requests = run_installer_in(
                root,
                VERSION,
                metadata_json=metadata_json,
                archive_path=archive_path,
                checksum_path=checksum_path,
                force_macos=True,
                corrupt_archive=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum did not match expected digest", result.stderr)
        self.assertNotIn("installed successfully", result.stdout)
        assert_only_inkstack_urls(requests)

    def test_wrong_checksum_manifest_digest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path, checksum_path, metadata_json = create_package_release(root)

            result, requests = run_installer_in(
                root,
                VERSION,
                metadata_json=release_metadata(),
                archive_path=archive_path,
                checksum_path=checksum_path,
                force_macos=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum did not match expected digest", result.stderr)
        self.assertNotIn("installed successfully", result.stdout)

    def test_incomplete_checksum_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path, checksum_path, metadata_json = create_package_release(
                root, manifest_lists_archive=False
            )

            result, requests = run_installer_in(
                root,
                VERSION,
                metadata_json=metadata_json,
                archive_path=archive_path,
                checksum_path=checksum_path,
                force_macos=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "Could not find SHA-256 digest for", result.stderr
        )
        self.assertIn("inkstack-package_SHA256SUMS", result.stderr)
        self.assertNotIn("installed successfully", result.stdout)

    def test_release_without_checksum_asset_is_rejected(self) -> None:
        metadata = json.loads(release_metadata())
        metadata["assets"] = [
            asset for asset in metadata["assets"] if "SHA256SUMS" not in asset["name"]
        ]
        result, _requests = run_installer(VERSION, metadata_json=json.dumps(metadata))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not provide the required release assets", result.stderr)

    def test_asset_download_failure_reports_missing_download(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path, checksum_path, metadata_json = create_package_release(root)

            result, requests = run_installer_in(
                root,
                VERSION,
                metadata_json=metadata_json,
                archive_path=archive_path,
                checksum_path=checksum_path,
                force_macos=True,
                asset_failure=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Could not download", result.stderr)
        assert_only_inkstack_urls(requests)

    def test_release_binary_reporting_wrong_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            # The release metadata advertises the requested version, but the
            # archive contains a binary reporting a different version.
            archive_path, checksum_path, metadata_json = create_package_release(
                root, metadata_version=MISMATCH_VERSION, binary_version=VERSION
            )

            result, requests = run_installer_in(
                root,
                MISMATCH_VERSION,
                metadata_json=metadata_json,
                archive_path=archive_path,
                checksum_path=checksum_path,
                force_macos=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            f"did not report expected version {MISMATCH_VERSION}", result.stderr
        )
        self.assertNotIn("installed successfully", result.stdout)

    def test_macos_install_exposes_code_mode_host_beside_inkstack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path, checksum_path, metadata_json = create_package_release(root)

            result, requests = run_installer_in(
                root,
                VERSION,
                metadata_json=metadata_json,
                archive_path=archive_path,
                checksum_path=checksum_path,
                force_macos=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            assert_only_inkstack_urls(requests)
            install_bin = root / "install-bin"
            current = root / "inkstack-home" / "packages" / "standalone" / "current"
            inkstack_path = install_bin / "inkstack"
            host_path = install_bin / "inkstack-code-mode-host"
            self.assertEqual(os.readlink(inkstack_path), str(current / "bin" / "inkstack"))
            self.assertEqual(
                os.readlink(host_path),
                str(current / "bin" / "inkstack-code-mode-host"),
            )
            self.assertTrue(os.access(host_path, os.X_OK))

    def test_reinstall_reuses_complete_offline_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path, checksum_path, metadata_json = create_package_release(root)
            options = dict(
                metadata_json=metadata_json,
                archive_path=archive_path,
                checksum_path=checksum_path,
                force_macos=True,
            )

            first, _first_requests = run_installer_in(root, VERSION, **options)
            self.assertEqual(first.returncode, 0, first.stderr)

            (root / "requests.log").unlink()
            second, second_requests = run_installer_in(root, VERSION, **options)

            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                second_requests,
                [f"{API_BASE}/releases/tags/rust-v{VERSION}"],
            )
            self.assertNotIn("Downloading InkStack CLI", second.stdout)

    def test_latest_installs_verified_package(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive_path, checksum_path, metadata_json = create_package_release(root)

            result, requests = run_installer_in(
                root,
                "latest",
                metadata_json=metadata_json,
                archive_path=archive_path,
                checksum_path=checksum_path,
                force_macos=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                requests,
                [
                    f"{API_BASE}/releases?per_page=100&page=1",
                    f"{API_BASE}/releases/tags/rust-v{VERSION}",
                    f"{DOWNLOAD_BASE}/rust-v{VERSION}/inkstack-package_SHA256SUMS",
                    f"{DOWNLOAD_BASE}/rust-v{VERSION}/"
                    f"inkstack-package-aarch64-apple-darwin.tar.gz",
                ],
            )

    def test_daemon_install_preserves_visible_cli_and_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            archive, checksum, metadata = create_package_release(root)
            options = dict(
                metadata_json=metadata,
                archive_path=archive,
                checksum_path=checksum,
                force_macos=True,
            )
            pinned, _ = run_installer_in(root, VERSION, **options)
            self.assertEqual(pinned.returncode, 0, pinned.stderr)
            visible = root / "install-bin/inkstack"
            original = visible.resolve()
            pending = visible.with_name(".inkstack.12345")
            pending.symlink_to(original)
            profile = root / "home/.profile"
            profile.write_text("unchanged profile\n")

            installed, _ = run_installer_in(root, "latest", daemon_only=True, **options)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            daemon = root / "inkstack-home/packages/app-server-daemon"
            release_name = f"{VERSION}-aarch64-apple-darwin"
            self.assertEqual(
                (daemon / "current").resolve(), daemon / "releases" / release_name
            )
            self.assertEqual((daemon / "auto-update-version").read_text(), release_name)
            history = daemon / "selection-history"
            original_history = history.read_bytes()
            self.assertEqual(history.read_text().splitlines()[:2], [release_name, ""])
            repeated, _ = run_installer_in(root, "latest", daemon_only=True, **options)
            self.assertEqual(repeated.returncode, 0, repeated.stderr)
            self.assertEqual(history.read_bytes(), original_history)
            options["daemon_only"] = True
            local = daemon / "releases/local-development"
            local.mkdir()
            (daemon / "current").unlink()
            (daemon / "current").symlink_to(local)
            marker = daemon / "auto-update-version"
            marker.unlink()

            scheduled, _ = run_installer_in(
                root, "latest", update_guard_from_release=local.name, **options
            )
            self.assertEqual(scheduled.returncode, 0, scheduled.stderr)
            self.assertEqual((daemon / "current").resolve(), local)
            self.assertFalse(marker.exists())

            raced, _ = run_installer_in(
                root,
                "latest",
                update_guard_from_release="a-different-release",
                manual_update=True,
                **options,
            )
            self.assertNotEqual(raced.returncode, 0, raced.stderr)
            self.assertEqual((daemon / "current").resolve(), local)
            self.assertFalse(marker.exists())

            binary = daemon / "releases" / release_name / "bin/inkstack"
            contents = binary.read_text()
            binary.write_text(
                '#!/bin/sh\n[ "$1" = "--version" ] || exit 2\n'
                f"echo inkstack-cli {VERSION}\n"
            )
            incompatible, _ = run_installer_in(
                root,
                "latest",
                update_guard_from_release=local.name,
                manual_update=True,
                **options,
            )
            self.assertNotEqual(incompatible.returncode, 0)
            self.assertIn("does not support daemon-owned packages", incompatible.stderr)
            self.assertEqual((daemon / "current").resolve(), local)
            self.assertFalse(marker.exists())
            binary.write_text(contents)

            restored, _ = run_installer_in(
                root,
                "latest",
                update_guard_from_release=local.name,
                manual_update=True,
                **options,
            )
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertEqual(
                (daemon / "current").resolve(), daemon / "releases" / release_name
            )
            self.assertEqual(marker.read_text(), release_name)
            self.assertEqual(visible.resolve(), original)
            self.assertTrue(pending.is_symlink())
            self.assertEqual(profile.read_text(), "unchanged profile\n")
            self.assertFalse(
                (root / "inkstack-home/packages/standalone/auto-update-version").exists()
            )

    def test_explicit_release_pins_even_the_current_latest_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive, checksum, metadata = create_package_release(root)
            options = dict(
                metadata_json=metadata,
                archive_path=archive,
                checksum_path=checksum,
                force_macos=True,
            )
            marker = root / "inkstack-home/packages/standalone/auto-update-version"
            latest, _ = run_installer_in(root, "latest", **options)
            self.assertEqual(latest.returncode, 0, latest.stderr)
            release_name = f"{VERSION}-aarch64-apple-darwin"
            self.assertEqual(marker.read_text(), release_name)

            pinned, _ = run_installer_in(root, VERSION, **options)
            self.assertEqual(pinned.returncode, 0, pinned.stderr)
            self.assertFalse(marker.exists())

            updater_record = (
                root / "inkstack-home/app-server-daemon/app-server-updater.pid"
            )
            updater_record.parent.mkdir(parents=True)
            updater_record.write_text(
                json.dumps(
                    {"pid": os.getpid(), "processStartTime": process_start_time()}
                )
            )
            old_updater, _ = run_installer_in(
                root, "latest", old_updater_parent_pid=os.getpid(), **options
            )
            self.assertEqual(old_updater.returncode, 0, old_updater.stderr)
            self.assertFalse(marker.exists())

            skipped, _ = run_installer_in(
                root, "latest", update_guard_from_release=release_name, **options
            )
            self.assertEqual(skipped.returncode, 0, skipped.stderr)
            self.assertFalse(marker.exists())

            updater_record.write_text(
                json.dumps({"pid": os.getpid(), "processStartTime": "stale"})
            )
            latest_again, _ = run_installer_in(
                root, "latest", old_updater_parent_pid=os.getpid(), **options
            )
            self.assertEqual(latest_again.returncode, 0, latest_again.stderr)
            self.assertEqual(marker.read_text(), release_name)

            managed = (
                root
                / f"inkstack-home/packages/standalone/releases/{release_name}/bin/inkstack"
            )
            managed.unlink()
            guarded, _ = run_installer_in(
                root,
                "latest",
                update_guard_from_release=release_name,
                **options,
            )
            self.assertEqual(guarded.returncode, 0, guarded.stderr)
            self.assertTrue(managed.exists())

    def test_uninspectable_legacy_updater_does_not_clear_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            archive, checksum, metadata = create_package_release(root)
            options = dict(
                metadata_json=metadata,
                archive_path=archive,
                checksum_path=checksum,
                force_macos=True,
            )
            pinned, _ = run_installer_in(root, VERSION, **options)
            self.assertEqual(pinned.returncode, 0, pinned.stderr)
            updater_record = (
                root / "inkstack-home/app-server-daemon/app-server-updater.pid"
            )
            updater_record.parent.mkdir(parents=True)
            updater_record.write_text(
                json.dumps(
                    {"pid": os.getpid(), "processStartTime": process_start_time()}
                )
            )

            attempted, _ = run_installer_in(
                root,
                "latest",
                old_updater_parent_pid=os.getpid(),
                fail_ps=True,
                **options,
            )
            self.assertEqual(attempted.returncode, 0, attempted.stderr)
            self.assertFalse(
                (root / "inkstack-home/packages/standalone/auto-update-version").exists()
            )

    def test_installer_scripts_never_reference_openai_distribution(self) -> None:
        for script in (INSTALL_SCRIPT, PS_INSTALL_SCRIPT):
            with self.subTest(script=script.name):
                text = script.read_text(encoding="utf-8")
                for reference in FORBIDDEN_DISTRIBUTION_REFERENCES:
                    self.assertNotIn(
                        reference,
                        text,
                        f"{script.name} must not reference {reference}",
                    )


def assert_only_inkstack_urls(requests: list[str]) -> None:
    for url in requests:
        if not url.startswith(f"{API_BASE}/") and not url.startswith(
            f"{DOWNLOAD_BASE}/"
        ):
            raise AssertionError(f"installer contacted a non-InkStack URL: {url}")


def run_installer(
    release: str,
    *,
    api_failure: bool = False,
    metadata_json: str | None = None,
    list_metadata_json: str | None = None,
    list_metadata_json_page2: str | None = None,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    with tempfile.TemporaryDirectory() as temp_dir:
        return run_installer_in(
            Path(temp_dir),
            release,
            api_failure=api_failure,
            metadata_json=metadata_json,
            list_metadata_json=list_metadata_json,
            list_metadata_json_page2=list_metadata_json_page2,
        )


def run_installer_in(
    root: Path,
    release: str,
    *,
    api_failure: bool = False,
    asset_failure: bool = False,
    corrupt_archive: bool = False,
    metadata_json: str | None = None,
    list_metadata_json: str | None = None,
    list_metadata_json_page2: str | None = None,
    archive_path: Path | None = None,
    checksum_path: Path | None = None,
    force_macos: bool = False,
    update_guard_from_release: str | None = None,
    old_updater_parent_pid: int | None = None,
    fail_ps: bool = False,
    daemon_only: bool = False,
    manual_update: bool = False,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = root / "bin"
    bin_dir.mkdir(exist_ok=True)
    request_log = root / "requests.log"
    fake_curl = bin_dir / "curl"
    fake_curl.write_text(
        textwrap.dedent(
            """\
            #!/bin/sh
            url=""
            output=""
            previous=""
            for arg in "$@"; do
              case "$arg" in
                https://*) url="$arg" ;;
              esac
              if [ "$previous" = "-o" ]; then
                output="$arg"
              fi
              previous="$arg"
            done
            printf '%s\\n' "$url" >>"$INKSTACK_TEST_REQUEST_LOG"

            case "$url" in
              "$INKSTACK_TEST_API_BASE"/releases?per_page=100\&page=1)
                if [ "$INKSTACK_TEST_API_FAILURE" = "1" ]; then
                  echo "curl: (22) The requested URL returned error: 403" >&2
                  exit 22
                fi
                printf '%s\\n' "$INKSTACK_TEST_LIST_METADATA_JSON"
                ;;
              "$INKSTACK_TEST_API_BASE"/releases?per_page=100\&page=2)
                if [ "$INKSTACK_TEST_API_FAILURE" = "1" ]; then
                  echo "curl: (22) The requested URL returned error: 403" >&2
                  exit 22
                fi
                printf '%s\\n' "$INKSTACK_TEST_LIST_METADATA_JSON_PAGE2"
                ;;
              "$INKSTACK_TEST_API_BASE"/releases?per_page=100\&page=*)
                if [ "$INKSTACK_TEST_API_FAILURE" = "1" ]; then
                  echo "curl: (22) The requested URL returned error: 403" >&2
                  exit 22
                fi
                printf '[]\\n'
                ;;
              "$INKSTACK_TEST_API_BASE"/releases/tags/*)
                if [ "$INKSTACK_TEST_API_FAILURE" = "1" ]; then
                  echo "curl: (22) The requested URL returned error: 403" >&2
                  exit 22
                fi
                printf '%s\\n' "$INKSTACK_TEST_METADATA_JSON"
                ;;
              "$INKSTACK_TEST_DOWNLOAD_BASE"/*/inkstack-package_SHA256SUMS)
                if [ "$INKSTACK_TEST_ASSET_FAILURE" = "1" ]; then
                  exit 22
                fi
                if [ -n "$INKSTACK_TEST_CHECKSUM_PATH" ]; then
                  cp "$INKSTACK_TEST_CHECKSUM_PATH" "$output"
                else
                  exit 22
                fi
                ;;
              "$INKSTACK_TEST_DOWNLOAD_BASE"/*/inkstack-package-*.tar.gz)
                if [ "$INKSTACK_TEST_ASSET_FAILURE" = "1" ]; then
                  exit 22
                fi
                if [ "$INKSTACK_TEST_CORRUPT_ARCHIVE" = "1" ]; then
                  printf '<html>proxy error</html>\\n' >"$output"
                  exit 0
                fi
                if [ -n "$INKSTACK_TEST_ARCHIVE_PATH" ]; then
                  cp "$INKSTACK_TEST_ARCHIVE_PATH" "$output"
                else
                  exit 22
                fi
                ;;
              *)
                echo "curl: refusing non-InkStack URL: $url" >&2
                exit 22
                ;;
            esac
            """
        ),
        encoding="utf-8",
    )
    fake_curl.chmod(0o755)
    if force_macos:
        fake_uname = bin_dir / "uname"
        fake_uname.write_text(
            "#!/bin/sh\n"
            'case "$1" in\n'
            "  -s) printf 'Darwin\\n' ;;\n"
            "  -m) printf 'arm64\\n' ;;\n"
            "esac\n",
            encoding="utf-8",
        )
        fake_uname.chmod(0o755)
    if old_updater_parent_pid is not None:
        fake_ps = bin_dir / "ps"
        fake_ps.write_text(
            "#!/bin/sh\nexit 1\n"
            if fail_ps
            else "#!/bin/sh\n"
            'case "$*" in\n'
            '  *lstart*) printf "S %s\\n" "$INKSTACK_TEST_PARENT_START" ;;\n'
            '  *) printf "%s\\n" "$INKSTACK_TEST_PARENT_PID" ;;\n'
            "esac\n",
            encoding="utf-8",
        )
        fake_ps.chmod(0o755)

    home = root / "home"
    home.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(
        {
            "INKSTACK_HOME": str(root / "inkstack-home"),
            "INKSTACK_INSTALL_DIR": str(root / "install-bin"),
            "INKSTACK_NON_INTERACTIVE": "1",
            "INKSTACK_RELEASE": release,
            "INKSTACK_INSTALL_DAEMON_ONLY": "1" if daemon_only else "0",
            "INKSTACK_TEST_API_BASE": API_BASE,
            "INKSTACK_TEST_DOWNLOAD_BASE": DOWNLOAD_BASE,
            "INKSTACK_TEST_ARCHIVE_PATH": str(archive_path or ""),
            "INKSTACK_TEST_CHECKSUM_PATH": str(checksum_path or ""),
            "INKSTACK_TEST_API_FAILURE": "1" if api_failure else "0",
            "INKSTACK_TEST_ASSET_FAILURE": "1" if asset_failure else "0",
            "INKSTACK_TEST_CORRUPT_ARCHIVE": "1" if corrupt_archive else "0",
            "INKSTACK_TEST_METADATA_JSON": (
                metadata_json if metadata_json is not None else release_metadata()
            ),
            "INKSTACK_TEST_LIST_METADATA_JSON": (
                list_metadata_json
                if list_metadata_json is not None
                else releases_list_json(application_release())
            ),
            "INKSTACK_TEST_LIST_METADATA_JSON_PAGE2": (
                list_metadata_json_page2
                if list_metadata_json_page2 is not None
                else "[]"
            ),
            "INKSTACK_TEST_REQUEST_LOG": str(request_log),
            "HOME": str(home),
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "SHELL": "/bin/sh",
        }
    )
    env["INKSTACK_INSTALL_IF_CURRENT"] = "1" if manual_update else "0"
    if update_guard_from_release is None:
        env.pop("INKSTACK_INSTALL_IF_LATEST", None)
        env.pop("INKSTACK_UPDATE_FROM_RELEASE", None)
    else:
        env["INKSTACK_INSTALL_IF_LATEST"] = "0" if manual_update else "1"
        env["INKSTACK_UPDATE_FROM_RELEASE"] = update_guard_from_release
    if old_updater_parent_pid is not None:
        env["INKSTACK_TEST_PARENT_PID"] = str(old_updater_parent_pid)
        env["INKSTACK_TEST_PARENT_START"] = process_start_time()
    result = subprocess.run(
        ["/bin/sh", str(INSTALL_SCRIPT)],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )
    requests = (
        request_log.read_text(encoding="utf-8").splitlines()
        if request_log.exists()
        else []
    )
    return result, requests


def process_start_time() -> str:
    details = subprocess.check_output(
        ["ps", "-p", str(os.getpid()), "-o", "stat=", "-o", "lstart="], text=True
    ).strip()
    return details.split(maxsplit=1)[1]


def create_package_release(
    root: Path,
    *,
    metadata_version: str = VERSION,
    binary_version: str | None = None,
    manifest_lists_archive: bool = True,
) -> tuple[Path, Path, str]:
    reported_version = binary_version if binary_version is not None else metadata_version
    package_dir = root / "package"
    (package_dir / "bin").mkdir(parents=True)
    (package_dir / "inkstack-path").mkdir()
    (package_dir / "inkstack-package.json").write_text("{}\n", encoding="utf-8")
    write_executable(
        package_dir / "bin" / "inkstack",
        f"#!/bin/sh\nprintf 'inkstack-cli {reported_version}\\n'\n",
    )
    write_executable(
        package_dir / "bin" / "inkstack-code-mode-host",
        "#!/bin/sh\nexit 0\n",
    )
    write_executable(package_dir / "inkstack-path" / "rg", "#!/bin/sh\nexit 0\n")

    asset = "inkstack-package-aarch64-apple-darwin.tar.gz"
    archive_path = root / asset
    with tarfile.open(archive_path, "w:gz") as archive:
        for path in package_dir.iterdir():
            archive.add(path, arcname=path.name)

    archive_digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    checksum_path = root / "inkstack-package_SHA256SUMS"
    manifest_line = f"{archive_digest}  {asset}\n" if manifest_lists_archive else ""
    checksum_path.write_text(manifest_line, encoding="utf-8")
    checksum_digest = hashlib.sha256(checksum_path.read_bytes()).hexdigest()
    metadata_json = json.dumps(
        {
            "assets": [
                {"name": asset, "digest": f"sha256:{archive_digest}"},
                {
                    "name": "inkstack-package_SHA256SUMS",
                    "digest": f"sha256:{checksum_digest}",
                },
            ],
            "tag_name": f"rust-v{metadata_version}",
        },
        indent=2,
    )
    return archive_path, checksum_path, metadata_json


def application_release() -> dict:
    assets = [
        {
            "name": f"inkstack-package-{target}.tar.gz",
            "digest": f"sha256:{'a' * 64}",
        }
        for target in (
            "aarch64-apple-darwin",
            "x86_64-apple-darwin",
            "aarch64-unknown-linux-musl",
            "x86_64-unknown-linux-musl",
        )
    ]
    assets.append(
        {"name": "inkstack-package_SHA256SUMS", "digest": f"sha256:{'b' * 64}"}
    )
    return {"tag_name": f"rust-v{VERSION}", "assets": assets}


def v8_dependency_release() -> dict:
    """The published V8 dependency release: never a valid application release."""
    return {
        "tag_name": V8_RELEASE_TAG,
        "assets": [
            {
                "name": "librusty_v8_release_x86_64-unknown-linux-gnu.a.gz",
                "digest": f"sha256:{'c' * 64}",
            },
        ],
    }


def releases_list_json(*entries: dict) -> str:
    return json.dumps(list(entries), indent=2)


def release_metadata(
    *,
    compact: bool = False,
    reorder: bool = False,
    version: str = VERSION,
) -> str:
    release = application_release()
    if version != VERSION:
        release["tag_name"] = f"rust-v{version}"
    assets = [
        asset_metadata(asset["name"], asset["digest"], reorder=reorder)
        for asset in release["assets"]
    ]
    separators = (",", ":") if compact else None
    return json.dumps(
        {"assets": assets, "body": "braces: { } [ ]", "tag_name": release["tag_name"]},
        indent=None if compact else 2,
        separators=separators,
    )


def asset_metadata(name: str, digest: str, *, reorder: bool) -> dict[str, str]:
    if reorder:
        return {"digest": digest, "name": name}
    return {"name": name, "digest": digest}


def release_metadata_with_decoys() -> str:
    fake_digest = f"sha256:{'0' * 64}"
    assets = [
        {
            "metadata": {
                "name": "inkstack-package-x86_64-unknown-linux-musl.tar.gz",
                "digest": fake_digest,
            },
            "digest": f"sha256:{'c' * 64}",
            "name": "librusty_v8_release_x86_64-unknown-linux-gnu.a.gz",
        }
    ]
    return json.dumps(
        {
            "body": (
                f'fake: {{"name":"inkstack-package_SHA256SUMS","digest":"{fake_digest}"}}'
            ),
            "assets": assets,
            "tag_name": f"rust-v{VERSION}",
        },
        separators=(",", ":"),
    )


def write_executable(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
