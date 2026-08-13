#!/usr/bin/env bash

# utility functions for manual installs. should be sourced before running a package's manual.sh.

# pipe output of raw logs/output and transform into logs
# if starts with standard prefix, like INFO: ..., it's a raw log and will call corresponding func
# else, just a normal output
# (make sure to redirect stderr if used for logging)
raw_logs_to_logs() {
  while IFS= read -r line; do
    log_type=${line%%:*}
    log_type=${log_type,,} # lowercase
    if [[ "$log_type" == 'error' ]]; then log_type='err'; fi
    if function_exists "$log_type"; then
      log=${line#*:}
      "$log_type" "$(trimstring "$log")" </dev/null
    else
      echo "$line"
    fi
  done
}

get_latest_github_tag() {
  [[ $# -eq 1 ]]
  tag=$(
    curl -L --fail -s "https://api.github.com/repos/$1/releases/latest" |
      sed -nE 's/^.*"tag_name"\s*:\s*"([^"]+)"\s*,?.*$/\1/p'
  ) || return 1
  [[ -n "$tag" ]] && echo "$tag" || {
    err 'empty version tag'
    return 1
  }
}

is_out_of_date() {
  [[ $# -eq 2 ]]
  local get_version="$1" # function
  local latest_version="$2" current_version=

  current_version=$("$get_version") || return 1

  info "$current_version current vs $latest_version latest"
  [[ "$current_version" == "$latest_version" ]] && echo false || echo true
}

transform_var() {
  [[ $# -eq 2 ]]
  local var=$1 value=${!1}
  local -n transform_map=$2
  for original in "${!transform_map[@]}"; do
    if [[ "$value" == "$original" ]]; then
      export "$var"="${transform_map[$original]}"
      return
    fi
  done
}

download() {
  [[ $# -eq 1 ]]
  local url="$1" tmp=$(mktemp)
  curl --ssl-revoke-best-effort --fail -L -o "$tmp" "$url"
  if [[ $? -ne 0 ]]; then
    debug "download failed: $url"
    err "download .../$(basename "$url") failed"
    rm -f "$tmp"
    return 1
  fi
  echo "$tmp"
}
# return 0 if success, 1 if download failed, 2 if extract failed
download_and_extract() {
  [[ $# -ge 2 ]]
  local url=$1 file=$(basename "$1")
  local outdir=$2
  [[ $# -ge 3 ]] && local archive_type=$3 # "zip" | "tar"; optional, falls back to url filename

  local tmp=$(download "$url") || return 1
  trap "rm -f '$tmp'" RETURN

  if [[ -z "${archive_type:-}" ]]; then
    case "$url" in
      *.zip) archive_type=zip ;;
      *.tar | *.tar.*) archive_type=tar ;;
      *)
        err 'could not determine archive type from url'
        return 2
        ;;
    esac
  fi

  case "$archive_type" in
    zip)
      unzip -o -d "$outdir" "$tmp" || {
        err "unzip '$file' failed"
        return 2
      }
      ;;
    tar)
      tar --directory="$outdir" -xf "$tmp" || {
        err "untar '$file' failed"
        return 2
      }
      ;;
  esac

  # remove nested root dirs until the outdir is the root dir
  while true; do
    items=("$outdir/"* "$outdir/".*)
    if [[ "${#items[@]}" -gt 0 ]]; then
      rootdir="${items[0]}"
      if [[ "${#items[@]}" -eq 1 && -d "$rootdir" ]]; then
        mv "$rootdir/"* "$rootdir/".* "$outdir"
        rmdir "$rootdir"
      else
        break
      fi
    fi
  done
}
atomic_download_and_extract() {
  [[ $# -ge 2 ]]
  local url=$1
  local outdir=$2
  shift && shift

  tmpoutdir=$(atomic_change_start "$outdir") || return 1
  mkdir -p "$tmpoutdir"

  download_and_extract "$url" "$tmpoutdir" "$@" || {
    local exitstatus=$?
    atomic_change_abort "$outdir"
    return $exitstatus
  }
  atomic_change_apply "$outdir"
}
