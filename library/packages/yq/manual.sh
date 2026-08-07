#!/usr/bin/env bash

INSTALL_DIR="$1"
REPO='mikefarah/yq'

[[ -n "$INSTALL_DIR" ]] || fatal "no install dir passed"

get_version() {
  [[ -f "$1" ]] || return 1
  "$1" --version 2>/dev/null | sed -nE 's/.*([0-9]+(\.[0-9]+){2}).*/\1/p'
}

info 'getting version from github'
latest_version=$(get_latest_github_tag "$REPO") || fatal "couldn't get tag from $REPO"

should_install=true

# check if update is necessary
if [[ -d "$INSTALL_DIR" ]]; then
  current_version="v$(get_version "$INSTALL_DIR/yq")"
  if [[ $? -eq 0 ]]; then
    info "$current_version installed vs $latest_version latest"
    if [[ "$current_version" == "$latest_version" ]]; then
      info 'up to date'
      should_install=false
    else
      info 'updating'
    fi
  else
    info 'broken install, reinstalling latest'
  fi
fi

if $should_install; then
  rm -fr "$INSTALL_DIR"
  info "download/extract version $latest_version"

  declare -A OS_TRANSFORMS=([mac]='darwin')
  declare -A ARCH_TRANSFORMS=(
    [x64]='amd64'
    [x32]='386'
    [arm32]='arm'
  )
  transform_var OS OS_TRANSFORMS
  transform_var ARCH ARCH_TRANSFORMS

  binary="yq_${OS}_${ARCH}"
  url="https://github.com/$REPO/releases/download/$latest_version/$binary"
  [[ $OS == windows ]] && url+='.zip' || url+='.tar.gz'
  atomic_download_and_extract "$url" "$INSTALL_DIR" || fatal 'install failed'

  mv "$INSTALL_DIR/$binary" "$INSTALL_DIR/yq"
  chmod +x "$INSTALL_DIR/yq"
fi

echo '.' # return relative bin directory, which is the install dir
