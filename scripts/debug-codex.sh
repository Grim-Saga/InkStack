#!/bin/bash

# Set "chatgpt.cliExecutable": "/Users/<USERNAME>/code/inkstack/scripts/debug-inkstack.sh" in VSCode settings to always get the 
# latest inkstack-rs binary when debugging InkStack Extension.


set -euo pipefail

INKSTACK_RS_DIR=$(realpath "$(dirname "$0")/../inkstack-rs")
(cd "$INKSTACK_RS_DIR" && cargo run --quiet --bin inkstack -- "$@")