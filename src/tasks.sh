#/usr/bin/env bash

# a task is a process that has seperate logging and is run in a forked bash subprocess (optionally
# in parallel).

TASK_LOCKFILE="$VULPIX_TMP/tasks.lock"
TASK_DIR="$VULPIX_TMP/tasks"
MAX_PROCESSES=${MAX_PROCESSES:-5}

# clean tasks on init
rm -fr "$TASK_DIR"
mkdir -p "$TASK_DIR"

_await_tasks_lock() {
  while [ -f "$TASK_LOCKFILE" ]; do
    sleep 1
  done
}

_lock_tasks() {
  ! [ -f "$TASK_LOCKFILE" ] || fatal "_lock_tasks: could not create lock (possible race condition)"
  touch "$TASK_LOCKFILE"
}

_unlock_tasks() {
  [ -f "$TASK_LOCKFILE" ] || fatal "_unlock_tasks: tasks not locked"
  rm "$TASK_LOCKFILE"
}

_count_tasks() {
  [ -f "$TASK_LOCKFILE" ] || fatal '_count_tasks: tasks not locked'
  find "$TASK_DIR" -maxdepth 1 -type f | wc -l
}

_add_task() {
  [ -f "$TASK_LOCKFILE" ] || fatal '_add_task: tasks not locked'
  touch "$TASK_DIR/$1"
}

_remove_task() {
  [ -f "$TASK_LOCKFILE" ] || fatal '_add_task: tasks not locked'
  [ -f "$TASK_DIR/$1" ] || fatal '_add_task: no such task'
  rm "$TASK_DIR/$1"
}

_task_init() {
  local taskname="$1"

  # wait until there are less tasks than MAX_PROCESSES
  while true; do
    _await_tasks_lock
    _lock_tasks
    [[ "$(_count_tasks)" -lt "$MAX_PROCESSES" ]] && break
    _unlock_tasks
    sleep 1
  done

  # add task
  _add_task "$taskname"
  _unlock_tasks

  # set log context and init log
  export TASK="$taskname"
  warn 'running new task'
}

_task_cleanup() {
  status=$?

  # cleanup task
  _await_tasks_lock
  _lock_tasks
  _remove_task "$TASK"
  _unlock_tasks

  # log exit status and reset log context
  [[ $status -eq 0 ]] && success 'success' || err 'failure'
  unset TASK

  return $status
}

# starts task syncronously
run_foreground_task() {
  _task_init "$1" # stops execution until task can start
  shift
  ("$@")
  _task_cleanup
}

# starts task asyncronously
run_background_task() {
  _task_init "$1" # stops execution until task can start
  shift
  (
    trap _task_cleanup EXIT
    "$@"
  ) &
  unset TASK # reset log context after subprocess has been forked
}

AWAIT_VERIFIES=3 # number of times to verify that there are 0 tasks running to make sure that no more are being spawned

await_tasks() {
  n_verifies=0

  while true; do
    _await_tasks_lock
    _lock_tasks
    n="$(_count_tasks)"
    _unlock_tasks

    [[ "$n" -eq 0 ]] && n_verifies=$((n_verifies + 1))
    [[ "$n_verifies" -eq "$AWAIT_VERIFIES" ]] && break

    sleep 1
  done
}
