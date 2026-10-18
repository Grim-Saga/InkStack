"""Guard updater execution paths against unverified or foreign bootstrap.

InkStack's TUI and daemon must never fetch installers, updates, or release
notes from OpenAI's Codex infrastructure, and standalone updates must never
pipe a remote script straight into an interpreter: the installer has to be
resolved from a verified InkStack application release, checked against the
SHA-256 digest GitHub records for the release asset, and executed from a
staged file. This scans the updater sources and the CLI update path so
those guarantees cannot silently regress. Unrelated fixtures and protocol
test data elsewhere in the workspace are intentionally out of scope.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

UPDATER_PATH_FILES = (
    "inkstack-rs/tui/src/update_action.rs",
    "inkstack-rs/tui/src/update_prompt.rs",
    "inkstack-rs/tui/src/updates.rs",
    "inkstack-rs/tui/src/update_versions.rs",
    "inkstack-rs/app-server-daemon/src/update_loop.rs",
    "inkstack-rs/app-server-daemon/src/manual_update.rs",
    "inkstack-rs/app-server-daemon/src/migration.rs",
    "inkstack-rs/app-server-daemon/README.md",
    "inkstack-rs/cli/src/main.rs",
    "inkstack-rs/cli/src/doctor/updates.rs",
)

FORBIDDEN_DESTINATIONS = (
    "chatgpt.com/codex",
    "github.com/openai/codex/releases",
    "releases.openai.com",
    "api.github.com/repos/openai",
)

# Unverified pipe-to-interpreter execution of remote downloads. These apply
# to updater execution-path code; the daemon README deliberately documents a
# human-run first-install bootstrap, which is a different trust model.
FORBIDDEN_EXECUTION_PATTERNS = (
    "| INKSTACK_NON_INTERACTIVE=1 sh",
    "| iex",
)

DOCUMENTATION_FILES = ("inkstack-rs/app-server-daemon/README.md",)


def negative_probe_span(relative: str, text: str) -> tuple[int, int] | None:
    """Recognize only the literal host fixture in its cfg(test) CLI test.

    This deliberately accepts a small Rust syntax subset, failing closed on
    changed names, types, expressions or hosts. No whole line is exempted.
    """
    if relative != "inkstack-rs/cli/src/main.rs":
        return None
    module = re.search(r"(?ms)^#\[cfg\(test\)\]\nmod tests \{\n(?P<body>.*?)^}", text)
    if module is None:
        return None
    test = re.search(
        r"(?ms)^    #\[tokio::test\]\n"
        r"    async fn updater_http_client_factory_enforces_application_requirements\(\) \{\n"
        r"(?P<body>.*?)^    }",
        module.group("body"),
    )
    if test is None:
        return None
    declaration = re.search(
        r"(?m)^        const[ \t]+DENIED_UPDATE_PROBE_HOSTS\s*:\s*"
        r"\[\s*&str\s*;\s*3\s*\]\s*=\s*"
        r'\[\s*"chatgpt\.com"\s*,\s*"releases\.openai\.com"\s*,\s*'
        r'"unlisted\.example"\s*,?\s*\]\s*;',
        test.group("body"),
    )
    if declaration is None:
        return None
    offset = module.start("body") + test.start("body")
    return offset + declaration.start(), offset + declaration.end()


def updater_destination_findings(relative: str, text: str) -> list[str]:
    exempt = negative_probe_span(relative, text)
    findings: list[str] = []
    for destination in FORBIDDEN_DESTINATIONS:
        for match in re.finditer(re.escape(destination), text):
            if exempt is not None and exempt[0] <= match.start() < exempt[1]:
                continue
            number = text.count("\n", 0, match.start()) + 1
            line = text.splitlines()[number - 1]
            findings.append(f"{relative}:{number}: {destination}: {line.strip()}")
    return findings


class UpdaterDestinationTest(unittest.TestCase):
    def test_updater_paths_never_reference_openai_codex(self) -> None:
        findings: list[str] = []
        for relative in UPDATER_PATH_FILES:
            path = ROOT / relative
            self.assertTrue(
                path.is_file(),
                f"expected updater path is missing: {relative}",
            )
            text = path.read_text(encoding="utf-8", errors="replace")
            findings.extend(updater_destination_findings(relative, text))
        self.assertEqual(
            findings,
            [],
            "Updater paths must not reference OpenAI Codex destinations:\n"
            + "\n".join(findings),
        )

    def test_updater_code_never_pipes_remote_scripts_into_interpreters(self) -> None:
        code_files = [
            relative
            for relative in UPDATER_PATH_FILES
            if relative not in DOCUMENTATION_FILES
        ]
        findings: list[str] = []
        for relative in code_files:
            text = (ROOT / relative).read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), start=1):
                for pattern in FORBIDDEN_EXECUTION_PATTERNS:
                    if pattern in line:
                        findings.append(
                            f"{relative}:{number}: {pattern}: {line.strip()}"
                        )
        self.assertEqual(
            findings,
            [],
            "Updater execution paths must verify downloads before execution:\n"
            + "\n".join(findings),
        )

    def test_installer_bootstrap_uses_inkstack_releases(self) -> None:
        update_action = (ROOT / "inkstack-rs/tui/src/update_action.rs").read_text(
            encoding="utf-8"
        )
        # Standalone updates must run the CLI's verified bootstrap rather
        # than a remote pipe-to-interpreter command.
        self.assertIn(
            'UpdateAction::StandaloneUnix => ("inkstack", &["update"])', update_action
        )
        self.assertIn(
            'UpdateAction::StandaloneWindows => ("inkstack", &["update"])',
            update_action,
        )
        cli_main = (ROOT / "inkstack-rs/cli/src/main.rs").read_text(encoding="utf-8")
        self.assertIn("fetch_verified_installer_script_blocking", cli_main)
        self.assertIn("verified_installer::fetch_installer_script", cli_main)
        update_loop = (
            ROOT / "inkstack-rs/app-server-daemon/src/update_loop.rs"
        ).read_text(encoding="utf-8")
        self.assertIn("fetch_verified_installer_script", update_loop)
        verified_installer = (
            ROOT / "inkstack-rs/app-server-daemon/src/verified_installer.rs"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "https://api.github.com/repos/Grim-Saga/InkStack", verified_installer
        )
        self.assertIn(
            "https://github.com/Grim-Saga/InkStack/releases/download",
            verified_installer,
        )
        # The fetched bytes are compared against the digest GitHub records
        # for the exact release asset before execution.
        self.assertIn("verify_installer_bytes", verified_installer)
        self.assertIn("did not match the digest", verified_installer)
        self.assertIn("was empty", verified_installer)


if __name__ == "__main__":
    unittest.main()
