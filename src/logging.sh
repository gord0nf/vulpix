#!/usr/bin/env bash

[[ -v VULPIX_LOG ]] || fatal 'logging.sh requires VULPIX_LOG'

mkdir -p "$VULPIX_LOG" "$VULPIX_TMP"

# clear logs on init
clear_logs() {
  [[ -v LOG_FILE && -f "$VULPIX_LOG/$LOG_FILE" ]] && current_log=true || current_log=false
  ! $current_log || mv "$VULPIX_LOG/$LOG_FILE" "$VULPIX_TMP/$LOG_FILE"
  rm -fr "$VULPIX_LOG"
  mkdir -p "$VULPIX_LOG"
  ! $current_log || mv "$VULPIX_TMP/$LOG_FILE" "$VULPIX_LOG/$LOG_FILE"
}

# log file bridge ---------------------------------------------------------------------------------

# uses LOG_FILE env var for relative path to log file, defaulting to main.log
_log() {
  local log_level=$1
  local message=$2
  local script_name=$(basename $0)
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  local log_file="$VULPIX_LOG/${LOG_FILE:-main.log}"

  if ! [[ -v LOG_REPLAY ]]; then
    mkdir -p "$(dirname "$log_file")"
    echo "$timestamp '$script_name' [$log_level] $message" >>"$log_file"
  fi
  echo "$message" # return message for printing
}

# programming interface ---------------------------------------------------------------------------

output() {
  while IFS= read -r line || [[ -n "$line" ]]; do
    _log 'OUTPUT' "$line"
  done </dev/stdin
}

open_stdout_log() {
  exec 3>&1 # open fd 3 for bypassing output logs (for ui stuff)
  exec 1> >(output >&3)
}
close_stdout_log() {
  exec 1>&3
  exec 3>&-
}

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

# stuff for replaying logs ------------------------------------------------------------------------

# write to log_type and log_message
parse_log_line() {
  local line=$1
  [[ "$line" == *'['*']'* ]] || return 1
  line="${line#*'['}"
  log_type="${line%%']'*}"
  log_type=${log_type,,} # lowercase
  log_message="${line#*']'}"
}

replay_logs() {
  export LOG_REPLAY=
  local log_type= message=
  while IFS= read -r line; do
    if parse_log_line "$line"; then
      if [[ "$log_type" == 'error' ]]; then log_type='err'; fi
      if function_exists "$log_type"; then
        "$log_type" "$(trimstring "$log_message")" </dev/null
        continue
      fi
    fi
    echo "$line"
  done
  unset LOG_REPLAY
}

replay_log_file() {
  [[ $# -eq 1 ]]
  [[ -f "$VULPIX_LOG/$1" ]] || return 1
  replay_logs <"$VULPIX_LOG/$1"
}

enum_log_files() {
  [[ $# -eq 1 ]]
  load_array_by_line_from_command $1 find "$VULPIX_LOG" -type f -name '*.log' -printf "%P\n"
}
