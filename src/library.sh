#!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
LIBRARY=$(realpath "$SCRIPT_DIR/../library")

REQUIRED_MANAGER_FUNCTIONS=(
  'can_use_manager'
  'package_is_supported'
  'get_installed'
  'install_packages'
  'uninstall_packages'
  'update_packages'
  'reinstall_packages'
)

_get_manager_interface() {
  echo "$LIBRARY/managers/$1/interface.sh"
}

is_manager() {
  [[ -f "$(_get_manager_interface "$1")" ]]
}

# sources manager interface, with checks
load_manager() {
  local script=$(_get_manager_interface "$1")
  source_script "$script" || fatal 'invalid manager'

  # verify required exports
  for func in "${REQUIRED_MANAGER_FUNCTIONS[@]}"; do
    function_exists "$func" || fatal "$1 manager script does not export '$func()'"
  done
}
