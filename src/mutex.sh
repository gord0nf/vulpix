#!/usr/bin/env bash

[[ -v VULPIX_TMP ]] || fatal 'mutex.sh requires VULPIX_TMP'

MUTEX_DIR="$VULPIX_TMP/mutex"
LOCK_TIMEOUT=30 # seconds

rm -fr "$MUTEX_DIR"
mkdir -p "$MUTEX_DIR"

mutex_lock() {
  [[ $# -eq 1 ]]
  local mutex_name=$1 mutex_file="$MUTEX_DIR/$1"
  exec {LOCK_FD}>"$mutex_file" || fatal "_mutex_lock: could not establish lock ($mutex_file)"
  export "$mutex_name"="$LOCK_FD"
  flock -x -w "$LOCK_TIMEOUT" ${!mutex_name} || fatal "_lock_acquire: failed ($mutex_name)"
}

mutex_unlock() {
  [[ $# -eq 1 ]]
  local mutex_name=$1
  [[ -v "$mutex_name" ]] || fatal "_mutex_lock_release: file not locked ($mutex_name)"
  flock -u ${!mutex_name} &&
    eval "exec {$mutex_name}>&-" &&
    unset "$mutex_name" ||
    fatal '_lock_release: failed'
}

mutex_await_free() {
  [[ $# -eq 1 ]]
  local mutex_name=$1 mutex_file="$MUTEX_DIR/$1"
  while ! flock -w 0 -n "$mutex_file" true 2>/dev/null; do
    sleep 1
  done
}
