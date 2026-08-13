#!/usr/bin/env bash

INSTALL_DIR="$(convert_path_if_needed --windows "$INSTALL_DIR")"
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
BOOTSTRAP_SCRIPT="$SCRIPT_DIR/manual.bootstrap.ps1"

[[ -n "$INSTALL_DIR" ]] || fatal 'no install dir specified'

if [[ $OS != 'windows' ]]; then
  fatal 'msys2 is a windows tool. not supported on linux.'
fi

# NOTE: let powershell snippet return line seperated bin paths to stdout
powershell -Command \
  "\$binaryDirs = & '$BOOTSTRAP_SCRIPT' -InstallDir '$INSTALL_DIR' 6>&2
  if ((\$\? -ne 0) -or (\$binaryDirs.Count -eq 0)) { exit 1; }
  \$binaryDirs -join \"\`n\""
