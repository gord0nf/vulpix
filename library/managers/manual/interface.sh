#!/usr/bin/env bash

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
LIBRARY="$SCRIPT_DIR/../.."

DEPENDENCIES=(grep sed awk curl unzip tar yq)
MANUAL_ROOT="$VULPIX_DATA/manual"
BIN="$MANUAL_ROOT/bin"
STATUS="$MANUAL_ROOT/status.yaml"
N_GRACE_DAYS=30 # number of days before deactivated packages are actually destroyed

source_script "$SCRIPT_DIR/utils.sh"

_get_install_script() {
  echo "$LIBRARY/packages/$1/manual.sh"
}

_get_install_dir() {
  echo "$MANUAL_ROOT/packages/$1"
}

_get_bin_link_filename() {
  local package=$1 relative_path=$(normalize_path "$2")
  if [[ "$relative_path" == '.' ]]; then relative_path=''; fi
  local path="$(_get_install_dir "$1")/$relative_path"
  if [[ -f "$path" ]]; then
    echo "$(basename "$path")"
  elif [[ -d "$path" ]]; then
    echo "${package}${relative_path:+_${relative_path//\//_}}"
  else
    warn "invalid binary '$relative_path' for $package"
  fi
}

# status.yaml utils -------------------------------------------------------------------------------

STATUS_MUTEX='MANUAL_STATUS_YAML'

_package_is_installed() {
  yq_has_key '.' "$1" "$STATUS"
}

_package_is_active() {
  [[ "$(yq_safe -r '.'$1'.active' "$STATUS")" == 'true' ]]
}

_destroy_package_entry() {
  mutex_is_locked $STATUS_MUTEX || fatal '_destroy_package_entry: status not locked'
  local package=$1
  info "destroying package entry '$package'"
  yq_safe --in-place 'del(.'$package')' "$STATUS"
}

_activate_package_entry() {
  mutex_is_locked $STATUS_MUTEX || fatal '_update_package_entry: status not locked'
  local package=$1
  info "activating package entry '$package'"
  yq_safe --in-place '.'$package'.active = true' "$STATUS"
  yq_safe --in-place '.'$package'.last_active = "'$(date +%Y-%m-%d)'"' "$STATUS"
  if [[ $# -gt 1 ]]; then
    local bin_paths=$2 # name of array var
    yq_set_array '.'$package'.binaries' $bin_paths "$STATUS"
  fi
}

_deactivate_package_entry() {
  mutex_is_locked $STATUS_MUTEX || fatal '_update_package_entry: status not locked'
  local package=$1
  info "deactivating package entry '$package'"
  yq_safe --in-place '.'$package'.active = false' "$STATUS"
}

_activate_package_binaries() {
  mutex_is_locked $STATUS_MUTEX || fatal '_activate_package_binaries: status not locked'

  local package=$1
  info "activating '$package' binaries"
  local binaries=()
  yq_get_array binaries '.'$package'.binaries[]' "$STATUS" || return 1

  # atomic add binary links (first copy bin/, do the stuff, then move to bin)
  local tmpbin=$(atomic_change_start "$BIN")
  mkdir -p "$tmpbin"
  for bin in "${binaries[@]}"; do
    bin_path="$(_get_install_dir "$package")/$bin"
    bin_link=$(_get_bin_link_filename "$package" "$bin")
    [[ -n "$bin_link" ]] || continue
    bin_link="$tmpbin/$bin_link"
    rm -fr "$bin_link"
    debug "bin link: '$bin_link' -> '$bin_path'"
    [[ -d "$bin_path" ]] &&
      dir_link "$bin_link" "$bin_path" ||
      file_link "$bin_link" "$bin_path"
    [[ $? -eq 0 ]] || {
      err "couldn't create link from '$bin_path' to '$bin_link'"
      atomic_change_abort "$BIN"
      return 1
    }
  done
  atomic_change_apply "$BIN"
}

_deactivate_package_binaries() {
  mutex_is_locked $STATUS_MUTEX || fatal '_deactivate_package_binaries: status not locked'

  local package=$1
  info "deactivating '$package' binaries"
  local binaries=()
  yq_get_array binaries '.'$package'.binaries' "$STATUS"

  # atomic remove binary links (first copy bin/, do the stuff, then move to bin)
  local tmpbin=$(atomic_change_start "$BIN")
  for bin in "${binaries[@]}"; do
    bin_link=$(_get_bin_link_path "$package" "$bin")
    [[ -n "$bin_link" ]] || continue
    bin_link="$tmpbin/$bin_link"
    item_exists "$bin_link" || {
      warn "manual: expected binary to be linked at '$bin_link'"
      continue
    }
    rm "$bin_link" || {
      err "manual: couldn't remove link at '$bin_link'"
      atomic_change_abort "$BIN"
      return 1
    }
  done
  atomic_change_apply "$BIN"
}

# install/uninstall/update/reinstall helpers ------------------------------------------------------

# writes array of returned binary paths to $package_binaries
_run_package_script() {
  local package=$1
  info "running script for package '$package'"
  install_script=$(_get_install_script "$package")
  install_dir=$(_get_install_dir "$package")
  tmp_install_dir=$(atomic_change_start "$install_dir")

  # load_array_by_line_from_command runs install_cmd as subshell to fork bash context and capture output
  local install_cmd="source '$install_script' '$tmp_install_dir' || fatal 'install script failed'"
  package_binaries=()
  load_array_by_line_from_command package_binaries \
    eval "$install_cmd" || {
    err "'$package' install failed. rolling back changes..."
    atomic_change_abort "$install_dir"
    return 1
  }
  atomic_change_apply "$install_dir"
}

_destory_package() {
  local package=$1
  info "destroying package '$package'"
  rm -fr "$(_get_install_dir "$package")"

  mutex_lock $STATUS_MUTEX
  _deactivate_package_binaries "$package" || return $?
  _destroy_package_entry "$package" || return $?
  mutex_unlock $STATUS_MUTEX
}

_install_package() {
  local package=$1
  package_binaries=
  info "installing package '$package'"

  _package_is_installed "$package" &&
    info "package already installed '$package'" ||
    _run_package_script "$package" || return 1

  mutex_lock $STATUS_MUTEX
  _activate_package_entry "$package" ${package_binaries:+package_binaries} || return $?
  _activate_package_binaries "$package" || return $?
  mutex_unlock $STATUS_MUTEX
}

_uninstall_package() {
  local package=$1
  info "uninstalling package '$package'"
  if _package_is_active "$1"; then
    mutex_lock $STATUS_MUTEX
    _deactivate_package_entry || return $?
    _deactivate_package_binaries "$package" || return $?
    mutex_unlock $STATUS_MUTEX
  else
    info "'$package' not installed or already deactivated"
  fi
}

_update_package() {
  local package=$1
  info "updating package '$package'"
  _package_is_installed "$package" || {
    err "package '$package' is not installed, so can't update"
    return 1
  }

  mutex_lock $STATUS_MUTEX
  _destroy_package_entry "$package" || return $? # remove status entry so we can create it again
  _run_package_script "$package" || return $?    # calling on an already installed package should update it
  _activate_package_entry "$package" package_binaries || return $?
  _activate_package_binaries "$package" || return $?
  mutex_unlock $STATUS_MUTEX
}

_reinstall_package() {
  local package=$1
  info "reinstalling package '$package'"
  _destory_package "$package" || return $?
  _install_package "$package" || return $?
}

# main exports ------------------------------------------------------------------------------------

can_use_manager() {
  for dep in "${DEPENDENCIES[@]}"; do
    command_exists "$dep" || {
      err "requires $dep, but not found"
      return 1
    }
  done
}

package_is_supported() {
  local package=$1
  local install_script=$(_get_install_script "$package")
  [[ -f "$install_script" ]]
}

# create stuff && verify status.yaml
presetup() {
  info 'making dirs'
  mkdir -p "$MANUAL_ROOT"
  mkdir -p "$BIN"

  if [[ -f "$STATUS" ]]; then
    info "verifying status.yaml"
    local packages=()
    yq_get_array packages '. | select(.) | keys[]' "$STATUS" || fatal "invalid yaml at $STATUS"
    for pkg in "${packages[@]}"; do
      if ! package_is_supported "$pkg"; then
        warn "cleaning unsupported package '$pkg' at $STATUS"
        yq_safe --in-place 'del(.'$pkg')' "$STATUS"
      fi
    done
  else
    touch "$STATUS"
  fi
}

# garbage collection
postsetup() {
  info 'checking for garbage packages'

  local cutoff_date=$(date -d "$N_GRACE_DAYS days ago" +"%Y-%m-%d")
  local garbage_packages=()
  yq_get_array garbage_packages \
    '. | with_entries(select(.value.last_active <= "'$cutoff_date'")) | keys[]' \
    "$STATUS"
  [[ $? -eq 0 ]] || fatal "could not parse status for garbage"

  for package in "${garbage_packages[@]}"; do
    info "'$package' for garbage collection"
    _destory_package "$package"
  done
}

get_installed() {
  local -n installed=$1
  yq_get_array installed \
    '. | with_entries(select(.value.active == true)) | keys[]' \
    "$STATUS"
}

install_packages() {
  local -n packages=$1
  for package in "${packages[@]}"; do
    package_is_supported "$package" || fatal "not supported '$package', SHOULD NOT GET HERE"
    run_background_task "$(make_task_name 'install' "$package@manual")" _install_package "$package"
  done
}

uninstall_packages() {
  local -n packages=$1
  for package in "${packages[@]}"; do
    package_is_supported "$package" || fatal "not supported '$package', SHOULD NOT GET HERE"
    run_background_task "$(make_task_name 'uninstall' "$package@manual")" _uninstall_package "$package"
  done
}

update_packages() {
  local -n packages=$1
  for package in "${packages[@]}"; do
    package_is_supported "$package" || fatal "package not supported '$package'. SHOULD NOT GET HERE"
    run_background_task "$(make_task_name 'update' "$package@manual")" _update_package "$package"
  done
}

reinstall_packages() {
  local -n packages=$1
  for package in "${packages[@]}"; do
    package_is_supported "$package" || fatal "package not supported '$package'. SHOULD NOT GET HERE"
    run_background_task "$(make_task_name 'reinstall' "$package@manual")" _reinstall_package "$package"
  done
}
