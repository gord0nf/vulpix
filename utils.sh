#!/usr/bin/env bash

# a bunch of general util functions and env vars.
# also provides default logs to stdout/stderr, which can be overridden (such as the case with cli logging)

# functions ---------------------------------------------------------------------------------------

# basic default logging
debug() {
  if [[ -v DEBUG ]]; then echo "DEBUG: $*"; fi
}
info() {
  echo "INFO: $*"
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
