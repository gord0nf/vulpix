#/usr/bin/env bash

# a task is a process that has seperate logging and is run in a forked bash subprocess (optionally
# in parallel).

[[ -v VULPIX_LOG ]] || fatal 'logging.sh requires VULPIX_LOG'
[[ -v MAX_PROCESSES ]] || fatal 'logging.sh requires MAX_PROCESSES'
[[ "$MAX_PROCESSES" =~ ^[0-9]+$ ]] || fatal 'invalid MAX_PROCESSES'
[[ "$MAX_PROCESSES" -ge 1 ]] || fatal 'MAX_PROCESSES must at least be 1'

# source of truth between processes for the tasks that are running --------------------------------

TASK_FILE="$VULPIX_TMP/running_tasks.list"
TASK_LOCK_TIMEOUT=30 # seconds

# clean on init
mkdir -p "$VULPIX_TMP"
echo >"$TASK_FILE"

_lock_acquire() {
  exec {LOCKFD}<"$TASK_FILE" || fatal '_lock_acquire: could not establish lock'
  flock -x -w "$TASK_LOCK_TIMEOUT" $LOCKFD || fatal '_lock_acquire: failed'
}

_lock_release() {
  test "$LOCKFD" || fatal '_lock_release: file not locked'
  flock -u $LOCKFD && exec {LOCKFD}>&- && unset LOCKFD || fatal '_lock_release: failed'
}

_load_running_tasks() {
  _lock_acquire
  load_array_by_line running_tasks <"$TASK_FILE"
  debug "loaded running tasks: ${running_tasks[@]}"
}

_set_running_tasks() {
  debug "setting running tasks: ${running_tasks[@]}"
  printf '%s\n' "${running_tasks[@]}" >"$TASK_FILE"
  _lock_release
}

# run task funcs ----------------------------------------------------------------------------------

TASK_POLL_PERIOD=1 # seconds

_task_create() {
  # wait until there are less tasks than MAX_PROCESSES
  while true; do
    _load_running_tasks
    if [[ "${#running_tasks[@]}" -lt "$MAX_PROCESSES" ]]; then break; fi
    _lock_release
    sleep $TASK_POLL_PERIOD
  done

  running_tasks+=("$TASK_NAME")
  _set_running_tasks
}

_task_remove() {
  _load_running_tasks
  array_remove_element running_tasks "$TASK_NAME"
  _set_running_tasks
}

_task_handle_output() {
  prefix_output "  [$TASK_NAME] "
}

_task_main() {
  (
    export LOG_FILE="tasks/$TASK_NAME.log"
    info 'running new task'
    log_stdout
    trap '[ $? -eq 0 ] && success "success" || err "failure"' EXIT
    "$@"
  ) |& _task_handle_output >&2 # also redirect stdout to stderr because it shouldn't be logged in the main context
}

# exported functions ------------------------------------------------------------------------------

# starts task syncronously
run_foreground_task() {
  export TASK_NAME="$1"
  shift

  _task_create # stops execution until task can start
  debug "task start '$TASK_NAME'"

  _task_main "$@"
  exit_status=$?
  _task_remove

  debug "task done '$TASK_NAME'"
  unset TASK_NAME
  return $exit_status
}

# starts task asyncronously
run_background_task() {
  export TASK_NAME="$1"
  shift

  _task_create # stops execution until task can start
  (
    debug "task start '$TASK_NAME'"
    _task_main "$@"
    exit_status=$?
    _task_remove
    debug "task done '$TASK_NAME'"
    return $exit_status
  ) &

  unset TASK_NAME
}

# number of times to verify that there are 0 tasks running to make sure that no more are being spawned
AWAIT_VERIFIES=3 # TODO: there's probably a better way...

await_tasks() {
  local n_verifies=0
  while true; do
    _load_running_tasks
    _lock_release

    debug "await_tasks, task count: ${#running_tasks[@]}"
    [[ "${#running_tasks[@]}" -eq 0 ]] && n_verifies=$((n_verifies + 1)) || n_verifies=0
    if [[ "$n_verifies" -eq "$AWAIT_VERIFIES" ]]; then break; fi

    sleep $TASK_POLL_PERIOD
  done
}
