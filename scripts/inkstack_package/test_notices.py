import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

from inkstack_package.archive import write_archive
from inkstack_package.layout import build_package_dir, validate_package_dir
from inkstack_package.targets import PACKAGE_VARIANTS, REPO_ROOT, TARGET_SPECS, PackageInputs


class PackageNoticesTest(unittest.TestCase):
    def test_both_variants_ship_exact_root_notices_in_archives(self):
        for variant in PACKAGE_VARIANTS.values():
            for target in ("x86_64-unknown-linux-musl", "aarch64-apple-darwin", "x86_64-pc-windows-msvc"):
                with self.subTest(variant=variant.name, target=target), tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    binary = root / "fixture"
                    binary.write_bytes(b"fixture executable")
                    binary.chmod(0o755)
                    package = root / "package"
                    package.mkdir()
                    spec = TARGET_SPECS[target]
                    inputs = PackageInputs(
                        entrypoint_bin=binary, code_mode_host_bin=binary, rg_bin=binary,
                        bwrap_bin=binary if spec.is_linux else None,
                        inkstack_command_runner_bin=binary if spec.is_windows else None,
                        inkstack_windows_sandbox_setup_bin=binary if spec.is_windows else None,
                    )
                    build_package_dir(package, "1.2.3", variant, spec, inputs)
                    validate_package_dir(package, variant, spec)
                    for suffix in ("tar.gz", "zip"):
                        archive = root / f"package.{suffix}"
                        write_archive(package, archive, force=False)
                        if suffix == "zip":
                            with zipfile.ZipFile(archive) as contents:
                                for name in ("LICENSE", "NOTICE"):
                                    self.assertIn(name, contents.namelist())
                                actual = {name: contents.read(name) for name in ("LICENSE", "NOTICE")}
                        else:
                            with tarfile.open(archive) as contents:
                                for name in ("LICENSE", "NOTICE"):
                                    self.assertIn(name, contents.getnames())
                                actual = {name: contents.extractfile(name).read() for name in ("LICENSE", "NOTICE")}
                        for name, body in actual.items():
                            self.assertEqual(body, (REPO_ROOT / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
