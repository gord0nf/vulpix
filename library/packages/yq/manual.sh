#!/usr/bin/env bash

INSTALL_DIR="$1"
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

bash "$SCRIPT_DIR/manual.bootstrap.sh" "$INSTALL_DIR" 2> >(raw_logs_to_logs)
