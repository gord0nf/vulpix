#!/usr/bin/env bash

INSTALL_DIR="$1"
[[ -n "$INSTALL_DIR" ]] || fatal "no install dir passed"

REPO='yt-dlp/yt-dlp'
BINARY='yt-dlp'
if [[ $OS == 'windows' ]]; then BINARY+='.exe'; fi

get_version() {
  [[ -d "$INSTALL_DIR" && -f "$INSTALL_DIR/$BINARY" ]] || return 1
  "$INSTALL_DIR/$BINARY" --version 2>/dev/null
}

info 'getting version from github'
latest_version=$(get_latest_github_tag "$REPO") || fatal "couldn't get tag from $REPO"

should_install=$(is_out_of_date get_version "$latest_version") || {
  err 'broken install, reinstalling latest'
  should_install=true
}

debug "should_install=$should_install"

if $should_install; then
  rm -fr "$INSTALL_DIR"
  info "download/extract version $latest_version"

  case $OS in
    linux) file='yt-dlp' ;;
    windows) file='yt-dlp.exe' ;;
    mac) file='yt-dlp_macos' ;;
  esac
  url="https://github.com/$REPO/releases/download/$latest_version/$file"
  file=$(download "$url") || fatal 'download failed'

  mkdir -p "$INSTALL_DIR"
  mv "$file" "$INSTALL_DIR/$BINARY"
  chmod +x "$INSTALL_DIR/$BINARY"
else
  info 'up to date'
fi

echo "$BINARY" # return relative bin
