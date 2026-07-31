#!/usr/bin/env bash

prepend_to_file() {
  local text=$(</dev/stdin) file=$1
  echo "$text" | cat - "$file" >/tmp/out && mv /tmp/out "$file"
}
