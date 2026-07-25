#!/usr/bin/env bash

INSTALL_DIR="$1"
REPO='mikefarah/yq'

[[ -z "$INSTALL_DIR" ]] && {
  echo "FATAL: no install dir passed" >&2
  exit 1
}

get_latest_github_tag() {
  curl --fail -s "https://api.github.com/repos/$REPO/releases/latest" |
    grep -E -o '.*"tag_name".*:.+' |
    sed 's/^.*:\s*"\(.*\)".*$/\1/'
}

# exports $OS as 'windows' | 'linux' | 'mac'
get_os() {
  if grep -qEi "(Microsoft|WSL|MSYS)" /proc/version &>/dev/null; then
    OS=windows
  else
    case "$OSTYPE" in
      darwin*) OS=darwin ;;
      solaris* | linux* | bsd* | freebsd*) OS=linux ;;
      msys* | cygwin* | win32*) OS=windows ;;
      *)
        echo 'FATAL: could not determine os; please define $OSTYPE.' >&2
        exit 1
        ;;
    esac
  fi
}

# exports $ARCH as 'x64' | 'x32' | 'arm32' | 'arm64'
get_arch() {
  local commands=(
    "uname -m | tr '[:upper:]' '[:lower:]'"
    'arch'
  )
  for cmd in "${commands[@]}"; do
    case $(eval "$cmd") in
      x86_64*) ARCH=amd64 ;;
      i*86) ARCH=386 ;;
      arm64 | aarch64) ARCH=arm64 ;;
      arm*) ARCH=arm ;;
    esac
    [[ -n "$ARCH" ]] && break
  done
  [[ -n "$ARCH" ]] || {
    echo 'FATAL: could not determine arch' >&2
    exit 1
  }
}

download_and_extract() {
  tmp=$(mktemp)
  curl -L --fail --output "$tmp" "$1" || return 1
  case $1 in
    *.tar*) tar -C "$2" -xf "$tmp" ;;
    *.zip) unzip -d "$2" "$tmp" ;;
  esac
  status=$?
  rm -f "$tmp"
  return $status
}

if [[ -d "$INSTALL_DIR" ]]; then
  echo "INFO: already installed" >&2
else
  get_os
  get_arch
  mkdir -p "$INSTALL_DIR"

  echo 'INFO: getting version from github' >&2
  version=$(get_latest_github_tag) || exit 1

  echo "INFO: downloading version $version" >&2
  binary="yq_${OS}_${ARCH}"
  url="https://github.com/$REPO/releases/download/$version/$binary"
  [[ $OS == windows ]] && url+='.zip' || url+='.tar.gz'
  download_and_extract "$url" "$INSTALL_DIR" || {
    echo 'FATAL: install failed' >&2
    exit 1
  }

  mv "$INSTALL_DIR/$binary" "$INSTALL_DIR/yq"
  chmod +x "$INSTALL_DIR/yq"
fi

[[ -f "$INSTALL_DIR/yq" ]] || echo "WARN: yq not in install dir" >&2
echo "$INSTALL_DIR" # return bin directory
