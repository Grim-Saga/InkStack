"""Guard release publishing against OpenAI destinations and ungated publishers.

InkStack's application-release pipeline must only publish to destinations
the repository owner has explicitly configured, and must never target
OpenAI-owned infrastructure. Optional external publishers are disabled by
default through repository variables; this guard fails if a gate is
removed or if an OpenAI-owned destination reappears in the release
pipeline. The Python SDK publication workflows intentionally keep their
`github.repository == 'openai/inkstack'` guards: the guard can never
match this repository, so those publishers stay safely disabled until
PyPI ownership is decided.
"""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RELEASE_PIPELINE_FILES = (
    ".github/workflows/rust-release.yml",
    ".github/workflows/rust-release-windows.yml",
    ".github/workflows/r2-release.yml",
    ".github/scripts/publish_r2_release.py",
    ".github/scripts/releases.py",
)

FORBIDDEN_FRAGMENTS = (
    "releases.openai.com",
    "openai/inkstack",
)

# Optional external publishers in rust-release.yml that must stay behind
# an explicit repository-variable opt-in.
GATED_PUBLISHERS = {
    "publish-npm": "vars.INKSTACK_PUBLISH_NPM == 'true'",
    "winget": "vars.INKSTACK_PUBLISH_WINGET == 'true'",
    "deploy-dev-website": "vars.INKSTACK_PUBLISH_DEV_WEBSITE == 'true'",
    "publish-r2-assets": "vars.INKSTACK_PUBLISH_R2 == 'true'",
    "publish-r2": "vars.INKSTACK_PUBLISH_R2 == 'true'",
}

_JOB_HEADER = re.compile(r"^  [a-zA-Z][a-zA-Z0-9-]*(?: \[[^\]]*\])?:\s*$", re.MULTILINE)


def _job_block(workflow: str, job_name: str) -> str:
    header = re.compile(rf"^  {re.escape(job_name)}:\s*$", re.MULTILINE)
    match = header.search(workflow)
    if match is None:
        raise AssertionError(f"job {job_name} is missing from the release workflow")
    following = _JOB_HEADER.search(workflow, match.end())
    return workflow[match.start() : following.start() if following else len(workflow)]


class ReleasePublisherGateTest(unittest.TestCase):
    def test_release_pipeline_has_no_openai_destinations(self) -> None:
        for relative in RELEASE_PIPELINE_FILES:
            path = ROOT / relative
            self.assertTrue(path.is_file(), f"missing release pipeline file: {relative}")
            text = path.read_text(encoding="utf-8")
            for fragment in FORBIDDEN_FRAGMENTS:
                self.assertNotIn(
                    fragment,
                    text,
                    f"{relative} must not reference {fragment}",
                )

    def test_r2_publisher_uses_the_inkstack_repository(self) -> None:
        source = (ROOT / ".github/scripts/publish_r2_release.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('REPOSITORY = "Grim-Saga/InkStack"', source)
        self.assertIn(
            'GITHUB_RELEASES_DOWNLOAD_URL = f"https://github.com/{REPOSITORY}/releases/download"',
            source,
        )

    def test_optional_publishers_require_explicit_opt_in(self) -> None:
        workflow = (ROOT / ".github/workflows/rust-release.yml").read_text(
            encoding="utf-8"
        )
        for job_name, gate in GATED_PUBLISHERS.items():
            with self.subTest(job=job_name):
                block = _job_block(workflow, job_name)
                self.assertIn(
                    gate,
                    block,
                    f"publisher job {job_name} must be gated on {gate}",
                )

    def test_canary_branch_update_tolerates_skipped_publishers(self) -> None:
        workflow = (ROOT / ".github/workflows/rust-release.yml").read_text(
            encoding="utf-8"
        )
        block = _job_block(workflow, "update-branch")
        self.assertIn("needs.publish-r2.result != 'failure'", block)
        self.assertIn("needs.publish-npm.result != 'failure'", block)

    def test_python_publishers_stay_disabled_outside_upstream(self) -> None:
        # The Python SDK/runtime workflows keep upstream's repository guard.
        # It can never match Grim-Saga/InkStack, so PyPI publishing stays
        # disabled until the repository owner verifies package ownership.
        guards = sorted(
            path
            for path in (ROOT / ".github/workflows").glob("python-*.yml")
            if "openai/inkstack" in path.read_text(encoding="utf-8")
        )
        self.assertTrue(
            guards,
            "expected the python workflows to retain their disabled-state "
            "repository guards",
        )


if __name__ == "__main__":
    unittest.main()
