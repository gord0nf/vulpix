#!/usr/bin/env bash

REPO='neovim/neovim'
INSTALL_DIR="$1"
[[ -z "$INSTALL_DIR" ]] && fatal "no install dir passed"

# try to isntall win32 make if windows as some neovim plugins need it
WIN32MAKE_URL='https://sourceforge.net/projects/gnuwin32/files/make/3.81/make-3.81-bin.zip/download'
WIN32MAKE_INSTALL="$INSTALL_DIR/win32_make"

get_version() {
  [[ -d "$INSTALL_DIR" && -d "$INSTALL_DIR/bin" && -f "$INSTALL_DIR/bin/nvim" ]] || return 1
  "$INSTALL_DIR/bin/nvim" --version 2>/dev/null ||
    sed -nE '1s/.*(v[0-9]+(\.[0-9]+){2}).*/\1/p'
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
    [mac]='macos'
  )
  declare -A ARCH_TRANSFORMS=(
    [x64]='-x86_64'
    [x32]='-x86_64'
    [arm64]='-arm64'
    [arm32]=''
  )
  transform_var OS OS_TRANSFORMS
  transform_var ARCH ARCH_TRANSFORMS
  [[ -n "$ARCH" ]] || fatal "architecture not supported"
  [[ $OS == 'win' && $ARCH == '-x86_64' ]] && ARCH='64'

  file="nvim-${OS}${ARCH}"
  [[ $OS == 'win' ]] && file+='.zip' || file+='.tar.gz'
  url="https://github.com/$REPO/releases/download/$latest_version/$file"
  atomic_download_and_extract "$url" "$INSTALL_DIR" || fatal 'install failed'

  # try to isntall win32 make if windows as some neovim plugins need it
  if [[ $OS == 'win' ]]; then
    info 'download/extract win32 make (not strictly required, but some plugins need it)'
    atomic_download_and_extract "$WIN32MAKE_URL" "$WIN32MAKE_INSTALL" zip ||
      warn "win32 make install failed (not required though)"
    echo 'bin/make' # return relative bin
  fi
else
  info 'up to date'
fi

echo 'bin/nvim' # return relative bin
