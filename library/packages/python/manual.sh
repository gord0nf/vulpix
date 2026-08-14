#!/usr/bin/env bash

if [[ $OS == 'linux' ]]; then
  err 'manual python install is not supported on linux (would have to build from source)'
  fatal 'you should install python using your os package manager'
fi

INSTALL_DIR="$1"
[[ -z "$INSTALL_DIR" ]] && fatal "no install dir passed"

PY_URL='https://www.python.org/ftp/python/'
BINS=('python.exe' 'pip.exe')

# https://stackoverflow.com/a/65316146
get_latest_version() {
  curl "$PY_URL" |
    sed -n 's!.*href="\([0-9]\+\.[0-9]\+\.[0-9]\+\)/".*!\1!p' |
    sort -rV |
    while read -r version; do
      filename="Python-$version.tar.xz"
      # Versions which only have alpha, beta, or rc releases will fail here.
      # Stop when we find one with a final release.
      if curl --fail --silent --head --output /dev/null "$PY_URL/$version/$filename"; then
        echo "$version"
        break
      fi
    done
}

get_version() {
  [[ -d "$INSTALL_DIR" ]] || return 1
  for bin in "${BINS[@]}"; do
    [[ -f "$INSTALL_DIR/$bin" ]] || return 1
  done
  "$INSTALL_DIR/${BINS[0]}" --version 2>/dev/null |
    sed -nE 's/^.*([0-9]+(\.[0-9]+){2}).*$/\1/p'
}

info 'getting version from github'
latest_version=$(get_latest_version) || fatal "couldn't get version tag from python.org"

should_install=$(is_out_of_date get_version "$latest_version") || {
  err 'broken install, reinstalling latest'
  should_install=true
}

if $should_install; then
  rm -fr "$INSTALL_DIR"
  info "download/extract version $latest_version"

  declare -A OS_TRANSFORMS=([mac]='' [linux]='')
  declare -A ARCH_TRANSFORMS=([x32]='' [arm32]='' [x64]='amd64')
  transform_var OS OS_TRANSFORMS
  transform_var ARCH ARCH_TRANSFORMS
  [[ -n "$OS" ]] || fatal "os not supported"
  [[ -n "$ARCH" ]] || fatal "architecture not supported"

  url="$PY_URL/$latest_version/python-$latest_version-$ARCH.zip"
  atomic_download_and_extract "$url" "$INSTALL_DIR" || fatal 'install failed'
else
  info 'up to date'
fi

echo '.' # return relative bin dir
