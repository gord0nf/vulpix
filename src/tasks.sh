#/usr/bin/env bash

# a task is a process that has seperate logging and is run in a forked bash subprocess (optionally
# in parallel).

[[ -v VULPIX_LOG ]] || fatal 'tasks.sh requires VULPIX_LOG'
[[ -v MAX_PROCESSES ]] || fatal 'tasks.sh requires MAX_PROCESSES'
[[ "$MAX_PROCESSES" =~ ^[0-9]+$ ]] || fatal 'invalid MAX_PROCESSES'
[[ "$MAX_PROCESSES" -ge 1 ]] || fatal 'MAX_PROCESSES must at least be 1'

[[ -z "$TASK_SECTION_FOOTER" || "$TASK_SECTION_FOOTER" =~ ^[0-9]+$ ]] || fatal 'invalid TASK_SECTION_FOOTER'

# conditions to disable TASK_SECTION ui
if ! [ -t 0 ] || [ -z "$TERM" ]; then
  info 'task section ui disabled' &>/dev/null
  export OVERRIDE_TASK_SECTION=false
fi

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

# special task section ui funcs -------------------------------------------------------------------

# uses tput for header/footer (see https://www.reddit.com/r/commandline/comments/14i82e/comment/c7ddcfs/)

_print_header() {
  printf " < ${1^^} >%$((COLUMNS - "${#1}"))s\n" | tr ' ' '=' | colorize "$BOLD$CYAN"
}

_jump_to_footer_index() {
  local index=$1
  if ((index > TASK_SECTION_FOOTER)); then
    return 1
  fi
  tput cup $((LINES - TASK_SECTION_FOOTER - 1 + index)) 0 >&3 # - 1 for footer title
}

begin_task_section() {
  [[ $# -eq 1 ]]
  local section_name=$1
  export TASK_SECTION=${OVERRIDE_TASK_SECTION:-true}
  $TASK_SECTION || return 1

  export LINES=$(tput lines)
  export COLUMNS=$(tput cols)

  if [[ -z "$TASK_SECTION_FOOTER" ]]; then
    local half_screen_lines=$((LINES / 2))
    export TASK_SECTION_FOOTER=$((MAX_PROCESSES < half_screen_lines ? MAX_PROCESSES : half_screen_lines))
    debug "TASK_SECTION_FOOTER=$TASK_SECTION_FOOTER"
  fi
  if ! ((TASK_SECTION_FOOTER < LINES)); then
    warn 'terminal height less than TASK_SECTION_FOOTER height, so no task section ui'
    export TASK_SECTION=false
    return 1
  fi

  # alternate screen
  info "opening section '$section_name' in alt screen..."
  tput smcup >&3 && clear
  trap 'tput rmcup >&3' EXIT SIGINT SIGTERM

  # init title and footer
  tput csr 1 $((LINES - TASK_SECTION_FOOTER - 2)) >&3 # - 2 for index offbyone + footer title
  tput cup 0 0 && _print_header "$section_name" >&3   # title
  if [[ "$TASK_SECTION_FOOTER" -gt 0 ]]; then
    _jump_to_footer_index 0
    _print_header 'tasks' >&3 # footer
  fi
  tput cup 1 0 >&3
}

end_task_section() {
  if ${TASK_SECTION:-false}; then
    tput csr 0 $(tput lines) >&3
    tput rmcup >&3
    export TASK_SECTION=false
  fi
}

_update_task_section_footer() {
  if ${TASK_SECTION:-false} && [[ "$TASK_SECTION_FOOTER" -gt 0 ]]; then
    tput sc >&3
    _jump_to_footer_index 1
    for ((i = 0; i < TASK_SECTION_FOOTER; i++)); do
      if ((i == 0 && "${#running_tasks[@]}" == 0)); then
        printf 'no tasks running...' >&3
      elif ((i + 1 == TASK_SECTION_FOOTER && i + 1 < ${#running_tasks[@]})); then
        printf '...' >&3
      elif ((i < "${#running_tasks[@]}")); then
        printf "${running_tasks[$i]} (${YELLOW}running${RESET})" >&3
      fi
      printf "$(tput el)\n" >&3
    done
    tput rc >&3
  fi
}

_log_task_done() {
  local taskname="$1" exit_status="$2"
  if ${TASK_SECTION:-false}; then
    [[ "$exit_status" -eq 0 ]] &&
      printf "%s (${GREEN}done${RESET})\n" "$(_log 'SUCCESS' "$taskname")" ||
      printf "%s (${RED}failed${RESET})\n" "$(_log 'ERROR' "$taskname")"
  else
    debug "task done '$TASK_NAME' (exit: $exit_status)"
  fi
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
  _update_task_section_footer
  _set_running_tasks
}

_task_remove() {
  _load_running_tasks
  array_remove_element running_tasks "$TASK_NAME"
  _update_task_section_footer
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
  ) 2>&1 | _task_handle_output >&2 # also redirect stdout to stderr because it shouldn't be logged in the main context
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
  _log_task_done "$TASK_NAME" $exit_status

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
    _log_task_done "$TASK_NAME" $exit_status
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
