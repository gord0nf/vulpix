#!/usr/bin/env bash

INSTALL_DIR="$1"
[[ -z "$INSTALL_DIR" ]] && fatal "no install dir passed"

get_latest_version() {
  latest_version=$(
    curl 'https://nodejs.org/download/release/latest/' |
      sed -nE 's/^.*node-(v[0-9]+\.[0-9]+\.[0-9]+).*$/\1/p' |
      head -n 1
  )
  [[ -n "$latest_version" ]] && echo "$latest_version"
}

BINS=(
  'bin/node'
  'bin/npx'
  'bin/npm'
)
if [[ $OS == 'windows' ]]; then
  for ((i = 0; i < ${#BINS[@]}; i++)); do
    BINS[$i]="${BINS[$i]}.exe"
  done
fi

get_version() {
  [[ -d "$INSTALL_DIR" && -d "$INSTALL_DIR/bin" ]] || return 1
  for bin in "${BINS[@]}"; do
    [[ -f "$INSTALL_DIR/$bin" ]] || return 1
  done
  "$INSTALL_DIR/${BINS[0]}" --version 2>/dev/null | tail -n 1
}

info 'getting version from github'
latest_version=$(get_latest_version) || fatal "couldn't get version tag from nodejs.org"

should_install=$(is_out_of_date get_version "$latest_version") || {
  err 'broken install, reinstalling latest'
  should_install=true
}

if $should_install; then
  rm -fr "$INSTALL_DIR"
  info "download/extract version $latest_version"

  declare -A OS_TRANSFORMS=(
    [windows]='win'
    [mac]='darwin'
  )
  declare -A ARCH_TRANSFORMS=(
    [x32]=''
    [arm32]=''
  )
  transform_var OS OS_TRANSFORMS
  transform_var ARCH ARCH_TRANSFORMS
  [[ -n "$ARCH" ]] || fatal "architecture not supported"

  url="https://nodejs.org/download/release/$latest_version/node-$latest_version-$OS-$ARCH"
  [[ $OS == 'win' ]] && url+='.zip' || url+='.tar.gz'
  atomic_download_and_extract "$url" "$INSTALL_DIR" || fatal 'install failed'
else
  info 'up to date'
fi

printf '%s\n' "${BINS[@]}" # return relative bin
