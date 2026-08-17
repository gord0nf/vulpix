#!/usr/bin/env bash

if command_exists pwsh; then
  return 0
fi

if command_exists powershell; then
  warn 'WindowsPowershell (powershell.exe) is installed but this is different than pwsh core'
fi

err 'no pwsh command'
return 1
