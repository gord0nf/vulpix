#!/usr/bin/env bash

[[ -v FUNCTIONAL_BLUEPRINT ]] || fatal 'config_scripts.sh requires FUNCTIONAL_BLUEPRINT'

CONFIG_SCRIPTS="$VULPIX_CONFIG/config"

_get_all_config_scripts() {
  local -n scope_packages=$1
  scripts=()
  for package in "${scope_packages[@]}"; do
    scripts+=("$CONFIG_SCRIPTS/$package.d/"*.sh "$CONFIG_SCRIPTS/$package.d/".*.sh)
    if [[ $OS == 'windows' ]]; then
      scripts+=("$CONFIG_SCRIPTS/$package.d/"*.ps1 "$CONFIG_SCRIPTS/$package.d/".*.ps1)
    fi
  done
}

_parse_numbered_script_prefix() {
  [[ "$1" =~ ^([0-9]+).*$ ]] && echo "${BASH_REMATCH[1]}"
}

_sort_config_scripts_by_round() {
  [[ -v scripts ]]

  # sort by number prefix
  local number_prefixes=()
  unnumbered_scripts=()
  for script in "${scripts[@]}"; do
    if number_prefix=$(_parse_numbered_script_prefix "$(basename "$script")"); then
      array_has_element number_prefixes $number_prefix || number_prefixes+=($number_prefix)
      [[ -v numbered_scripts_$number_prefix ]] || declare -g -a numbered_scripts_$number_prefix
      local -n numbered_scripts=numbered_scripts_$number_prefix
      numbered_scripts+=("$script")
    else
      unnumbered_scripts+=("$script")
    fi
  done
  debug "unnumbered_scripts: ${unnumbered_scripts[@]}"
  debug "number prefixes: ${number_prefixes[@]}"

  # order by prefix and make global namerefs for round arrays
  sort_array number_prefixes -n
  debug "sorted number prefixes: ${sorted_array[@]}"
  for ((i = 0; i < ${#sorted_array[@]}; i++)); do
    number_prefix="${sorted_array[$i]}"
    declare -g -n "script_round_$i"="numbered_scripts_$number_prefix"
  done
  if [[ ${#unnumbered_scripts[@]} -gt 0 ]]; then
    declare -g -n "script_round_${#sorted_array[@]}"=unnumbered_scripts
  fi
}

_run_config_script() {
  local script=$1
  local script_name=$(convert_path_if_needed --unix "$(
    realpath --relative-to "$CONFIG_SCRIPTS" "$script"
  )")
  local task_name=$(make_task_name 'config' "${script_name//\//@}")
  case $script in
    *.sh) run_background_task "$task_name" source "$script" ;;
    *.ps1) run_background_task "$task_name" powershell "$script" ;;
  esac
}

configure_packages() {
  local -n packages=$1
  _get_all_config_scripts packages && debug "n config scripts: ${#scripts[@]}"
  _sort_config_scripts_by_round # load into arrays like script_round_0, script_round_1, ...

  # source shared utils
  for script in "$CONFIG_SCRIPTS/shared/"*.sh; do
    local rscript=$(realpath --relative-to "$CONFIG_SCRIPTS" "$script")
    info "sourcing '$rscript'"
    source_script "$script"
  done

  # for each round, run script then wait
  local round=0
  while [[ -v script_round_$round ]]; do
    debug "script_round=script_round_$round"
    unset -n script_round && declare -n script_round=script_round_$round
    debug "script_round_scripts: ${script_round[@]}"
    for script in "${script_round[@]}"; do
      _run_config_script "$script"
    done
    await_tasks
    round=$((round + 1))
  done
}

# hardcoded config script utils -------------------------------------------------------------------

_is_simple_query() {
  [[ "$1" =~ [\.a-zA-Z0-9\[\]]+ ]]
}

# util function for config scripts to access blueprint
blueprint_query() {
  local query=$1
  [[ -n "$2" ]] &&
    local -n var=$2 ||
    local var=

  if [[ "$(yq_safe -r "$query | type" "$FUNCTIONAL_BLUEPRINT")" == 'array' ]]; then
    if _is_simple_query "$query" && [[ "$query" != *"[]" ]]; then
      query+='[]'
    fi
    yq_get_array var "$query" "$FUNCTIONAL_BLUEPRINT"
    [[ -R var ]] || echo "${var[@]}"
  else
    [[ -R var ]] || echo "$var"
  fi
}

# util function for config scripts to access config in blueprint
# (prefer blueprint_query with .config prefix if doing complex yq queries)
config_query() {
  local package=$1 query=$2
  shift && shift
  _is_simple_query "$query" || warn 'vulpix: be careful using config_query() with complex yq queries'
  [[ "$query" == .* ]] || query=".$query"
  ! [[ "$query" == '.' ]] || query=''
  blueprint_query ".config.$package$query" "$@"
}
