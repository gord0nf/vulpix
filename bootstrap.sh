#!/usr/bin/env bash

set -e

OVERRIDE_INSTALL="$1"

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
VULPIX_REPO='gord0nf/vulpix'
VULPIX_REPO_GIT="https://github.com/$VULPIX_REPO"
VULPIX_REPO_RAW="https://raw.githubusercontent.com/$VULPIX_REPO/refs/heads/main"
VULPIX_REPO_TARBALL="$VULPIX_REPO_GIT/tarball/main"

command_exists() {
  command -v "$1" &>/dev/null
}

if command_exists curl; then
  DOWNLOAD='curl --fail -#L'
elif command_exists wget; then
  DOWNLOAD='wget --no-check-certificate -O -'
else
  echo 'FATAL: curl or wget required to install source' >&2
  exit 1
fi

# download utils script and source just for bootstrap
echo "INFO: downloading utils script" >&2
source <(eval "$DOWNLOAD '$VULPIX_REPO_RAW/utils.sh'")
if [[ $? -ne 0 ]]; then
  echo 'FATAL: failed to download and source utils script'
  exit 1
fi
echo # style

info 'will install at highest privilege (run with root to install globally)'
is_root && level=system || level=user
verify "continue with bootstrap at $level level?" || fatal 'bootstrap aborted'

# define MANUAL_ROOT, which SHOULD BE THE SAME as defined in `library/managers/manual.sh`
MANUAL_ROOT="$VULPIX_DATA/manual"
debug "manual root: $MANUAL_ROOT"

bootstrap_package() {
  info "bootstraping $1"
  local script="library/packages/$1/manual.bootstrap.sh"
  local install_dir="$MANUAL_ROOT/packages/$1"
  debug "bootstrapping at $install_dir"
  if [[ -f "$VULPIX_INSTALL/$script" ]]; then
    local install_cmd="bash '$VULPIX_INSTALL/$script'"
  else
    script="$VULPIX_REPO_RAW/$script"
    info "downloading $script"
    local install_cmd="'$DOWNLOAD' '$script' | bash -s"
  fi
  readarray -t bin_dirs < <(eval "$install_cmd '$install_dir'")
  [[ $? -eq 0 || "${#bin_dirs[@]}" -eq 0 ]] || return 1
  debug "$1 bin dirs: ${bin_dirs[@]}"

  echo # style

  # add to PATH (only for bash session, but that's all that's needed)
  for dir in "${bin_dirs[@]}"; do
    export PATH="$PATH:$install_dir/$dir"
  done
}

# step 1: install source --------------------------------------------------------------------------

clone_source() {
  git clone "$VULPIX_REPO_GIT" "$1" &> >(output)
}

update_source() {
  git -C "$1" pull origin main && git -C "$1" checkout main &> >(output)
}

download_source() {
  tar_cmd="tar -xzv -C '$1' --strip-components=1"
  cmd="$DOWNLOAD '$VULPIX_REPO_TARBALL' | $tar_cmd"
  if ! dir_is_empty "$1"; then
    warn "install dir not empty ($1)"
    verify "overwrite to continue?" || fatal 'install aborted'
  fi
  rm -fr "$1" &>/dev/null
  mkdir -p "$1"
  eval "$cmd" &> >(output)
}

[[ -v VULPIX_INSTALL ]] || fatal "devs didn't define VULPIX_INSTALL in utils.sh"

# determine whether vulpix is already install (if so, we'll basically be updating by bootstrapping)
debug "VULPIX=$VULPIX"
if [[ -z "$OVERRIDE_INSTALL" && -v VULPIX ]]; then
  if [[ -d "$VULPIX" ]]; then
    info 'bootstrapping/updating existing installation at $VULPIX'
    OVERRIDE_INSTALL="$VULPIX"
  else
    warn '$VULPIX is env var but is not a valid directory'
    warn 'cannot determine whether to bootstrap existing installation'
  fi
fi

# check if OVERRIDE_INSTALL or if script dir is a git repo (which we assume is the vulpix repo)
if [[ -n "$OVERRIDE_INSTALL" ]]; then
  export VULPIX_INSTALL="$OVERRIDE_INSTALL"
else
  if command_exists git && is_git_repo "$SCRIPT_DIR"; then
    info "looks like you already cloned vulpix in script dir"
    export VULPIX_INSTALL="$SCRIPT_DIR"
  else
    [[ -d "$SCRIPT_DIR/.git" ]] &&
      warn "looks like script dir might be git repo, but cannot verify"
  fi
fi

info "installing at: $VULPIX_INSTALL"
verify 'is this a good place to install?' || {
  VULPIX_INSTALL=$(prompt 'enter install dir: ')
  VULPIX_INSTALL=$(convert_path_if_needed --unix "$VULPIX_INSTALL")
  export VULPIX_INSTALL="${VULPIX_INSTALL/#~/$HOME}"
  debug "install dir: $VULPIX_INSTALL"
}
echo # style

if command_exists git; then
  if is_git_repo "$VULPIX_INSTALL"; then
    info "updating vulpix at $VULPIX_INSTALL"
    update_source "$VULPIX_INSTALL" || fatal 'fetch or checkout failed'
  else
    info "cloning vulpix at $VULPIX_INSTALL"
    clone_source "$VULPIX_INSTALL" || fatal 'clone failed'
  fi
else
  info "no git, so downloading vulpix to $VULPIX_INSTALL"
  download_source "$VULPIX_INSTALL" || fatal 'download failed'
fi

debug 'chmoding bin/'
chmod a+x "$VULPIX_INSTALL/bin/"*
debug 'chmoding bootstrap'
chmod a+x "$VULPIX_INSTALL/bootstrap."*

echo # style

# step 2: bootstrap dependencies ------------------------------------------------------------------

info "bootstrapping dependencies at $MANUAL_ROOT/packages"

bootstrap_package yq || fatal 'yq bootstrap failed'
command_exists yq || fatal "bootstrap suppossedly succeeded, but yq isn't available"

echo # style

# step 3: init blueprint and config stuff ---------------------------------------------------------

mkdir -p "$VULPIX_CONFIG"
use_defaults=true
if ! dir_is_empty "$VULPIX_CONFIG"; then
  warn "$VULPIX_CONFIG not empty"
  warn "if you don't use the defaults, some setup may not work correctly"
  verify 'keep the current configuration and skip core defaults?' && use_defaults=false
fi
if $use_defaults; then
  info "copying default config to $VULPIX_CONFIG"
  rm -fr "$VULPIX_CONFIG"
  cp --recursive "$VULPIX_INSTALL/config.default" "$VULPIX_CONFIG"
fi

BLUEPRINT="$VULPIX_CONFIG/blueprint.yaml"
[[ -f "$BLUEPRINT" ]] || fatal "no blueprint.yaml in $VULPIX_CONFIG"

# update blueprint.yaml to reflect manual manager packages
info "updating blueprint.yaml to include bootstrapped packages"
blueprint_packages=()
yq_get_array blueprint_packages '.packages[]' "$BLUEPRINT" || fatal "invalid yaml at $BLUEPRINT"
debug "original blueprint_packages: ${blueprint_packages[@]}"
for pkg_dir in "$MANUAL_ROOT/packages/"*; do
  [[ -d "$pkg_dir" ]] || continue
  pkg=$(basename "$pkg_dir")
  [[ -d "$VULPIX_INSTALL/library/packages/$pkg" ]] || continue
  array_has_element blueprint_packages "${pkg}@manual" || blueprint_packages+=("${pkg}@manual")
done
debug "blueprint_packages with bootstrapped: ${blueprint_packages[@]}"
yq_set_array '.packages' blueprint_packages "$BLUEPRINT" || fatal "invalid yaml at $BLUEPRINT"

echo # style

# step 4: vuplix first run ------------------------------------------------------------------------

info "everything should be bootstrapped, but we have to run vulpix for the first time to make env/packages permanent"
info 'running vulpix for initialization (you will have to rerun bootstrap if this fails)'
verify "ready to kick off?" || fatal 'bootstrap aborted'
VULPIX="$VULPIX_INSTALL" bash "$VULPIX_INSTALL/bin/vulpix"
