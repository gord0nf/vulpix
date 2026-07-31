#!/usr/bin/env bash

BIN="$VULPIX_DATA/manual/bin"
shopt -u nullglob

if [[ -d "$BIN" ]]; then
  global_env_add_path "$BIN"
  for dir in "$BIN/"*; do
    [[ -d "$dir" ]] || continue
    global_env_add_path "$dir"
  done

  # make bins executable
  find "$BIN" -type f -exec chmod +x {} +
fi
