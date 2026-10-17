"""Keep publication GitHub-only without dropping release integrity contracts."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class GitHubOnlyDistributionTest(unittest.TestCase):
    def test_no_external_publishers_or_foreign_publication_targets(self):
        forbidden = (
            "publish-r2", "publish-npm:", "OpenAI.InkStack",
            "KOMAC_FORK_OWNER", 'scope: "@openai"',
            "developers.openai.com", "gh-action-pypi-publish",
            "npm publish", "INKSTACK_PUBLISH_", "vercel-deploy",
        )
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            with self.subTest(workflow=path.name):
                text = path.read_text()
                for fragment in forbidden:
                    self.assertNotIn(fragment, text)

    def test_github_release_artifacts_and_first_release_handling_remain(self):
        text = (ROOT / ".github/workflows/rust-release.yml").read_text()
        for required in (
            '"rust-v*.*.*"', "stage-npm-packages:",
            "inkstack-package_SHA256SUMS", "dist/install.sh", "dist/install.ps1",
            "gh release upload", "--check-github latest-response",
            "./.github/actions/setup-rusty-v8", "publish-dotslash:",
        ):
            self.assertIn(required, text)

    def test_canary_update_depends_only_on_github_publication(self):
        text = (ROOT / ".github/workflows/rust-release.yml").read_text()
        block = text[text.index("  update-branch:"):]
        self.assertNotIn("npm_tag", block)
        self.assertNotIn("publish-r2", block)
        self.assertNotIn("publish-npm", block)
        self.assertIn("needs.publish-dotslash.result == 'success'", block)
        self.assertIn("needs.release.outputs.version", block)

    def test_local_reusable_workflows_and_needs_resolve(self):
        # All job headers in these workflows are two-space-indented.
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            text = path.read_text()
            jobs = set(re.findall(r"^  ([\w-]+):\s*$", text, re.M))
            for match in re.finditer(r"^    needs:[ \t]*(.*)$", text, re.M):
                inline = match.group(1).strip()
                if inline:
                    deps = inline.strip("[]").replace(",", " ").split()
                else:
                    deps = re.findall(r"^      - ([\w-]+)$", text[match.end():].split("\n    ", 1)[0], re.M)
                for dep in deps:
                    self.assertIn(dep, jobs, f"{path.name}: dangling needs {dep}")
            for relative in re.findall(r"uses: (\./\.github/workflows/[^\s]+)", text):
                self.assertTrue((ROOT / relative).is_file(), relative)

    def test_updater_never_queries_external_package_registries(self):
        for relative in ("inkstack-rs/tui/src/updates.rs", "inkstack-rs/cli/src/doctor/updates.rs"):
            text = (ROOT / relative).read_text()
            for fragment in ("formulae.brew.sh", "npm_registry::", "persistent.oaistatic.com", "backend-api/wham/app", "OpenAI.InkStack"):
                self.assertNotIn(fragment, text, relative)
        action = (ROOT / "inkstack-rs/tui/src/update_action.rs").read_text()
        for command in ('("npm",', '("bun",', '("pnpm",', '("vp",', '("brew",'):
            self.assertNotIn(command, action)


if __name__ == "__main__":
    unittest.main()
