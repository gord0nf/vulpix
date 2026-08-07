#!/usr/bin/env bash

[[ -v APT_MODE ]] || fatal 'apt/interface.sh requires APT_MODE'
[[ "$APT_MODE" == 'safe' || "$APT_MODE" == 'strict' ]] || fatal 'invalid APT_MODE'

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
LIBRARY="$SCRIPT_DIR/../.."

APT_PACKAGE_LIST="$VULPIX_DATA/apt_packages.list"
[[ -f "$APT_PACKAGE_LIST" ]] || touch "$APT_PACKAGE_LIST"

_get_template_script() {
  echo "$LIBRARY/packages/$1/apt.sh"
}

_load_template() {
  local script=$(_get_template_script "$1")
  source "$script" || return 1

  # verify env vars
  [[ -v APT_PACKAGES ]] || fatal "'$script' did not define APT_PACKAGES"
}

_package_id_syntax() {
  [[ "$1" == *'?' ]] && echo "${1%?}"
}

_list_internal_packages() {
  installed_packages=()
  readarray -t installed_packages <"$APT_PACKAGE_LIST"
}

_list_all_system_packages() {
  readarray -t installed_packages < <(
    python3 -c '
      from apt import cache
      manual = set(
          pkg for pkg in cache.Cache() if pkg.is_installed and not pkg.is_auto_installed
      )
      depends = set(
          dep_pkg.name
          for pkg in manual
          for dep in pkg.installed.get_dependencies("PreDepends", "Depends", "Recommends")
          for dep_pkg in dep
      )
      print("\n".join(pkg.name for pkg in manual if pkg.name not in depends))
    '
  )
}

_apt_packages_install() {
  for package_id in "${APT_PACKAGES[@]}"; do
    sudo apt install --yes "$package_id" || fatal "failed to install '$package_id'"
    sed -i "/^${package_id}?$/d" "$APT_PACKAGE_LIST"
    echo "${package_id}?" >>"$APT_PACKAGE_LIST" # write package_id syntax regardless of whether template because next package(s) might fail
  done
}
_apt_packages_upgrade() {
  for package_id in "${APT_PACKAGES[@]}"; do
    sudo apt install --yes "$package_id" || fatal "failed to upgrade '$package_id'"
  done
}
_apt_packages_remove() {
  for package_id in "${APT_PACKAGES[@]}"; do
    sudo apt remove --yes "$package_id" || fatal "failed to remove '$package_id'"
    sed -i "/^$package_id$/d" "$APT_PACKAGE_LIST"
  done
}
_apt_packages_reinstall() {
  _apt_packages_remove && _apt_packages_install
}

_template_install() {
  local template=$1
  APT_PACKAGES=()
  _load_template "$template" || {
    warn "couldn't load template '$template'"
    continue
  }

  _apt_packages_install || return 1

  # replace individual package ids with template
  for package_id in "${APT_PACKAGES[@]}"; do
    sed -i "/^${package_id}?$/d" "$APT_PACKAGE_LIST"
  done
  sed -i "/^$template$/d" "$APT_PACKAGE_LIST"
  echo "$template" >>"$APT_PACKAGE_LIST"
}
_template_uninstall() {
  local template=$1
  APT_PACKAGES=()
  _load_template "$template" || {
    warn "couldn't load template '$template'"
    continue
  }

  # filter APT_PACKAGES to remove to be only package_ids not explicitly defined in APT_PACKAGE_LIST
  local filtered=()
  for package_id in "${APT_PACKAGES[@]}"; do
    grep -q "${package_id}?" "$APT_PACKAGE_LIST" || filtered+=("$package_id")
  done
  APT_PACKAGES=("${filtered[@]}")
  if [[ "${#APT_PACKAGES[@]}" -eq 0 ]]; then
    warn "no apt packages to remove for template since they are all explicitly defined using package id syntax"
    return
  fi

  _apt_packages_remove || return 1
  sed -i "/^$template/d" "$APT_PACKAGE_LIST"
}
_template_update() {
  APT_PACKAGES=()
  _load_template "$1" || {
    warn "couldn't load template '$1'"
    continue
  }
  _apt_packages_upgrade
}
_template_reinstall() {
  _template_uninstall "$1" && _template_install "$1"
}

can_use_manager() {
  declare -A requirements=(
    ['[[ $OS == linux ]]']='apt is only for linux (specifically debian)'
    ['command_exists apt']='apt not found'
    ['command_exists apt-get']='apt-get not found'
    ['command_exists python3']='requires python3 (should be preinstalled on debian) but not found'
    # ['is_root']='root required for apt'
  )
  for r in "${!requirements[@]}"; do
    eval "$r" || {
      err "${requirements[$r]}"
      return 1
    }
  done
}

package_is_supported() {
  _package_id_syntax "$1" >/dev/null || [[ -f "$(_get_template_script "$1")" ]]
}

presetup() {
  info 'updating apt sources'
  sudo apt update |& output
}

get_installed() {
  local -n installed=$1
  case "$APT_MODE" in
    safe) _list_internal_packages ;;
    strict) _list_all_system_packages ;;
  esac
  [[ $? -eq 0 ]] || return 1
  installed=("${installed_packages[@]}")
}

install_packages() {
  local -n packages=$1

  # split between direct ids (package? syntax) and templates
  local package_ids=() package_templates=()
  for package in "${packages[@]}"; do
    package_id=$(_package_id_syntax "$package") &&
      package_ids+=("$package_id") ||
      package_templates+=("$package")
  done

  debug "apt direct package_ids: ${package_ids[@]}"
  debug "apt templates: ${package_templates[@]}"

  # !NOTE! install package_templates first becuase they will override direct package names in
  # APT_PACKAGE_LIST, then package_ids will add the direct references
  for template in "${package_templates[@]}"; do
    run_foreground_task "install $template@apt" _template_install "$template" ||
      warn "package install failed for '$template'"
  done
  for package_id in "${package_ids[@]}"; do
    APT_PACKAGES=("$package_id")
    run_foreground_task "install $package_id?@apt" _apt_packages_install ||
      warn "package install failed for '$package_id'"
  done
}

uninstall_packages() {
  local -n packages=$1

  # split between direct ids (package? syntax) and templates
  local package_ids=() package_templates=()
  for package in "${packages[@]}"; do
    package_id=$(_package_id_syntax "$package") &&
      package_ids+=("$package_id") ||
      package_templates+=("$package")
  done

  debug "apt direct package_ids: ${package_ids[@]}"
  debug "apt templates: ${package_templates[@]}"

  # !NOTE! install package_ids first becuase _template_uninstall will not uninstall any direct package_ids,
  # so we have to remove those first before uninstalling templates
  for package_id in "${package_ids[@]}"; do
    APT_PACKAGES=("$package_id")
    run_foreground_task "uninstall $package_id?@apt" _apt_packages_remove ||
      warn "package uninstall failed for '$package_id'"
  done
  for template in "${package_templates[@]}"; do
    run_foreground_task "uninstall $template@apt" _template_uninstall "$template" ||
      warn "package uninstall failed for '$template'"
  done
}

update_packages() {
  local -n packages=$1
  for package in "${packages[@]}"; do
    if package_id=$(_package_id_syntax "$package"); then
      APT_PACKAGES=("$package_id")
      run_foreground_task "update $package@apt" _apt_packages_upgrade ||
        warn "package update failed for '$package'"
    else
      run_foreground_task "update $package@apt" _template_update "$package" ||
        warn "package update failed for '$package'"
    fi
  done
}

reinstall_packages() {
  local -n packages=$1
  for package in "${packages[@]}"; do
    if package_id=$(_package_id_syntax "$package"); then
      APT_PACKAGES=("$package_id")
      run_foreground_task "reinstall $package@apt" _apt_packages_reinstall ||
        warn "package reinstall failed for '$package'"
    else
      run_foreground_task "reinstall $package@apt" _template_reinstall "$package" ||
        warn "package reinstall failed for '$package'"
    fi
  done
}
