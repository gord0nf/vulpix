#!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)

DEPENDENCIES=(grep sed awk curl unzip tar yq)
LIBRARY="$SCRIPT_DIR/.."
MANUAL_ROOT="$VULPIX_DATA/manual"

mkdir -p "$MANUAL_ROOT"

can_use_manager() {
  for dep in "${DEPENDENCIES[@]}"; do
    command_exists "$dep" || {
      err "manager(manual): requires $dep, but not found"
      return 1
    }
  done
}

package_is_supported() {
  local package=$1
  local install_script="$LIBRARY/packages/$package/manual.sh"
  [[ -f "$install_script" ]]
}

presetup() {
  : # TODO; garbage collector, etc
}

get_installed() {
  : # TODO; listing based on status.yaml
}

install_packages() {
  local -n packages=$1
  : # TODO
}

uninstall_packages() {
  local -n packages=$1
  : # TODO
}

update_packages() {
  local -n packages=$1
  : # TODO
}

reinstall_packages() {
  local -n packages=$1
  : # TODO
}
