#!/usr/bin/env bash

[[ -v FUNCTIONAL_BLUEPRINT ]] || fatal 'config_scripts.sh requires FUNCTIONAL_BLUEPRINT'

CONFIG_SCRIPTS="$VULPIX_CONFIG/config"

_get_config_scripts() {
  local package=$1
  scripts=()
  if [[ -f "$CONFIG_SCRIPTS/$package.sh" ]]; then scripts+=("$CONFIG_SCRIPTS/$package.sh"); fi
  for script in "$CONFIG_SCRIPTS/$package.d/"*.{sh,ps1}; do
    scripts+=("$script")
  done
}

_configure_package() {
  local package=$1
  _get_config_scripts "$package" # loads $scripts

  [[ "${#scripts[@]}" -gt 0 ]] || {
    info "no scripts"
    return
  }

  info "running '$package' scripts"
  for script in "${scripts[@]}"; do
    local rscript=$(realpath --relative-to "$CONFIG_SCRIPTS" "$script")
    case $script in
      *.sh)
        info "$rscript"
        # start in subshell for access to utils in current env
        (source "$script") || warn "$package: failed $rscript"
        ;;
      *.ps1)
        if [[ $OS == 'windows' ]]; then
          info "$rscript"
          powershell "$script" || warn "$package: failed $rscript"
        fi
        ;;
    esac
  done

}

configure_packages() {
  local -n packages=$1

  # source shared utils
  for script in "$CONFIG_SCRIPTS/shared/"*.sh; do
    local rscript=$(realpath --relative-to "$CONFIG_SCRIPTS" "$script")
    info "sourcing '$rscript'"
    source_script "$script"
  done

  for package in "${packages[@]}"; do
    # TODO: asyncronous config scripts by numbered 00-script.sh format
    run_foreground_task "config $package" _configure_package "$package"
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
