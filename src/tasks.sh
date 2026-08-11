#/usr/bin/env bash

# a task is a process that has seperate logging and is run in a forked bash subprocess (optionally
# in parallel).

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
source_script "$SCRIPT_DIR/mutex.sh"

[[ -v VULPIX_LOG ]] || fatal 'tasks.sh requires VULPIX_LOG'
[[ -v VULPIX_TMP ]] || fatal 'tasks.sh requires VULPIX_TMP'
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
TASK_MUTEX='TASKS'

# clean on init
mkdir -p "$VULPIX_TMP"
echo >"$TASK_FILE"

_load_running_tasks() {
  mutex_lock $TASK_MUTEX
  load_array_by_line running_tasks <"$TASK_FILE"
  debug "loaded running tasks: ${running_tasks[@]}"
}

_set_running_tasks() {
  debug "setting running tasks: ${running_tasks[@]}"
  printf '%s\n' "${running_tasks[@]}" >"$TASK_FILE"
  mutex_unlock $TASK_MUTEX
}

# stdout/err while rendering ui to prevent conflicts ----------------------------------------------

RENDER_MUTEX='RENDER'

render() {
  mutex_lock $RENDER_MUTEX
  "$@"
  mutex_unlock $RENDER_MUTEX
}

# got to prevent normal logging while jumping around the terminal to render ui
_buffer_until_not_rendering() {
  while IFS= read -r line; do
    render echo "$line"
  done
}

open_render_output_nonconflict() {
  # save og stderr/stdout
  exec 3>&1
  exec 4>&2
  exec 1> >(output | _buffer_until_not_rendering >&3)
  exec 2> >(_buffer_until_not_rendering >&4)
}
close_render_output_nonconflict() {
  mutex_await_free $RENDER_MUTEX
  exec 1>&3
  exec 2>&4
  exec 3>&-
  exec 4>&-
}

# special task section ui funcs -------------------------------------------------------------------

# uses tput for header/footer (see https://www.reddit.com/r/commandline/comments/14i82e/comment/c7ddcfs/)

_print_header() {
  printf " < ${1^^} >%$((COLUMNS - "${#1}" - 5))s\n" | tr ' ' '=' | colorize "$BOLD$CYAN"
}

_jump_to_footer_index() {
  local index=$1
  if ((index > TASK_SECTION_FOOTER)); then
    return 1
  fi
  tput cup $((LINES - TASK_SECTION_FOOTER - 1 + index)) 0 # - 1 for footer title
}

_init_task_section_screen() {
  # open alt screen
  tput smcup
  clear

  # init title/footer stuff
  tput csr 1 $((LINES - TASK_SECTION_FOOTER - 2)) # - 2 for index offbyone + footer title
  tput cup 0 0 && _print_header "$section_name"   # title
  if [[ "$TASK_SECTION_FOOTER" -gt 0 ]]; then
    _jump_to_footer_index 0
    _print_header 'tasks' # footer
  fi
  tput cup 1 0
}

_reprint_footer() {
  tput sc
  _jump_to_footer_index 1
  for ((i = 0; i < TASK_SECTION_FOOTER; i++)); do
    if ((i == 0 && "${#running_tasks[@]}" == 0)); then
      printf 'no tasks running...'
    elif ((i + 1 == TASK_SECTION_FOOTER && i + 1 < ${#running_tasks[@]})); then
      printf '...'
    elif ((i < "${#running_tasks[@]}")); then
      printf "%s (${YELLOW}running${RESET})" "${running_tasks[$i]}"
    fi
    printf "$(tput el)\n"
  done
  tput rc
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
  info "opening section '$section_name' in alt screen..."

  # init logging (need to prevent logging while rendering ui stuff)
  close_stdout_log
  open_render_output_nonconflict

  render _init_task_section_screen >&3 || {
    end_task_section
    err '_init_task_section_screen failed'
    warn 'no task section ui'
    return 1
  }
  trap end_task_section SIGINT SIGTERM
}

end_task_section() {
  if ${TASK_SECTION:-false}; then
    close_render_output_nonconflict
    open_stdout_log

    tput csr 0 $(tput lines) >&3
    tput rmcup >&3

    export TASK_SECTION=false
  fi
}

_update_task_section_footer() {
  if ${TASK_SECTION:-false} && [[ "$TASK_SECTION_FOOTER" -gt 0 ]]; then
    render _reprint_footer >&3
  fi
}

_task_handle_output() {
  ${TASK_SECTION:-false} &&
    cat >/dev/null ||
    prefix_output "  $TASK_NAME "
}

# task failure tracking ---------------------------------------------------------------------------

FAILED_TASKS_LIST="$VULPIX_LOG/failed_tasks.list"

mark_task_failed() {
  [[ $# -eq 1 ]]
  echo "$1" >>"$FAILED_TASKS_LIST"
}

# writes failed_tasks
get_failed_tasks() {
  failed_tasks=()
  [[ -f "$FAILED_TASKS_LIST" ]] || return
  if [[ $# -gt 0 ]]; then
    load_array_by_line_from_command failed_tasks \
      grep "$@" "$FAILED_TASKS_LIST"
  else
    load_array_by_line failed_tasks <"$FAILED_TASKS_LIST"
  fi
}

check_task_failed() {
  [[ $# -eq 1 ]]
  [[ -f "$FAILED_TASKS_LIST" ]] || return 1
  get_failed_tasks -xF "$1" || return 1
  [[ "${#failed_tasks[@]}" -ne 0 ]]
}

# run task funcs ----------------------------------------------------------------------------------

TASK_POLL_PERIOD=1 # seconds
task_queue=()      # NOTE: this is only for the current process, while tasks can span multiple subprocesses...

_log_task_done() {
  local taskname="$1" exit_status="$2"
  [[ "$exit_status" -eq 0 ]] || mark_task_failed "$taskname"
  if ${TASK_SECTION:-false}; then
    [[ "$exit_status" -eq 0 ]] &&
      printf "%s (${GREEN}done${RESET})\n" "$(_log 'SUCCESS' "$taskname")" >&2 ||
      printf "%s (${RED}failed${RESET})\n" "$(_log 'ERROR' "$taskname")" >&2
  else
    debug "task done '$TASK_NAME' (exit: $exit_status)"
  fi
}

_task_create() {
  # wait until there are less tasks than MAX_PROCESSES
  task_queue+=("$TASK_NAME")
  while true; do
    _load_running_tasks
    if [[ "${#running_tasks[@]}" -lt "$MAX_PROCESSES" ]]; then break; fi
    mutex_unlock $TASK_MUTEX
    sleep $TASK_POLL_PERIOD
  done

  running_tasks+=("$TASK_NAME")
  _update_task_section_footer
  _set_running_tasks
  array_remove_element task_queue "$TASK_NAME"
}

_task_remove() {
  _load_running_tasks
  array_remove_element running_tasks "$TASK_NAME"
  _update_task_section_footer
  _set_running_tasks
}

_task_main() {
  (
    export LOG_FILE="tasks/$TASK_NAME.log"
    info 'running new task'
    # no need for open_stdout_log(), because its maintained from parent
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
  exit_status=0
  _task_main "$@" || exit_status=$?
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
    exit_status=0
    _task_main "$@" || exit_status=$?
    _task_remove
    _log_task_done "$TASK_NAME" $exit_status
    return $exit_status
  ) &

  unset TASK_NAME
}

# NOTE: await_tasks relis on task_queue, which only represents the current process (it's more a 'good enough' solution)
await_tasks() {
  local n=
  while true; do
    if [[ "${#task_queue[@]}" -eq 0 ]]; then break; fi
    sleep $TASK_POLL_PERIOD
  done
  while true; do
    _load_running_tasks
    n="${#running_tasks[@]}"
    mutex_unlock $TASK_MUTEX
    if [[ "$n" -eq 0 ]]; then break; fi
    sleep $TASK_POLL_PERIOD
  done
}
