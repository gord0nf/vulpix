#!/usr/bin/env bash

INSTALL_DIR="$1"
[[ -z "$INSTALL_DIR" ]] && fatal "no install dir passed"

REPO='junegunn/fzf'
BINARY='fzf'
if [[ $OS == 'windows' ]]; then BINARY+='.exe'; fi

get_version() {
  [[ -d "$INSTALL_DIR" && -f "$INSTALL_DIR/$BINARY" ]] || return 1
  version=$(
    "$INSTALL_DIR/$BINARY" --version 2>/dev/null |
      sed -nE 's/^.*([0-9]+(\.[0-9]+){2}).*$/\1/p'
  )
  [[ -n "$version" ]] && echo "v$version"
}

info 'getting version from github'
latest_version=$(get_latest_github_tag "$REPO") || fatal "couldn't get tag from $REPO"

should_install=$(is_out_of_date get_version "$latest_version") || {
  err 'broken install, reinstalling latest'
  should_install=true
}

if $should_install; then
  rm -fr "$INSTALL_DIR"
  info "download/extract version $latest_version"

  declare -A OS_TRANSFORMS=([mac]='darwin')
  declare -A ARCH_TRANSFORMS=(
    [x64]='amd64'
    [arm32]='armv7'
    [x32]=''
  )
  transform_var OS OS_TRANSFORMS
  transform_var ARCH ARCH_TRANSFORMS
  [[ -n "$ARCH" ]] || fatal "architecture not supported"

  url="https://github.com/$REPO/releases/download/$latest_version/fzf-${latest_version:1}-${OS}_${ARCH}"
  [[ $OS == 'windows' ]] && url+='.zip' || url+='.tar.gz'
  atomic_download_and_extract "$url" "$INSTALL_DIR" || fatal 'install failed'
else
  info 'up to date'
fi

echo "$BINARY" # return relative bin
