CONFIG_SCRIPTS="$VULPIX_CONFIG/config"
BLUEPRINT="${BLUEPRINT:-$VULPIX_CONFIG/blueprint.yaml}"

_get_config_scripts() {
  local package=$1
  scripts=()
  [[ -f "$CONFIG_SCRIPTS/$package.sh" ]] && scripts+=("$CONFIG_SCRIPTS/$package.sh")
  for script in "$CONFIG_SCRIPTS/$package.d/"*.{sh,ps1}; do
    scripts+=("$script")
  done
}

configure_packages() {
  local -n packages=$1
  shopt -s nullglob

  # source shared utils
  for script in "$CONFIG_SCRIPTS/shared/"*.sh; do
    local rscript=$(realpath --relative-to "$CONFIG_SCRIPTS" "$script")
    info "config: sourcing '$rscript'"
    source_script "$script"
  done

  for package in "${packages[@]}"; do
    _get_config_scripts "$package" # loads $scripts

    [[ "${#scripts[@]}" -gt 0 ]] || {
      info "config: no scripts for '$package'"
      continue
    }

    info "config: running '$package' scripts"
    for script in "${scripts[@]}"; do
      local rscript=$(realpath --relative-to "$CONFIG_SCRIPTS" "$script")
      case $script in
        *.sh)
          info "config: $rscript"
          # start in subshell for its very own env
          (source "$script") || warn "config: $package: failed $rscript"
          ;;
        *.ps1)
          if [[ $OS == 'windows' ]]; then
            info "config: $rscript"
            powershell "$script" || warn "config: $package: failed $rscript"
          fi
          ;;
      esac

    done
  done

  shopt -u nullglob
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

  if [[ "$(yq_safe -r "$query | type" "$BLUEPRINT")" == 'array' ]]; then
    if _is_simple_query "$query" && [[ "$query" != *"[]" ]]; then
      query+='[]'
    fi
    yq_get_array var "$query" "$BLUEPRINT"
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
  [[ "$query" == '.' ]] && query=
  blueprint_query ".config.$package$query" "$@"
}
