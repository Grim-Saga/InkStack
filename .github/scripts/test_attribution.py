"""Retain original notices alongside the fork's own attribution."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class AttributionTest(unittest.TestCase):
    def test_license_and_notice_keep_upstream_and_fork_copyrights(self):
        license_text = (ROOT / "LICENSE").read_text()
        notice = (ROOT / "NOTICE").read_text().replace("\u00a0", " ")
        self.assertIn("Version 2.0, January 2004", license_text)
        for text in (license_text, notice):
            self.assertIn("Copyright 2025 OpenAI", text)
            self.assertIn("Copyright 2025 Grim Saga", text)
        for attribution in ("OpenAI Codex", "Florian Dehau", "The Ratatui Developers"):
            self.assertIn(attribution, notice)


if __name__ == "__main__":
    unittest.main()
