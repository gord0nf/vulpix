#!/usr/bin/env bash

# utility functions for manual installs. should be sourced before running a package's manual.sh.

# pipe output of raw logs/output and transform into logs
# if starts with standard prefix, like INFO: ..., it's a raw log and will call corresponding func
# else, just a normal output log
# (make sure to redirect stderr if used for logging)
raw_logs_to_logs() {
  while IFS= read -r line; do
    log_type=${line%%:*}
    log_type=${log_type,,} # lowercase
    [[ "$log_type" == 'error' ]] && log_type='err'
    if function_exists "$log_type"; then
      log=${line#*:}
      "$log_type" "$(trimstring "$log")"
    else
      output "$line"
    fi
  done
}
