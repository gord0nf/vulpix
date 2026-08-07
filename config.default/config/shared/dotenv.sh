#!/usr/bin/env bash

# interface for variables in global .env (with += syntax for appending)

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
export GLOBAL_ENV=$(realpath "$SCRIPT_DIR/../../.env")

global_env_unset() {
  [[ $# -eq 1 ]]
  local variable=$1
  unset "$variable"
  sed -i "/^$variable=/d" "$GLOBAL_ENV"
}

global_env_set() {
  [[ $# -eq 2 ]]
  local variable=$1 value=$2
  global_env_unset "$variable"
  export "$variable"="$value"
  echo "$variable=\"$value\"" >>"$GLOBAL_ENV"
}

global_env_append() {
  [[ $# -eq 2 ]]
  local variable=$1 value=$2
  export "$variable"="${!variable}$value"

  local existing_value=$(grep -oE -m 1 '^'$variable'\+=.*$' "$GLOBAL_ENV")
  existing_value=${existing_value#*=}
  if [[ -n "$existing_value" ]]; then
    sed -i '/^'$variable'+=/d' "$GLOBAL_ENV" # remove existing (we already saved the value)
  fi
  [[ "$existing_value" =~ \"(.*)\"|\'(.*)\' ]] && existing_value=${BASH_REMATCH[1]} # remove quotes
  echo "$variable+=\"$existing_value$value\"" >>"$GLOBAL_ENV"
}

# specifically for adding to PATH in global env, if it's not already there
global_env_add_path() {
  [[ $# -eq 1 || $# -eq 2 ]]
  local p=$(convert_path_if_needed --unix "$1") # global PATH stored in unix format
  local force=false
  if [[ $# -eq 2 ]] && [[ "$2" == '--force' ]]; then force=true; fi
  if ! $force; then
    [[ -d "$p" ]] || return 1 # ensure existence
  fi

  # only add if not already in .env PATH
  local global_PATH=$(sed -n 's/^PATH+=\(.*\)/\1/p' "$GLOBAL_ENV" 2>/dev/null)
  [[ "$global_PATH" =~ \"(.*)\"|\'(.*)\' ]] && global_PATH=${BASH_REMATCH[1]} # remove quotes
  if [[ ":$global_PATH:" != *":$p:"* ]]; then
    global_env_append PATH ":$p"
  fi
}
