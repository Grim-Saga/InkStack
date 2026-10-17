"""Guard the Bazel build graph against OpenAI Codex application binaries.

InkStack builds, tests, and releases must never fetch application binaries
from OpenAI's Codex release infrastructure. Scanning every Bazel build file
for the known download hosts keeps those dependencies from silently
returning. Third-party *source* dependencies (for example the
openai-oss-forks crate mirrors pinned in Cargo and the module lockfile) are
unaffected: they use different URLs and remain legitimate.
"""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

# URL fragments that only appear when a build rule points at OpenAI-hosted
# Codex application artifacts.
FORBIDDEN_URL_FRAGMENTS = (
    "releases.openai.com",
    "openai/codex/releases",
)

SKIP_DIR_PARTS = ("/.git/", "/.superpowers/", "/node_modules/")


def _build_graph_files() -> list[Path]:
    candidates = [
        ROOT / "MODULE.bazel",
        ROOT / "MODULE.bazel.lock",
        ROOT / ".bazelrc",
    ]
    for pattern in ("*.bzl", "BUILD.bazel", "BUILD", "WORKSPACE", "WORKSPACE.bazel"):
        candidates.extend(ROOT.rglob(pattern))
    files = []
    for path in candidates:
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT).as_posix()
        if "/" in relative:
            prefix = "/" + relative.rsplit("/", 1)[0] + "/"
            if any(part in prefix for part in SKIP_DIR_PARTS):
                continue
        elif relative.startswith("."):
            continue
        files.append(path)
    return sorted(files)


class BazelNoUpstreamCodexBinariesTest(unittest.TestCase):
    def test_build_files_never_download_openai_codex_binaries(self) -> None:
        findings: list[str] = []
        for path in _build_graph_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), start=1):
                for fragment in FORBIDDEN_URL_FRAGMENTS:
                    if fragment in line:
                        findings.append(
                            f"{path.relative_to(ROOT)}:{number}: {fragment}: {line.strip()}"
                        )
        self.assertEqual(
            findings,
            [],
            "Bazel build files must not download OpenAI Codex application "
            "binaries:\n" + "\n".join(findings),
        )


if __name__ == "__main__":
    unittest.main()
