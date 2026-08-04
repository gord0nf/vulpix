#!/usr/bin/env bash

[[ -v VULPIX_LOG ]] || fatal 'logging.sh requires VULPIX_LOG'

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
  [[ -v TASK ]] && local log_file="tasks/$TASK.log"
  log_file="$VULPIX_LOG/$log_file"

  echo "$timestamp [$log_level] [$script_name] $message" >>"$log_file"

  # return message for printing (no newline if ends in \)
  [[ "$message" == *'\' ]] &&
    printf "${message%?}" ||
    echo "$message"
}

# programming interface ---------------------------------------------------------------------------

_log_interface() {
  local log_level=$1
  local color=$2
  shift && shift

  local log_pipe=""
  [[ -n "$color" ]] && log_pipe+=' | colorize "$color"'
  [[ -v TASK ]] && log_pipe+=" | sed 's/^/[${TASK}] /'"

  # from args
  if [[ $# -gt 0 ]]; then
    eval "_log '$log_level' '$*' $log_pipe"
  fi

  # also from stdin
  if [[ -p /dev/stdin ]]; then
    while IFS= read -r line; do
      eval "_log '$log_level' '$line' $log_pipe"
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

# use to log internal output or external command output
output() {
  _log_interface 'OUTPUT' '' "$@" </dev/stdin
}

# use to log user input
log_input() {
  # do not reprint user input
  _log_interface 'INPUT' '' "$@" >/dev/null </dev/stdin
}

# cli/ui interface --------------------------------------------------------------------------------

# TODO
