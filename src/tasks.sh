# a task has seperate logging and is run in a bash subprocess
run_task() {
  local name="$1"
  shift

  debug "running task '$name'"
  (
    export TASK="$name"
    "$@"
  )
}
