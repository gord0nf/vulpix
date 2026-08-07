#!/usr/bin/env bash

[[ -v VULPIX_LOG ]] || fatal 'logging.sh requires VULPIX_LOG'

# clear logs on init
rm -fr "$VULPIX_LOG"

# log file bridge ---------------------------------------------------------------------------------

# uses LOG_FILE env var for relative path to log file, defaulting to main.log
_log() {
  local log_level=$1
  local message=$2
  local script_name=$(basename $0)
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  local log_file="$VULPIX_LOG/${LOG_FILE:-main.log}"
  mkdir -p "$(dirname "$log_file")"

  echo "$timestamp [$log_level] [$script_name] $message" >>"$log_file"
  echo "$message" # return message for printing
}

# programming interface ---------------------------------------------------------------------------

_log_interface() {
  local log_level=$1
  local color=$2
  shift && shift

  # from args
  if [[ $# -gt 0 ]]; then
    _log "$log_level" "$*" | colorize "$color"
  fi

  # also from stdin
  if [[ -p /dev/stdin ]]; then
    while IFS= read -r line; do
      _log "$log_level" "$line" | colorize "$color"
    done
  fi
}

debug() {
  if [[ -v DEBUG ]]; then
    _log_interface 'DEBUG' "$PINK" "$@" >&2 </dev/stdin
  fi
}

info() {
  _log_interface 'INFO' "$BLUE" "$@" >&2 </dev/stdin
}

warn() {
  _log_interface 'WARN' "$YELLOW" "$@" >&2 </dev/stdin
}

success() {
  _log_interface 'SUCCESS' "$GREEN" "$@" >&2 </dev/stdin
}

err() {
  _log_interface 'ERROR' "$RED" "$@" >&2 </dev/stdin
}

fatal() {
  _log_interface 'FATAL' "$RED" "$@" >&2 </dev/stdin
  exit 1
}
