#!/usr/bin/env bash

if [[ $OS != 'windows' ]]; then
  err 'manual vim install is not supported on linux (would have to build from source)'
  fatal 'you should install vim using your os package manager'
fi

INSTALL_DIR="$1"
[[ -z "$INSTALL_DIR" ]] && fatal "no install dir passed"

REPO='vim/vim-win32-installer'
BINARY='vim.exe'

get_version() {
  [[ -d "$INSTALL_DIR" && -f "$INSTALL_DIR/$BINARY" ]] || return 1
  version=$(
    "$INSTALL_DIR/$BINARY" --version 2>/dev/null |
      sed -nE 's/^.*VIM - Vi IMproved ([0-9]+(\.[0-9]+){1}).*$/\1/p'
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

  declare -A OS_TRANSFORMS=([mac]='' [linux]='')
  declare -A ARCH_TRANSFORMS=([x32]='' [arm32]='')
  transform_var OS OS_TRANSFORMS
  transform_var ARCH ARCH_TRANSFORMS
  [[ -n "$OS" ]] || fatal "os not supported"
  [[ -n "$ARCH" ]] || fatal "architecture not supported"

  url="https://github.com/$REPO/releases/download/$latest_version/gvim_${latest_version:1}_$ARCH.zip"
  atomic_download_and_extract "$url" "$INSTALL_DIR" || fatal 'install failed'
else
  info 'up to date'
fi

echo "$BINARY" # return relative bin
