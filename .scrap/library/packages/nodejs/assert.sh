#!/usr/bin/env bash

commands=('node' 'npm')

for cmd in "${commands[@]}"; do
  if ! command_exists "$cmd"; then
    err "no $cmd"
    return 1
  fi
done
