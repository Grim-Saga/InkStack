"""Guard updater execution paths against OpenAI Codex destinations.

InkStack's TUI and daemon must never fetch installers, updates, or release
notes from OpenAI's Codex infrastructure. This scans the updater sources
(the standalone update commands, the daemon's installer bootstrap, the
release-notes link, and the daemon's install documentation) so those
destinations cannot silently return. Unrelated fixtures and protocol test
data elsewhere in the workspace are intentionally out of scope.
"""

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
    "inkstack-rs/cli/src/doctor/updates.rs",
)

FORBIDDEN_DESTINATIONS = (
    "chatgpt.com/codex",
    "github.com/openai/codex/releases",
    "releases.openai.com",
    "api.github.com/repos/openai",
)


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
            for number, line in enumerate(text.splitlines(), start=1):
                for destination in FORBIDDEN_DESTINATIONS:
                    if destination in line:
                        findings.append(
                            f"{relative}:{number}: {destination}: {line.strip()}"
                        )
        self.assertEqual(
            findings,
            [],
            "Updater paths must not reference OpenAI Codex destinations:\n"
            + "\n".join(findings),
        )

    def test_installer_bootstrap_uses_inkstack_releases(self) -> None:
        update_action = (
            ROOT / "inkstack-rs/tui/src/update_action.rs"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "https://github.com/Grim-Saga/InkStack/releases/latest/download/install.sh",
            update_action,
        )
        self.assertIn(
            "https://github.com/Grim-Saga/InkStack/releases/latest/download/install.ps1",
            update_action,
        )
        update_loop = (
            ROOT / "inkstack-rs/app-server-daemon/src/update_loop.rs"
        ).read_text(encoding="utf-8")
        self.assertIn("https://api.github.com/repos/Grim-Saga/InkStack", update_loop)
        self.assertIn(
            "https://github.com/Grim-Saga/InkStack/releases/download",
            update_loop,
        )


if __name__ == "__main__":
    unittest.main()
