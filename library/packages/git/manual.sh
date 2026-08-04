#!/usr/bin/env bash

INSTALL_DIR="$1"
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

[[ -z "$INSTALL_DIR" ]] && fatal 'no install dir specified'

_windows() {
  local install_dir=$(convert_path_if_needed --windows "$INSTALL_DIR")

  # NOTE: let powershell snippet return line seperated bin paths to stdout
  # TODO: actually test this...
  powershell "
      \$binaryDirs = & '$SCRIPT_DIR/manual.bootstrap.ps1' -InstallDir '$install_dir' 6>&2
      if ((\? -ne 0) -or (\$binaryDirs.Count -eq 0)) { exit 1; }
      \$binaryDirs -join \"\`n\" # convert to bash-usable stdout
  " 2> >(raw_logs_to_logs)
}

if [[ $OS != 'windows' ]]; then
  err 'manual git install is not supported on linux (would have to build from source)'
  fatal 'you must install git using your os package manager'
fi

_windows || fatal 'install failed'
