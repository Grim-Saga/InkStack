"""Exercise a built SDK's default runtime in an otherwise isolated environment."""

from dataclasses import replace
from importlib.metadata import distribution, version
from pathlib import Path
from tempfile import TemporaryDirectory

from app_server_harness import AppServerHarness

import inkstack
from inkstack import InkStack


def main() -> None:
    installed_root = Path(distribution("inkstack").locate_file("")).resolve()
    assert Path(inkstack.__file__).resolve().is_relative_to(installed_root), (
        "The smoke test must import the installed SDK, not the source checkout"
    )

    with TemporaryDirectory() as directory, AppServerHarness(Path(directory)) as harness:
        harness.responses.enqueue_assistant_message("Installed SDK works")
        config = replace(harness.app_server_config(), inkstack_bin=None)
        with InkStack(config=config) as inkstack:
            thread = inkstack.thread_start()
            result = thread.run(
                "Check the installed SDK", turn_service_tier="default", source="automation"
            )
            inkstack.thread_resume(thread.id, include_turns=False)
            inkstack.thread_fork(thread.id, include_turns=True)
        assert result.final_response == "Installed SDK works"
        assert harness.responses.single_request().message_input_texts("user")[-1:] == [
            "Check the installed SDK"
        ]

    print(f"Installed SDK passed with CLI runtime {version('inkstack-cli-bin')}")


if __name__ == "__main__":
    main()
