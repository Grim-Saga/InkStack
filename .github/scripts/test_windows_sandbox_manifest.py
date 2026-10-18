"""Keep Cargo/Bazel Windows setup inputs and privilege declarations consistent."""

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SANDBOX = ROOT / "inkstack-rs/windows-sandbox-rs"


class WindowsSandboxManifestTest(unittest.TestCase):
    def test_cargo_and_bazel_refer_to_the_same_existing_manifest(self):
        cargo_build = (SANDBOX / "build.rs").read_text()
        manifest = re.search(r'const SETUP_MANIFEST: &str = "([^"]+)";', cargo_build)
        self.assertIsNotNone(manifest)
        filename = manifest.group(1)
        self.assertTrue(
            (SANDBOX / filename).is_file(), f"missing setup manifest: {filename}"
        )
        bazel = (SANDBOX / "BUILD.bazel").read_text()
        inputs = set(re.findall(r"(?<![\w.-])([\w-]+\.manifest)(?![\w.-])", bazel))
        self.assertEqual(inputs, {filename})

    def test_setup_manifest_requests_as_invoker_without_ui_access(self):
        path = SANDBOX / "inkstack-windows-sandbox-setup.manifest"
        self.assertTrue(path.is_file(), f"missing setup manifest: {path.name}")
        tree = ET.parse(path)
        ns = {"asm": "urn:schemas-microsoft-com:asm.v2"}
        levels = tree.findall(".//asm:requestedExecutionLevel", ns)
        self.assertEqual(len(levels), 1)
        self.assertEqual(levels[0].attrib, {"level": "asInvoker", "uiAccess": "false"})


if __name__ == "__main__":
    unittest.main()
