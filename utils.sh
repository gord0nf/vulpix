#!/usr/bin/env bash

# a bunch of general util functions and env vars.
# also provides default logs to stdout/stderr, which can be overridden (such as the case with cli logging)

# functions ---------------------------------------------------------------------------------------

# basic default logging
output() {
  echo "OUTPUT: $*"
}
debug() {
  if [[ -v DEBUG ]]; then echo "DEBUG: $*" >&2; fi
}
info() {
  echo "INFO: $*" >&2
}
warn() {
  echo "WARN: $*" >&2
}
err() {
  echo "ERROR: $*" >&2
}
fatal() {
  echo "FATAL: $*" >&2
  exit 1
}

command_exists() {
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
    [[ -n "$ARCH" ]] && break
  done
  [[ -n "$ARCH" ]] || fatal 'could not determine arch'
  command_exists getconf && ARCH="${ARCH%??}$(getconf LONG_BIT)"
  export ARCH
}

is_root() {
  [[ "$EUID" -eq 0 ]]
}

is_git_repo() {
  git -C "$1" rev-parse --is-inside-work-tree &>/dev/null
}

prompt() {
  read -n 1 -r -p "$1 (y/n): " answer
  echo # new line
  case $answer in
    [yY]*) return 0 ;;
    *) return 1 ;;
  esac
}

convert_path_if_needed() {
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
  [[ "$(type -t "$1")" == "function" ]]
}

# https://jcgoran.github.io/2021/02/07/bash-string-trimming.html
trimstring() {
  if [ $# -ne 1 ]; then
    echo "USAGE: trimstring [STRING]"
    return 1
  fi
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
  local -n array=$1
  for element in "${array[@]}"; do
    if [[ "$element" == "$2" ]]; then
      return 0
    fi
  done
  return 1
}

# use like join_by 'sep' "${array[@]}"
join_by() {
  local d=${1-} f=${2-}
  if shift 2; then
    printf %s "$f" "${@/#/$d}"
  fi
}

__sourced=()
source_script() {
  [[ -f "$1" ]] || fatal "could not source nonexistent '$1'"
  for script in "${__sourced[@]}"; do
    [[ "$1" -ef "$script" ]] && {
      debug "skipping resource of $1"
      return
    }
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
  yq "${args[@]}"
}

yq_get_array() {
  local -n array=$1
  local query=$2 file=$3
  shift && shift && shift
  array=()
  _array=$(yq_safe -r "$@" "$query" "$file") || return 1
  [[ -z "$_array" ]] && return
  readarray -t _array <<<"$_array" && array=("${_array[@]}")
}

yq_set_array() {
  local -n array=$2
  local query=$1 file=$3
  shift && shift && shift
  [[ "$1" == '--append' ]] && local op_mod='+' && shift
  [[ "${#array[@]}" -gt 0 ]] &&
    local array_values="\"$(join_by '","' "${array[@]}")\""
  [ -z "$(cat "$file")" ] && echo '{}' >"$file" # python yq doesn't handle empty files well
  yq_safe --in-place "$@" \
    "$query $op_mod= [$array_values]" \
    "$file"
}

yq_has_key() {
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

# git bash on windows is iffy about detecting junctions as existing using just [ -e ... ]
item_exists() {
  [[ -e "$1" ]] || ls "$1" &>/dev/null
}

# functions for atomic item (file or directory) change through a temporary directory
atomic_change_start() {
  local item="$1" tmpitem="$1.temp"
  ! item_exists "$tmpitem" || fatal '_atomic_change_start used incorrectly by devs!'
  item_exists "$item" && cp --recursive --no-dereference --preserve=links "$item" "$tmpitem"
  echo "$tmpitem"
}
atomic_change_abort() {
  local item="$1" tmpitem="$1.temp"
  rm -fr "$tmpitem"
}
atomic_change_apply() {
  local item="$1" tmpitem="$1.temp"
  item_exists "$tmpitem" || fatal '_atomic_change_apply used incorrectly by devs!'
  rm -fr "$item" && mv "$tmpitem" "$item"
}

# returns 0 if link created, else 1
file_link() {
  local link=$1 target=$2
  MSYS=winsymlinks:nativestrict ln -s "$target" "$link"
  # TODO: windows symlink alternative for non-admin users (who can't create symlinks); .lnk files? hard links?
}

# returns 0 if link created, else 1
dir_link() {
  local link=$1 target=$2
  MSYS=winsymlinks:nativestrict ln -s "$target" "$link"
  # TODO: windows junction, checks ect.
}

dir_is_empty() {
  [ -z "$(ls -A "$1")" ]
}

normalize_path() {
  local path="$1"
  if [[ "$path" != "/" ]]; then
    path="${path%/}"
  fi
  path="${path//\/.\//\/}"
  while [[ $path =~ ([^/][^/]*/\.\\./) ]]; do
    path="${path/${BASH_REMATCH[0]}/}"
  done
  echo "$path"
}

# environmental variables -------------------------------------------------------------------------

get_os
get_arch
[[ $OS == mac ]] && fatal 'sorry, macos is not supported'

# check for windows env vars
if [[ $OS == windows ]]; then
  for var in ProgramFiles ProgramData APPDATA LOCALAPPDATA; do
    [[ -v "$var" ]] || fatal "windows environmental var is required: $var"
  done
fi

# VULPIX_INSTALL
if is_root; then
  [[ $OS == windows ]] &&
    VULPIX_INSTALL="$ProgramFiles/vulpix" ||
    VULPIX_INSTALL="/opt/vulpix"
else
  [[ $OS == windows ]] &&
    VULPIX_INSTALL="$LOCALAPPDATA/Programs/vulpix" ||
    VULPIX_INSTALL="$HOME/.local/opt/vulpix"
fi
export VULPIX_INSTALL

# VULPIX_DATA
if is_root; then
  [[ $OS == windows ]] &&
    VULPIX_DATA="$ProgramData/vulpix" ||
    VULPIX_DATA="/var/lib/vulpix"
else
  [[ $OS == windows ]] &&
    VULPIX_DATA="$LOCALAPPDATA/vulpix" ||
    VULPIX_DATA="${XDG_STATE_HOME:-$HOME/.local/state}/vulpix"
fi
export VULPIX_DATA

# VULPIX_LOG
if is_root; then
  [[ $OS == windows ]] &&
    VULPIX_LOG="$ProgramData/vulpix/log" ||
    VULPIX_LOG="/var/log/vulpix"
else
  [[ $OS == windows ]] &&
    VULPIX_LOG="$LOCALAPPDATA/vulpix/log" ||
    VULPIX_LOG="${XDG_STATE_HOME:-$HOME/.local/state}/vulpix/log"
fi
export VULPIX_LOG

# VUPLIX_CONFIG
if is_root; then
  [[ $OS == windows ]] &&
    VULPIX_CONFIG="$ProgramData/vulpix/config" ||
    VULPIX_CONFIG="/etc/vulpix"
else
  [[ $OS == windows ]] &&
    VULPIX_CONFIG="$APPDATA/Roaming/vulpix" ||
    VULPIX_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/vulpix"
fi
export VULPIX_CONFIG
