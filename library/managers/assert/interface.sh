#!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
LIBRARY="$SCRIPT_DIR/../.."

_package_force_syntax() {
  [[ "$1" == *'!' ]] && echo "${1%?}"
}

_get_preset_script() {
  local script="$LIBRARY/packages/$1/apt.sh"
  [[ -f "$script" ]] && echo "$script"
}

_assert_force() {
  info "forced assertation '$1'"
}

_assert_preset() {
  local preset="$1"
  local script=$(_get_preset_script "$preset")
  info "checking with preset '$preset'"
  set -e
  source "$script" || exit $?
}

_assert_binary() {
  local binary="$1"
  if ! command_exists "$binary"; then
    info "'$binary' is not a valid command"
    return 1
  fi
  info "'$binary' is a valid command"
}

can_use_manager() {
  true
}

package_is_supported() {
  true
}

get_installed() {
  local -n installed=$1
  installed=()
}

install_packages() {
  local -n packages=$1
  for package in "${packages[@]}"; do
    if pkg=$(_package_force_syntax "$package"); then
      run_background_task "$(make_task_name 'install' "$package@assert")" \
        _assert_force "$pkg"
    elif _get_preset_script "$package" >/dev/null; then
      run_background_task "$(make_task_name 'install' "$package@assert")" \
        _assert_preset "$package"
    else
      run_background_task "$(make_task_name 'install' "$package@assert")" \
        _assert_binary "$package"
    fi
  done
}

uninstall_packages() {
  fatal 'uninstall_packages should never be called'
}

update_packages() {
  fatal 'update_packages should never be called'
}

reinstall_packages() {
  fatal 'reinstall_packages should never be called'
}
