"""Exercise the updater scanner on negative fixtures and hostile near misses."""

import textwrap
import unittest

from test_updater_destinations import updater_destination_findings

CLI = "inkstack-rs/cli/src/main.rs"
DECLARATION = (
    "const DENIED_UPDATE_PROBE_HOSTS: [&str; 3] = "
    '["chatgpt.com", "releases.openai.com", "unlisted.example"];'
)
URLS = (
    "https://chatgpt.com/codex/install.sh",
    "https://github.com/openai/codex/releases/download/v1/codex.exe",
    "https://releases.openai.com/codex.exe",
    "https://api.github.com/repos/openai/codex/releases",
)


def negative_test(body: str) -> str:
    return (
        "#[cfg(test)]\nmod tests {\n"
        "    #[tokio::test]\n"
        "    async fn updater_http_client_factory_enforces_application_requirements() {\n"
        + textwrap.indent(body, "        ")
        + "\n    }\n}\n"
    )


class UpdaterDestinationScannerTest(unittest.TestCase):
    def test_accepts_single_line_negative_probe_declaration(self):
        self.assertEqual(
            updater_destination_findings(CLI, negative_test(DECLARATION)), []
        )

    def test_accepts_rustfmt_multiline_negative_probe_declaration(self):
        declaration = DECLARATION.replace(" = [", " =\n    [")
        self.assertEqual(
            updater_destination_findings(CLI, negative_test(declaration)), []
        )

    def test_accepts_expanded_initializer_with_trailing_comma(self):
        declaration = (
            "const DENIED_UPDATE_PROBE_HOSTS: [&str; 3] = [\n"
            '    "chatgpt.com",\n    "releases.openai.com",\n'
            '    "unlisted.example",\n];'
        )
        self.assertEqual(
            updater_destination_findings(CLI, negative_test(declaration)), []
        )

    def test_rejects_every_foreign_production_download_url(self):
        for url in URLS:
            with self.subTest(url=url):
                self.assertEqual(
                    len(updater_destination_findings(CLI, f'fetch("{url}");')), 1
                )

    def test_marker_comment_cannot_exempt_a_production_url(self):
        for url in URLS:
            with self.subTest(url=url):
                source = f'fetch("{url}"); // DENIED_UPDATE_PROBE_HOSTS'
                self.assertEqual(len(updater_destination_findings(CLI, source)), 1)

    def test_rejects_production_declaration_with_the_same_name(self):
        self.assertEqual(len(updater_destination_findings(CLI, DECLARATION)), 1)

    def test_rejects_same_line_url_after_the_exact_declaration(self):
        source = negative_test(
            DECLARATION + ' fetch("https://releases.openai.com/codex.exe");'
        )
        findings = updater_destination_findings(CLI, source)
        self.assertEqual(len(findings), 1)
        self.assertIn('fetch("https://releases.openai.com/codex.exe")', findings[0])

    def test_rejects_urls_before_and_after_the_fixture(self):
        source = negative_test(
            'fetch("https://releases.openai.com/before");\n'
            + DECLARATION
            + '\nfetch("https://releases.openai.com/after");'
        )
        self.assertEqual(len(updater_destination_findings(CLI, source)), 2)

    def test_rejects_url_expressions_in_the_initializer(self):
        source = negative_test(
            DECLARATION.replace(
                '"releases.openai.com"', 'fetch("https://releases.openai.com")'
            )
        )
        self.assertEqual(len(updater_destination_findings(CLI, source)), 1)

    def test_rejects_changed_host_list_or_array_length(self):
        for declaration in (
            DECLARATION.replace('"unlisted.example"', '"other.example"'),
            DECLARATION.replace("&str; 3", "&str; 4"),
            DECLARATION.replace(
                '"releases.openai.com"', '"https://releases.openai.com/codex.exe"'
            ),
        ):
            with self.subTest(declaration=declaration):
                self.assertEqual(
                    len(updater_destination_findings(CLI, negative_test(declaration))),
                    1,
                )

    def test_rejects_the_fixture_in_other_files_or_functions(self):
        source = negative_test(DECLARATION)
        self.assertEqual(
            len(updater_destination_findings("inkstack-rs/tui/src/updates.rs", source)),
            1,
        )
        source = source.replace("enforces_application_requirements", "fetches_a_binary")
        self.assertEqual(len(updater_destination_findings(CLI, source)), 1)

    def test_rejects_the_fixture_without_cfg_test(self):
        source = negative_test(DECLARATION).replace("#[cfg(test)]\n", "")
        self.assertEqual(len(updater_destination_findings(CLI, source)), 1)

    def test_rejects_unterminated_declaration_without_swallowing_later_url(self):
        source = negative_test(
            DECLARATION[:-2] + '\nfetch("https://releases.openai.com/codex.exe");'
        )
        self.assertGreaterEqual(len(updater_destination_findings(CLI, source)), 1)


if __name__ == "__main__":
    unittest.main()
