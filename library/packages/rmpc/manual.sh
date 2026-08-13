#!/usr/bin/env bash

INSTALL_DIR="$1"
[[ -z "$INSTALL_DIR" ]] && fatal "no install dir passed"

REPO='mierak/rmpc'
BINARY='rmpc'

get_version() {
  [[ -d "$INSTALL_DIR" && -f "$INSTALL_DIR/$BINARY" ]] || return 1
  "$INSTALL_DIR/$BINARY" version 2>/dev/null |
    sed -nE 's/^.*(v[0-9]+(\.[0-9]+){2}).*$/\1/p'
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

  declare -A OS_TRANSFORMS=(
    [windows]=''
    [mac]='apple-darwin'
    [linux]='unknown-linux-gnu'
  )
  declare -A ARCH_TRANSFORMS=(
    [x64]='x86_64'
    [x32]='x86_64'
    [arm64]='aarch64'
    [arm32]=''
  )
  transform_var OS OS_TRANSFORMS
  transform_var ARCH ARCH_TRANSFORMS
  [[ -n "$ARCH" ]] || fatal "architecture not supported"
  [[ -n "$OS" ]] || fatal "os not supported"

  [[ $OS == 'win' ]] && file+='.zip' || file+='.tar.gz'
  url="https://github.com/$REPO/releases/download/$latest_version/rmpc-$latest_version-$ARCH-$OS.tar.gz"
  atomic_download_and_extract "$url" "$INSTALL_DIR" || fatal 'install failed'
else
  info 'up to date'
fi

echo "$BINARY" # return relative bin
