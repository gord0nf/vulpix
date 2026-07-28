#!/usr/bin/env bash

set -e

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
echo "INFO: downloading utils script"
source <(eval "$DOWNLOAD '$VULPIX_REPO_RAW/utils.sh'")
if [[ $? -ne 0 ]]; then
  echo 'FATAL: failed to download and source utils script'
  exit 1
fi
echo # style

if ! is_root && prompt 'want to install system-wide?'; then
  info 'rerun this script as admin/root/sudo to install globally'
  exit
fi

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
  git clone "$VULPIX_REPO_GIT" "$1"
}

update_source() {
  git -C "$1" pull origin main &&
    git -C "$1" checkout main
}

download_source() {
  tar_cmd="tar -xzv -C '$1' --strip-components=1"
  cmd="$DOWNLOAD '$VULPIX_REPO_TARBALL' | $tar_cmd"
  if ! dir_is_empty "$1"; then
    warn "install dir not empty ($1)"
    prompt "overwrite to continue?" || fatal 'install aborted'
  fi
  rm -fr "$1" &>/dev/null
  mkdir -p "$1"
  eval "$cmd"
}

if command_exists git && is_git_repo "$SCRIPT_DIR"; then
  info "looks like you already cloned vulpix in script dir"
  export VULPIX_INSTALL="$SCRIPT_DIR"
else
  [[ -d "$SCRIPT_DIR/.git" ]] &&
    warn "looks like script dir might be git repo, but cannot verify"
fi

info "installing at: $VULPIX_INSTALL" # defined by default from utils.sh
prompt 'is this a good place to install?' || {
  read -p 'enter install dir: ' VULPIX_INSTALL
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

info "copying default config to $VULPIX_CONFIG"
mkdir -p "$VULPIX_CONFIG"
if ! dir_is_empty "$VULPIX_CONFIG"; then
  warn "$VULPIX_CONFIG not empty"
  warn "if you don't use the defaults, some setup may not work correctly"
  ! prompt 'are you sure you want to keep the current configuration and skip core defaults?'
else
  true
fi
[[ $? -eq 0 ]] && {
  debug 'copying config.default'
  rm -fr "$VULPIX_CONFIG"
  cp --recursive "$VULPIX_INSTALL/config.default" "$VULPIX_CONFIG"
}

# update blueprint.yaml to reflect manual manager packages
BLUEPRINT="$VULPIX_CONFIG/blueprint.yaml"
[[ -f "$BLUEPRINT" ]] || fatal "no blueprint.yaml in $VULPIX_CONFIG"
manual_packages=()
for pkg_dir in "$MANUAL_ROOT/packages/"*; do
  pkg=$(basename "$pkg_dir")
  [[ -d "$pkg_dir" ]] || continue
  [[ -d "$VULPIX_INSTALL/library/packages/$pkg" ]] || continue
  manual_packages+=("${pkg}@manual")
done
debug "manual_packages: ${manual_packages[@]}"
yq_set_array '.packages' manual_packages "$BLUEPRINT" --append || fatal "invalid yaml at $BLUEPRINT"

echo # style

# step 4: vuplix first run ------------------------------------------------------------------------

info "everything should be bootstrapped, but we have to run vulpix for the first time to make env/packages permanent"
info 'running vulpix for initialization (you will have to rerun bootstrap if this fails)'
prompt "ready to kick off?" || fatal 'bootstrap aborted'
VULPIX="$VULPIX_INSTALL" bash "$VULPIX_INSTALL/bin/vulpix"
