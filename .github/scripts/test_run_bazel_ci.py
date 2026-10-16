from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


SCRIPT = Path(__file__).with_name("run-bazel-ci.sh")


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "requires POSIX bash")
class RunBazelCITest(unittest.TestCase):
    def run_wrapper(
        self,
        *,
        runner: str,
        keyed: bool,
        bazel_args: tuple[str, ...] = ("build",),
        wrapper_args: tuple[str, ...] = (),
    ) -> list[str]:
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            captured = directory / "bazel-args.json"
            bazel = directory / "bazel"
            bazel.write_text(
                f"#!{sys.executable}\n"
                "import json, os, pathlib, sys\n"
                "pathlib.Path(os.environ['INKSTACK_TEST_BAZEL_ARGS_FILE']).write_text(\n"
                "    json.dumps(sys.argv[1:]))\n",
                encoding="utf-8",
            )
            bazel.chmod(0o755)
            env = {
                name: value
                for name, value in os.environ.items()
                if not name.startswith(
                    ("BAZEL_", "BUILDBUDDY_", "GITHUB_", "INKSTACK_BAZEL_")
                )
            }
            env.update(
                RUNNER_OS=runner,
                INKSTACK_BAZEL_BIN=str(bazel),
                INKSTACK_BAZEL_WINDOWS_PATH="C:/Windows/System32",
                INKSTACK_TEST_BAZEL_ARGS_FILE=str(captured),
            )
            if keyed:
                env["BUILDBUDDY_API_KEY"] = "test-key"
            result = subprocess.run(
                [
                    "bash",
                    str(SCRIPT),
                    *wrapper_args,
                    "--",
                    *bazel_args,
                    "--",
                    "//:fixture",
                ],
                cwd=directory,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(captured.read_text(encoding="utf-8"))

    def test_explicit_platform_wins_over_automatically_added_linux_config(self) -> None:
        platform = "--platforms=@rules_rs//rs/platforms:x86_64-unknown-linux-musl"
        args = self.run_wrapper(
            runner="Linux",
            keyed=True,
            bazel_args=("test", "--platforms=//:earlier-choice", platform),
        )
        separator = args.index("--")
        effective_platform = max(
            index
            for index, value in enumerate(args[:separator])
            if value.startswith("--platforms=")
        )
        self.assertGreater(effective_platform, args.index("--config=ci-linux"))
        self.assertEqual(args[effective_platform], platform)
        self.assertEqual(args[separator + 1 :], ["//:fixture"])

    def test_keyed_windows_cross_keeps_its_default_remote_platform(self) -> None:
        args = self.run_wrapper(
            runner="Windows", keyed=True, wrapper_args=("--windows-cross-compile",)
        )
        self.assertIn("--config=ci-windows-cross", args)
        self.assertIn("--host_platform=//:rbe", args)
        self.assertIn("--shell_executable=/bin/bash", args)
        self.assertFalse(any(arg.startswith("--platforms=") for arg in args))

    def test_keyless_windows_cross_keeps_native_msvc_fallback(self) -> None:
        args = self.run_wrapper(
            runner="Windows", keyed=False, wrapper_args=("--windows-cross-compile",)
        )
        self.assertIn("--host_platform=//:local_windows_msvc", args)
        self.assertIn("--jobs=8", args)
        self.assertNotIn("--host_platform=//:rbe", args)
        self.assertFalse(any(arg.startswith("--config=") for arg in args))
        self.assertFalse(any(arg.startswith("--platforms=") for arg in args))


if __name__ == "__main__":
    unittest.main()
