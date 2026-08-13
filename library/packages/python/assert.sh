#!/usr/bin/env bash

if ! command_exists python || ! command_exists python3; then
  err 'no python binary'
  return 1
fi

if ! command_exists pip || ! command_exists pip3; then
  err 'python but no pip'
  return 1
fi
