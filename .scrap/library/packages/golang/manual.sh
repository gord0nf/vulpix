#!/usr/bin/env bash

INSTALL_DIR="$1"
[[ -z "$INSTALL_DIR" ]] && fatal "no install dir passed"

GO_URL='https://go.dev'

get_latest_version() {
  latest_version=$(
    curl --ssl-revoke-best-effort "$GO_URL/VERSION?m=text" |
      grep -P '^go\d+\.\d+\.\d+$'
  )
  [[ -n "$latest_version" ]] && echo "$latest_version"
}

BINS=('bin/go' 'bin/gofmt')
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
  "$INSTALL_DIR/${BINS[0]}" version 2>/dev/null |
    sed -nE 's/^.*(go[0-9]+(\.[0-9]+){2}).*$/\1/p'
}

info 'getting latest version number'
latest_version=$(get_latest_version) || fatal "couldn't get version tag from nodejs.org"

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
    [x32]='386'
    [arm32]='armv6l'
  )
  transform_var OS OS_TRANSFORMS
  transform_var ARCH ARCH_TRANSFORMS

  url="$GO_URL/dl/$latest_version.$OS-$ARCH"
  [[ $OS == 'windows' ]] && url+='.zip' || url+='.tar.gz'
  atomic_download_and_extract "$url" "$INSTALL_DIR" || fatal 'install failed'
else
  info 'up to date'
fi

printf '%s\n' "${BINS[@]}" # return relative bins
