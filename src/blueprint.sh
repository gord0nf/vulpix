#!/usr/bin/env bash

[[ -v BLUEPRINT ]] || fatal 'blueprint.sh requires BLUEPRINT'

load_settings_from_blueprint() {
  # default setting values
  export DOTFILES=
  export MAX_PROCESSES=5

  declare -A SETTINGS=(
    [DOTFILES]='.dotfiles'
    [MAX_PROCESSES]='.max_bg_processes'
  )

  for setting in "${!SETTINGS[@]}"; do
    blueprint_path="${SETTINGS[$setting]}"
    value=$(yq_safe -r "$blueprint_path" "$BLUEPRINT") || fatal 'failed to parse blueprint'
    if ! [[ -z "$value" || "$value" == 'null' ]]; then
      export "$setting"="$value"
    fi
    debug "$setting=${!setting}"
  done
}

debug 'loading blueprint settings'
load_settings_from_blueprint
