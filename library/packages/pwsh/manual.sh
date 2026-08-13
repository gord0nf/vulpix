#!/usr/bin/env bash

INSTALL_DIR="$1"
[[ -z "$INSTALL_DIR" ]] && fatal "no install dir passed"

REPO='PowerShell/PowerShell'
BINARY='pwsh'
if [[ $OS == 'windows' ]]; then BINARY+='.exe'; fi

get_version() {
  [[ -d "$INSTALL_DIR" && -f"$INSTALL_DIR/$BINARY" ]] || return 1
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

  declare -A OS_TRANSFORMS=(
    [windows]='win'
    [mac]='osx'
    [linux]='linux'
  )
  declare -A ARCH_TRANSFORMS=(
    [x32]='x86'
    [arm64]='arm64'
    [arm32]='arm32'
  )
  transform_var OS OS_TRANSFORMS
  transform_var ARCH ARCH_TRANSFORMS

  if [[ $OS == 'win' ]]; then
    file="PowerShell-${latest_version:1}-$OS-$ARCH.zip"
  else
    file="powershell-${latest_version:1}-$OS-$ARCH.tar.gz"
  fi
  url="https://github.com/$REPO/releases/download/$latest_version/$file"
  atomic_download_and_extract "$url" "$INSTALL_DIR" || fatal 'install failed'
else
  info 'up to date'
fi

echo "$BINARY" # return relative bin
