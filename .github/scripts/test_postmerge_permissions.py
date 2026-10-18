"""Keep the postmerge reusable V8 call within GitHub's permission ceiling."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def job_block(workflow: str, name: str) -> str:
    match = re.search(
        rf"^  {re.escape(name)}:\n((?:\n| {{4}}[^\n]*\n)*)", workflow, re.M
    )
    if match is None:
        raise AssertionError(f"missing job: {name}")
    return match.group(1)


def explicit_permissions(job: str) -> dict[str, str]:
    match = re.search(r"^    permissions:\n((?:      [^\n]*\n)+)", job, re.M)
    if match is None:
        return {}
    return dict(
        re.findall(r"^      ([\w-]+): (read|write|none)\s*$", match.group(1), re.M)
    )


class PostmergePermissionsTest(unittest.TestCase):
    def test_v8_call_grants_exactly_the_callees_read_permissions(self):
        caller = (ROOT / ".github/workflows/postmerge-ci.yml").read_text()
        callee = (ROOT / ".github/workflows/v8-canary.yml").read_text()
        requested = explicit_permissions(job_block(callee, "build"))
        self.assertEqual(requested, {"contents": "read", "actions": "read"})
        self.assertEqual(
            explicit_permissions(job_block(caller, "v8-canary")), requested
        )

    def test_v8_grant_does_not_restrict_other_postmerge_jobs(self):
        caller = (ROOT / ".github/workflows/postmerge-ci.yml").read_text()
        self.assertNotRegex(caller, r"(?m)^permissions:")
        self.assertNotIn("permissions:", job_block(caller, "rust-ci-full"))
        self.assertNotIn("permissions:", job_block(caller, "results"))


if __name__ == "__main__":
    unittest.main()
