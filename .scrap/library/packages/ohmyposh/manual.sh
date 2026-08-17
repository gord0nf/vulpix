#!/usr/bin/env bash

INSTALL_DIR="$1"
[[ -z "$INSTALL_DIR" ]] && fatal "no install dir passed"

REPO='JanDeDobbeleer/oh-my-posh'
BINARY='oh-my-posh'
if [[ $OS == 'windows' ]]; then BINARY+='.exe'; fi

get_version() {
  [[ -d "$INSTALL_DIR" && -f "$INSTALL_DIR/$BINARY" ]] || return 1
  version=$("$INSTALL_DIR/$BINARY" --version 2>/dev/null)
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
    [x32]=''
    [arm32]='arm'
  )
  transform_var OS OS_TRANSFORMS
  transform_var ARCH ARCH_TRANSFORMS
  [[ -n "$ARCH" ]] || fatal "architecture not supported"

  url="https://github.com/$REPO/releases/download/$latest_version/posh-$OS-$ARCH"
  if [[ $OS == 'windows' ]]; then url+='.exe'; fi
  file=$(download "$url") || fatal 'download failed'

  mkdir -p "$INSTALL_DIR"
  mv "$file" "$INSTALL_DIR/$BINARY"
  chmod +x "$INSTALL_DIR/$BINARY"
else
  info 'up to date'
fi

echo "$BINARY" # return relative bin
