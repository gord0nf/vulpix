#!/usr/bin/env bash

# a bunch of general util functions and env vars.
# also provides default logs to stdout/stderr, which can be overridden (such as the case with cli logging)

set -euo pipefail
set -E
shopt -s nullglob globstar inherit_errexit

# functions ---------------------------------------------------------------------------------------

# basic default logging
output() { cat; }
debug() { if [[ -v DEBUG ]]; then echo "DEBUG: $*" >&2; fi; }
info() { echo "INFO: $*" >&2; }
warn() { echo "WARN: $*" >&2; }
success() { echo "SUCCESS: $*" >&2; }
err() { echo "ERROR: $*" >&2; }
fatal() { echo "FATAL: $*" >&2 && exit 1; }

verify() {
  [[ $# -eq 1 ]]
  read -p "$1 (y/n): " -n 1 -r REPLY
  echo # new line
  case $REPLY in
    [yY]*) return 0 ;;
    *) return 1 ;;
  esac
}

prompt() {
  [[ $# -eq 1 ]]
  read -p "$1" REPLY
  echo "$REPLY"
}

get_choice_idx() {
  [[ $# -eq 2 ]]
  local -n choices=$2
  local prompt=$1 n_choices=$((${#choices[@]} - 1))
  local n_digits=${#n_choices}
  echo
  for ((i = 0; i <= n_choices; i++)); do
    printf "  %0${n_digits}d) %b\n" "$i" "${choices[$i]}"
  done
  echo
  read -p "$prompt" -n "$n_digits" -r REPLY
  echo
  [[ "$REPLY" =~ ^[0-9]+$ ]] && choice_idx="$REPLY"
}

command_exists() {
  [[ $# -eq 1 ]]
  command -v "$1" &>/dev/null
}

# exports $OS as 'windows' | 'linux' | 'mac'
get_os() {
  if grep -qEi "(Microsoft|WSL|MSYS)" /proc/version &>/dev/null; then
    OS=windows
  else
    case "$OSTYPE" in
      darwin*) OS=mac ;;
      solaris* | linux* | bsd* | freebsd*) OS=linux ;;
      msys* | cygwin* | win32*) OS=windows ;;
      *) fatal 'could not determine os; please define $OSTYPE.' ;;
    esac
  fi
  export OS
}

# exports $ARCH as 'x64' | 'x32' | 'arm32' | 'arm64'
get_arch() {
  local commands=(
    "uname -m | tr '[:upper:]' '[:lower:]'"
    'arch'
  )
  for cmd in "${commands[@]}"; do
    case $(eval "$cmd") in
      x86_64*) ARCH=x64 ;;
      i*86) ARCH=x32 ;;
      arm64 | aarch64) ARCH=arm64 ;;
      arm*) ARCH=arm32 ;;
    esac
    if [[ -n "$ARCH" ]]; then break; fi
  done
  [[ -n "$ARCH" ]] || fatal 'could not determine arch'
  if command_exists getconf; then ARCH="${ARCH%??}$(getconf LONG_BIT)"; fi
  export ARCH
}

is_root() {
  [[ "$EUID" -eq 0 ]]
}

is_git_repo() {
  [[ $# -eq 1 ]]
  git -C "$1" rev-parse --is-inside-work-tree &>/dev/null
}

convert_path_if_needed() {
  [[ $# -eq 2 ]]
  local target_switch=$1
  local path=$2
  if command_exists wslpath; then
    echo "$(wslpath $target_switch "$path")"
  elif command_exists cygpath; then
    echo "$(cygpath $target_switch "$path")"
  else
    echo "$path"
  fi
}

function_exists() {
  [[ $# -eq 1 ]]
  [[ "$(type -t "$1")" == "function" ]]
}

# https://jcgoran.github.io/2021/02/07/bash-string-trimming.html
trimstring() {
  [ $# -eq 1 ] || return 1
  s="${1}"
  size_before=${#s}
  size_after=0
  while [ ${size_before} -ne ${size_after} ]; do
    size_before=${#s}
    s="${s#[[:space:]]}"
    s="${s%[[:space:]]}"
    size_after=${#s}
  done
  echo "${s}"
  return 0
}

array_has_element() {
  [[ $# -eq 1 ]]
  local -n array=$1
  for element in "${array[@]}"; do
    if [[ "$element" == "$2" ]]; then
      return 0
    fi
  done
  return 1
}

array_remove_element() {
  [[ $# -eq 2 ]]
  local -n array=$1
  local element=$2
  for ((i = ${#array[@]} - 1; i >= 0; i--)); do
    if [[ "${array[i]}" == "$element" ]]; then
      unset 'array[i]'
    fi
  done
  array=("${array[@]}")
}

# NOTE: DO NOT USE IN PIPES because pipe commands start in subprocesses so it doesn't load the array in the current context
load_array_by_line() {
  [[ $# -eq 1 ]]
  local -n array=$1
  local first_line=true
  array=()
  while IFS= read -r line || [[ -n "$line" ]]; do
    if $first_line && [[ -z "${line//[[:space:]]/}" ]]; then
      break
    fi
    array+=("$line")
    first_line=false
  done </dev/stdin
}

# NOTE: runs target command in subshell
load_array_by_line_from_command() {
  [[ $# -gt 1 ]]
  local array_name=$1
  shift
  load_array_by_line $array_name < <("$@") || {
    err 'load_array_by_line: failed'
    return 1
  }
  wait "$!" || return $? # fails if the target command fails
}

# use like join_by 'sep' "${array[@]}"
join_by() {
  local d=${1-} f=${2-}
  if shift 2; then
    printf %s "$f" "${@/#/$d}"
  fi
}

# writes to sorted_array
sort_array() {
  [[ $# -ge 1 ]]
  local -n array=$1
  shift
  sorted=$(printf '%s\n' "${array[@]}" | sort "$@") || return 1
  sorted_array=()
  load_array_by_line sorted_array <<<"$sorted"
}

__sourced=()
source_script() {
  [[ $# -eq 1 ]]
  [[ -f "$1" ]] || fatal "could not source nonexistent '$1'"
  for script in "${__sourced[@]}"; do
    if [[ "$1" -ef "$script" ]]; then
      debug "skipping resource of $1"
      return
    fi
  done
  debug "sourcing $1"
  source "$1" || fatal "failed to source '$1'"
  __sourced+=("$1")
}

_yq_implementation() {
  [[ $(yq --version) == *mikefarah* ]] && echo go || echo python
}

yq_safe() {
  local args=("$@")
  for ((i = 0; $i < ${#args[@]}; i++)); do
    case "${args[$i]}" in
      -i | --in-place)
        case "$(_yq_implementation)" in
          python) args+=('-Y') ;;
          go) args[$i]='--inplace' ;;
        esac
        ;;
    esac
  done
  debug "running: yq ${args[@]}"
  yq "${args[@]}" | tee >(output >/dev/null) || {
    err 'yq_safe: yq failed'
    return 1
  }
}

yq_get_array() {
  [[ $# -ge 3 ]]
  local -n array=$1
  local query=$2 file=$3
  shift && shift && shift
  load_array_by_line_from_command ${!array} \
    yq_safe -r "$@" "$query" "$file"
}

yq_set_array() {
  [[ $# -ge 3 ]]
  local -n array=$2
  local query=$1 file=$3
  shift && shift && shift
  local op='='
  if [[ $# -gt 0 ]] && [[ "$1" == '--append' ]]; then op='+=' && shift; fi

  local array_values=
  if [[ "${#array[@]}" -gt 0 ]]; then
    array_values="\"$(join_by '","' "${array[@]}")\""
  fi
  if file_is_empty; then
    echo '{}' >"$file" # python yq doesn't handle empty files well
  fi
  yq_safe --in-place "$@" \
    "$query $op [$array_values]" \
    "$file"
}

yq_has_key() {
  [[ $# -eq 3 ]]
  local query=$1 key=$2 file=$3
  case $(_yq_implementation) in
    go)
      has_key=$(yq_safe $query' | has("'$key'")' "$file")
      $has_key
      return $?
      ;;
    python)
      local keys=()
      yq_get_array keys $query' | keys[]' "$file"
      array_has_element keys "$key"
      return $?
      ;;
  esac
}

yq_merge_yamls() {
  case $(_yq_implementation) in
    go) yq ea '. as $item ireduce ({}; . *+ $item )' "$@" ;;
    python) yq -y 'input as $in | . *+ $in' "$@" ;; # TODO: need to test (also does it support - syntax?)
  esac
}

# git bash on windows is iffy about detecting junctions as existing using just [ -e ... ]
item_exists() {
  [[ $# -eq 1 ]]
  [[ -e "$1" ]] || ls "$1" &>/dev/null
}

# functions for atomic item (file or directory) change through a temporary directory
atomic_change_start() {
  [[ $# -eq 1 ]]
  local item="$1" tmpitem="$1.temp"
  ! item_exists "$tmpitem" || fatal '_atomic_change_start used incorrectly by devs!'
  if item_exists "$item"; then
    cp --recursive --no-dereference --preserve=links "$item" "$tmpitem"
  fi
  echo "$tmpitem"
}
atomic_change_abort() {
  [[ $# -eq 1 ]]
  local item="$1" tmpitem="$1.temp"
  rm -fr "$tmpitem"
}
atomic_change_apply() {
  [[ $# -eq 1 ]]
  local item="$1" tmpitem="$1.temp"
  item_exists "$tmpitem" || fatal '_atomic_change_apply used incorrectly by devs!'
  rm -fr "$item" && mv "$tmpitem" "$item"
}

# returns 0 if link created, else 1
file_link() {
  [[ $# -eq 2 ]]
  local link=$1 target=$2
  MSYS=winsymlinks:nativestrict ln -s "$target" "$link"
  # TODO: windows symlink alternative for non-admin users (who can't create symlinks); .lnk files? hard links?
}

# returns 0 if link created, else 1
dir_link() {
  [[ $# -eq 2 ]]
  local link=$1 target=$2
  MSYS=winsymlinks:nativestrict ln -s "$target" "$link"
  # TODO: windows junction, checks ect.
}

dir_is_empty() {
  [[ $# -eq 1 ]]
  [ -z "$(ls -A "$1")" ]
}

file_is_empty() {
  [[ $# -eq 1 ]] && local file=$1
  [ -z "$(cat "$file")" ]
}

normalize_path() {
  [[ $# -eq 1 ]]
  local path="$1"
  if [[ "$path" != "/" ]]; then
    path="${path%/}"
  fi
  path="${path//\/.\//\/}"
  while [[ $path =~ ([^/][^/]*/\.\\./) ]]; do
    path="${path/${BASH_REMATCH[0]}/}"
  done
  echo "${path/#~/$HOME}"
}

# add color to stdout
colorize() {
  [[ $# -eq 1 ]]
  local color="$1"
  xargs -n1 -d '\n' printf "${color}%s${RESET}\n" </dev/stdin
}

# https://superuser.com/questions/380772/removing-ansi-color-codes-from-text-stream
decolorize() {
  stdbuf -oL sed 's/\x1b\[[0-9;]*m//g' </dev/stdin
}

prefix_output() {
  [[ $# -eq 1 ]]
  stdbuf -oL sed "s/^/$1/" </dev/stdin
}

print_divider() {
  [[ $# -eq 1 ]]
  printf "\n${BOLD}-=#${RESET} ${CYAN}${1}${RESET} ${BOLD}#=-${RESET}\n"
}

# set exit status in $exit_status
wait_safe() {
  [[ $# -ge 1 ]]
  local pid=$1
  shift
  if kill -0 "$pid" 2>/dev/null; then
    exit_status=0
    wait "$@" "$pid" || exit_status=$?
  else
    wait "$@" "$pid" 2>/dev/null || true
    exit_status=$?
  fi
}

# parse package string like package_name@manager into $parsed_package and $parsed_manager
parse_package() {
  [[ $# -eq 1 ]]
  [[ "$1" =~ ^(.+)@(.+)$ ]] && {
    parsed_package=${BASH_REMATCH[1]}
    parsed_manager=${BASH_REMATCH[2]}
  }
}

make_task_name() {
  [[ $# -eq 2 ]]
  local verb="$1" target="$2"
  echo "$verb[${target//\//%}]"
}

# writes to parsed_task_verb and parsed_task_target
parse_task_name() {
  [[ $# -eq 1 ]]
  [[ "$1" =~ ^(.+)\[(.+)\]$ ]] && {
    parsed_task_verb=${BASH_REMATCH[1]}
    parsed_task_target=${BASH_REMATCH[2]}
  }
}

# environmental variables -------------------------------------------------------------------------

get_os
get_arch
[[ $OS == mac ]] && fatal 'sorry, macos is not supported'

# check for windows env vars
if [[ $OS == windows ]]; then
  for var in ProgramFiles ProgramData APPDATA LOCALAPPDATA TMP; do
    [[ -v "$var" ]] || fatal "windows environmental var is required: $var"
  done
fi

# VULPIX_INSTALL
if ! [[ -v VULPIX_INSTALL ]]; then
  if [[ -v VULPIX ]]; then
    VULPIX_INSTALL="$VULPIX" # cli requires $VULPIX as dir with vulpix source
  else
    if is_root; then
      [[ $OS == windows ]] &&
        VULPIX_INSTALL="$ProgramFiles/vulpix" ||
        VULPIX_INSTALL="/opt/vulpix"
    else
      [[ $OS == windows ]] &&
        VULPIX_INSTALL="$LOCALAPPDATA/Programs/vulpix" ||
        VULPIX_INSTALL="$HOME/.local/opt/vulpix"
    fi
  fi
fi
export VULPIX_INSTALL

# VULPIX_DATA
if ! [[ -v VULPIX_DATA ]]; then
  if is_root; then
    [[ $OS == windows ]] &&
      VULPIX_DATA="$ProgramData/vulpix" ||
      VULPIX_DATA="/var/lib/vulpix"
  else
    [[ $OS == windows ]] &&
      VULPIX_DATA="$LOCALAPPDATA/vulpix" ||
      VULPIX_DATA="${XDG_STATE_HOME:-$HOME/.local/state}/vulpix"
  fi
fi
export VULPIX_DATA

# VULPIX_LOG
if ! [[ -v VULPIX_LOG ]]; then
  if is_root; then
    [[ $OS == windows ]] &&
      VULPIX_LOG="$ProgramData/vulpix/log" ||
      VULPIX_LOG="/var/log/vulpix"
  else
    [[ $OS == windows ]] &&
      VULPIX_LOG="$LOCALAPPDATA/vulpix/log" ||
      VULPIX_LOG="${XDG_STATE_HOME:-$HOME/.local/state}/vulpix/log"
  fi
fi
export VULPIX_LOG

# VUPLIX_CONFIG
if ! [[ -v VULPIX_CONFIG ]]; then
  if is_root; then
    [[ $OS == windows ]] &&
      VULPIX_CONFIG="$ProgramData/vulpix/config" ||
      VULPIX_CONFIG="/etc/vulpix"
  else
    [[ $OS == windows ]] &&
      VULPIX_CONFIG="$APPDATA/Roaming/vulpix" ||
      VULPIX_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/vulpix"
  fi
fi
export VULPIX_CONFIG

# VUPLIX_TMP
if ! [[ -v VULPIX_TMP ]]; then
  [[ $OS == windows ]] &&
    VULPIX_TMP="$TMP/vulpix" ||
    VULPIX_TMP="/tmp/vulpix"
fi
export VULPIX_TMP

# ansi color codes
RESET="\e[0m"
BLACK="\e[30m"
RED="\e[31m"
GREEN="\e[32m"
YELLOW="\e[33m"
BLUE="\e[34m"
PINK="\e[35m"
CYAN="\e[36m"
WHITE="\e[37m"
BOLD="\e[1m"
