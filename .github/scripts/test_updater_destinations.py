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


def rust_code(text: str) -> str:
    """Blank comments and literals, retaining offsets and structural newlines."""
    code = list(text)
    raw_string = re.compile(r'(?:br|cr|r)(#*)"')
    character = re.compile(r"'(?:\\(?:u\{[0-9a-fA-F_]+\}|x[0-9a-fA-F]{2}|.)|[^'\\\n])'")
    i = 0
    while i < len(text):
        start = i
        if text.startswith("//", i):
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
        elif text.startswith("/*", i):
            end, depth = i + 2, 1
            while end < len(text) and depth:
                if text.startswith("/*", end):
                    depth += 1
                    end += 2
                elif text.startswith("*/", end):
                    depth -= 1
                    end += 2
                else:
                    end += 1
        elif match := raw_string.match(text, i):
            terminator = '"' + match.group(1)
            close = text.find(terminator, match.end())
            end = len(text) if close < 0 else close + len(terminator)
        elif text[i] == '"':
            end = i + 1
            while end < len(text):
                if text[end] == "\\":
                    end += 2
                elif text[end] == '"':
                    end += 1
                    break
                else:
                    end += 1
        elif match := character.match(text, i):
            end = match.end()
        else:
            i += 1
            continue
        end = min(end, len(text))
        for pos in range(start, end):
            if text[pos] != "\n":
                code[pos] = " "
        i = end
    return "".join(code)


def rust_block_end(code: str, opening: int) -> int | None:
    depth = 0
    for pos in range(opening, len(code)):
        if code[pos] == "{":
            depth += 1
        elif code[pos] == "}":
            depth -= 1
            if depth == 0:
                return pos
    return None


def negative_probe_span(relative: str, text: str) -> tuple[int, int] | None:
    """Recognize only the literal host fixture in its cfg(test) CLI test.

    Scope is identified in Rust code, never comments or string contents.
    The declaration accepts a small syntax subset and fails closed on
    changed names, types, expressions or hosts. No whole line is exempted.
    """
    if relative != "inkstack-rs/cli/src/main.rs":
        return None
    code = rust_code(text)
    module = re.search(r"(?m)^#\[cfg\(test\)\]\nmod tests \{", code)
    if module is None:
        return None
    module_end = rust_block_end(code, module.end() - 1)
    if module_end is None:
        return None
    test = re.compile(
        r"(?m)^    #\[tokio::test\]\n"
        r"    async fn updater_http_client_factory_enforces_application_requirements\(\) \{"
    ).search(code, module.end(), module_end)
    if test is None:
        return None
    test_end = rust_block_end(code, test.end() - 1)
    if test_end is None or test_end >= module_end:
        return None
    declaration = re.compile(
        r"(?m)^        const[ \t]+DENIED_UPDATE_PROBE_HOSTS\s*:\s*"
        r"\[\s*&str\s*;\s*3\s*\]\s*=\s*"
        r'\[\s*"chatgpt\.com"\s*,\s*"releases\.openai\.com"\s*,\s*'
        r'"unlisted\.example"\s*,?\s*\]\s*;'
    )
    for match in declaration.finditer(text, test.end(), test_end):
        # A matching declaration written inside a comment/raw string is data.
        if code[match.start() + 8 : match.start() + 13] == "const":
            return match.start(), match.end()
    return None


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
