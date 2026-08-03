#!/usr/bin/env bash

[[ -v VULPIX_LOG ]] || fatal 'no VULPIX_LOG'

# clear logs on init
rm -fr "$VULPIX_LOG"
mkdir -p "$VULPIX_LOG" "$VULPIX_LOG/tasks"

# bridge between programming and user interface ---------------------------------------------------

# seperates logs by $TASK env var (if not set, default to main context)
_log() {
  local log_level=$1
  local message=$2
  local script_name=$(basename $0)
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")

  local log_file='main.log'
  [[ -v "$TASK" ]] && local log_file="tasks/$TASK.log"
  log_file="$VULPIX_LOG/$log_file"

  echo "$timestamp [$log_level] [$script_name] $message" >>"$log_file"

  # return message for printing (no newline if ends in \)
  message="${TASK:+$TASK: }$message"
  [[ "$message" == *'\' ]] &&
    printf "${message%?}" ||
    echo "$message"
}

# programming interface ---------------------------------------------------------------------------

debug() {
  if [[ -v DEBUG ]]; then
    _log DEBUG "$*" | sed 's/^/DEBUG: /' >&2
  fi
}

info() {
  _log INFO "$*" | colorize "$BLUE" >&2
}

warn() {
  _log WARN "$*" | colorize "$YELLOW" >&2
}

success() {
  _log SUCCESS "$*" | colorize "$GREEN" >&2
}

err() {
  _log ERROR "$*" | colorize "$RED" >&2
}

fatal() {
  _log FATAL "$*" | colorize "$RED" >&2
  exit 1
}

# use to log internal output or external command output
output() {
  [[ $# -gt 0 ]] &&
    _log OUTPUT "$*" # allow output to be forwarded to stdout

  # also from stdin
  if [[ -p /dev/stdin ]]; then
    while IFS= read -r line; do
      _log OUTPUT "$line" # allow output to be forwarded to stdout
    done
  fi
}

# use to log user input
log_input() {
  _log INPUT "$*" >/dev/null # do not reprint user input
}

# cli/ui interface --------------------------------------------------------------------------------

# TODO
