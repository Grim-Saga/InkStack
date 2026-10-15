import sys
from pathlib import Path

_EXAMPLES_ROOT = Path(__file__).resolve().parents[1]
if str(_EXAMPLES_ROOT) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES_ROOT))

from _bootstrap import ensure_local_sdk_src, runtime_config

ensure_local_sdk_src()

from inkstack import InkStack

with InkStack(config=runtime_config()) as inkstack:
    # Create an initial thread and turn so we have a real thread to resume.
    original = inkstack.thread_start(model="gpt-5.4", config={"model_reasoning_effort": "high"})
    first = original.turn("Tell me one fact about Saturn.").run()
    print("Created thread:", original.id)

    # Resume the existing thread by ID.
    resumed = inkstack.thread_resume(original.id)
    second = resumed.turn("Continue with one more fact.").run()
    print(second.final_response)
