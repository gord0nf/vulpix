#!/usr/bin/env bash

[[ -v BLUEPRINT ]] || fatal 'blueprint.sh requires BLUEPRINT'

FUNCTIONAL_BLUEPRINT="$VULPIX_DATA/blueprint.yaml"
rm -f "$FUNCTIONAL_BLUEPRINT" # recompute each run

_get_extended_path() {
  local path=$(normalize_path "$1")
  local bp=$2
  if [[ "$extends_value" != /* ]]; then
    path="$(dirname "$bp")/$path"
  fi
  echo "$path"
}

# parse blueprint (specifically blueprint meta stuff) and return expanded yaml
_expand_blueprint() {
  local bp=$1
  debug "expanding $bp"

  local extended_blueprints=()
  yq_get_array extended_blueprints '.extends[]' "$bp" || fatal "couldn't parse yaml at '$bp'"
  profile=$(yq_safe -r '.profile' "$bp")
  if [[ -n "$profile" && "$profile" != 'null' ]]; then
    extended_blueprints+=("$VULPIX_CONFIG/profiles/$profile.yaml")
  fi

  local accumulated_yaml=$(mktemp)
  echo '{}' >"$accumulated_yaml"
  for extended in "${extended_blueprints[@]}"; do
    extended=$(_get_extended_path "$extended" "$bp")
    [[ -f "$extended" ]] || fatal "no blueprint at '$extended' (extended by '$bp')"
    _expand_blueprint "$extended" | yq_merge_yamls "$accumulated_yaml" - >"$accumulated_yaml"
  done

  yq_merge_yamls - "$bp" <"$accumulated_yaml"
  rm -f "$accumulated_yaml"
}

_load_settings_from_blueprint() {
  # default setting values
  export DOTFILES=${DOTFILES:-}
  export MAX_PROCESSES=${MAX_PROCESSES:-5}
  export OVERRIDE_TASK_SECTION=${OVERRIDE_TASK_SECTION:-}
  export TASK_SECTION_FOOTER=${TASK_SECTION_FOOTER:-} # true "default" is defined in begin_task_section()
  export NO_AUTO_UNINSTALL_THRESHOLD=${NO_AUTO_UNINSTALL_THRESHOLD:-10}
  export APT_MODE=${APT_MODE:-safe}

  declare -A SETTINGS=(
    [DOTFILES]='.dotfiles'
    [MAX_PROCESSES]='.max_bg_processes'
    [OVERRIDE_TASK_SECTION]='.enable_task_sections'
    [TASK_SECTION_FOOTER]='.tasks_section_footer_height'
    [NO_AUTO_UNINSTALL_THRESHOLD]='.no_auto_uninstall_threshold'
    [APT_MODE]='.apt_mode'
  )

  for setting in "${!SETTINGS[@]}"; do
    blueprint_path="${SETTINGS[$setting]}"
    value=$(yq_safe -r "$blueprint_path" "$FUNCTIONAL_BLUEPRINT") || fatal 'failed to parse blueprint'
    if ! [[ -z "$value" || "$value" == 'null' ]]; then
      export "$setting"="$value"
    fi
    debug "$setting=${!setting}"
  done
}

debug 'computing functional blueprint'
_expand_blueprint "$BLUEPRINT" >"$FUNCTIONAL_BLUEPRINT"

debug 'loading blueprint settings'
_load_settings_from_blueprint

BLUEPRINT_PACKAGES=()
yq_get_array BLUEPRINT_PACKAGES '.packages[]' "$FUNCTIONAL_BLUEPRINT" || fatal "failed to parse blueprint"
debug "BLUEPRINT_PACKAGES: ${BLUEPRINT_PACKAGES[@]}"
