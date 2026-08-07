#/usr/bin/env bash

# a task is a process that has seperate logging and is run in a forked bash subprocess (optionally
# in parallel).

[[ -v VULPIX_LOG ]] || fatal 'logging.sh requires VULPIX_LOG'
[[ -v MAX_PROCESSES ]] || fatal 'logging.sh requires MAX_PROCESSES'
[[ "$MAX_PROCESSES" =~ ^[0-9]+$ ]] || fatal 'invalid MAX_PROCESSES'
[[ "$MAX_PROCESSES" -ge 1 ]] || fatal 'MAX_PROCESSES must at least be 1'

TASK_LOCKFILE="$VULPIX_TMP/tasks.lock"
TASK_DIR="$VULPIX_TMP/tasks"

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

_task_create() {
  # wait until there are less tasks than MAX_PROCESSES
  while true; do
    _await_tasks_lock
    _lock_tasks
    [[ "$(_count_tasks)" -lt "$MAX_PROCESSES" ]] && break
    _unlock_tasks
    sleep 1
  done

  _add_task "$1"
  _unlock_tasks
}

_task_cleanup() {
  status=$?
  [[ -v TASK_NAME ]] || fatal '_task_cleanup: requires TASK_NAME'

  # cleanup task
  _await_tasks_lock
  _lock_tasks
  _remove_task "$TASK_NAME"
  _unlock_tasks

  # log exit status
  [[ $status -eq 0 ]] && success 'success' || err 'failure'

  return $status
}

# starts task syncronously
run_foreground_task() {
  local task_name="$1" prefix="  [$1] "
  shift

  _task_create "$task_name" # stops execution until task can start

  (
    export TASK_NAME="$task_name"
    export LOG_FILE="tasks/$TASK_NAME"
    info 'running new task'
    trap _task_cleanup EXIT
    "$@"
  ) \
    > >(prefix_output "$prefix") 2> >(prefix_output "$prefix" >&2)
}

# starts task asyncronously
run_background_task() {
  local task_name="$1" prefix="  [$1] "
  shift

  _task_create "$task_name" # stops execution until task can start

  (
    export TASK_NAME="$task_name"
    export LOG_FILE="tasks/$TASK_NAME"
    info 'running new task'
    trap _task_cleanup EXIT
    "$@"
  ) \
    > >(prefix_output "$prefix") 2> >(prefix_output "$prefix" >&2) \
    & # background process
}

# number of times to verify that there are 0 tasks running to make sure that no more are being spawned
AWAIT_VERIFIES=3 # TODO: there's probably a better way...

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
