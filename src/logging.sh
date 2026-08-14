#!/usr/bin/env bash

[[ -v VULPIX_LOG ]] || fatal 'logging.sh requires VULPIX_LOG'
mkdir -p "$VULPIX_LOG" "$VULPIX_TMP"

# programming interface ---------------------------------------------------------------------------

_start_log_context() {
  export LOG_FILE="$VULPIX_LOG/$1.log"
  mkdir -p "$(dirname "$LOG_FILE")"
  touch "$LOG_FILE"

  exec 3>&1                          # save stdout
  exec 4>&2                          # save stderr
  exec 1> >(tee -a "$LOG_FILE") 2>&1 # redirect both stdout and stderr to logs+stdout
}

end_log_context() {
  exec 1>&3
  exec 2>&4
  exec 3>&-
  exec 4>&-
  unset LOG_FILE
}

start_log_context() {
  [[ $# -eq 1 ]]
  end_log_context # clear existing
  _start_log_context "$1"
}

_log() {
  local log_level=$1 message=$2 color=$3
  [[ -v LOG_REPLAY ]] || echo "[$log_level] $message" >>"$LOG_FILE"
  printf "${color}%s${RESET}\n" "$message"
}

debug() {
  if [[ -v DEBUG ]]; then
    _log 'DEBUG' "$*" "$PINK" >&4
  fi
}

info() {
  _log 'INFO' "$*" "$BLUE" >&3
}

warn() {
  _log 'WARN' "$*" "$YELLOW" >&4
}

success() {
  _log 'SUCCESS' "$*" "$GREEN" >&3
}

err() {
  _log 'ERR' "$*" "$RED" >&4
}

fatal() {
  _log 'FATAL' "$*" "$RED" >&4
  exit 1
}

# stuff for replaying logs ------------------------------------------------------------------------

replay_logs() {
  export LOG_REPLAY=
  local log_type= message=
  while IFS= read -r line; do
    if [[ "$line" =~ ^\[([a-zA-Z]+)\][[:space:]](.*)$ ]]; then
      log_type=${BASH_REMATCH[1]} message=${BASH_REMATCH[2]}
      if function_exists "$log_type"; then
        "$log_type" "$message" </dev/null
        continue
      fi
    fi
    echo "$line"
  done
  unset LOG_REPLAY
}

replay_log_file() {
  [[ $# -eq 1 ]]
  [[ -f "$VULPIX_LOG/$1.log" ]] || return 1
  replay_logs <"$VULPIX_LOG/$1.log"
}

enum_log_files() {
  [[ $# -eq 1 ]]
  local files=$(
    find "$VULPIX_LOG" -type f \( -name '*.log' -a -not -path "$FLOATING_LOG_FILE" \) -printf "%P\n" |
      sed 's/\.[^.]*$//'
  )
  load_array_by_line "$1" <<<"$files"
}

# initial logs before start_log_context (aka floating logs) ---------------------------------------

FLOATING_LOG='init'
FLOATING_LOG_FILE="$VULPIX_LOG/$FLOATING_LOG.log"
rm -f "$FLOATING_LOG_FILE"

# before start_log_context is explicitly called, use FLOATING_LOG
_start_log_context "$FLOATING_LOG"

clear_logs() {
  if [[ -f "$FLOATING_LOG_FILE" ]]; then local tmpflog="$VULPIX_TMP/f.log"; fi
  ! [[ -v tmpflog ]] || mv "$FLOATING_LOG_FILE" "$tmpflog"
  rm -fr "$VULPIX_LOG"
  mkdir -p "$VULPIX_LOG"
  ! [[ -v tmpflog ]] || mv "$tmpflog" "$FLOATING_LOG_FILE"
}
