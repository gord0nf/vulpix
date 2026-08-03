#!/usr/bin/env

# FONT_INSTALL; only used for linux
is_root &&
  FONT_INSTALL='/usr/share/fonts' ||
  FONT_INSTALL="$HOME/.local/share/fonts"

_install_fonts() {
  local fontdir=$1
  case $OS in
    windows)
      # TODO
      ;;
    linux)
      mkdir -p "$FONT_INSTALL"
      cp -r "$fontdir/"* "$FONT_INSTALL"
      find "$FONT_INSTALL" -type d -print0 | xargs -0 chmod 755
      find "$FONT_INSTALL" -type f -print0 | xargs -0 chmod 644
      command_exists fc-cache && fc-cache | output
      ;;
  esac
}

_pretty_home_path() {
  local path=$(normalize_path "$1")
  [[ "$path" =~ ^"$HOME"(/|$) ]] && path="~${path#$HOME}"
  echo "$path"
}

_print_pretty_link() {
  if ! [[ -v max_item_len ]]; then
    max_item_len=0
    for i in "${!links[@]}"; do
      local pitem=$(_pretty_home_path "$i")
      [[ "${#pitem}" -gt $max_item_len ]] && max_item_len="${#pitem}"
    done
  fi

  local i=$1
  local l=$(_pretty_home_path "${links[$i]}")
  local i=$(_pretty_home_path "$i")
  printf "%s%*s ->  %s\n" "$i" $(($max_item_len - ${#i})) '' "$l"
}

setup_dotfiles() {
  local dotfiles=$1
  [[ -d "$dotfiles" ]] || return 1
  [[ "$dotfiles" == *"/" ]] && dotfiles="${dotfiles%?}"
  shopt -s nullglob globstar

  ignore_file="$dotfiles/.vulpixignore"
  font_dir="$dotfiles/fonts"

  # get ignored paths
  ignored_paths=("$ignore_file" "$font_dir")
  if [[ -f "$ignore_file" ]]; then
    while IFS= read -r ignored; do
      ignored_paths+=("$(normalize_path "$dotfiles/$ignored")")
    done <"$ignore_file"
  fi
  debug "ignoring: ${ignored_paths[@]}"

  declare -A links # like [target_path]=link_path

  # compile link map
  for item in "$dotfiles/"* "$dotfiles/".*; do
    array_has_element ignored_paths "$item" && continue
    if [[ -d "$item" ]]; then
      case "$(basename "$item")" in
        .config)
          for tool in "$item/"*; do
            [[ -d "$tool" ]] || continue
            array_has_element ignored_paths "$tool" && continue
            links["$tool"]="$HOME/.config/$(basename "$tool")"
          done
          continue
          ;;
      esac
    fi

    links["$item"]="$HOME/$(basename "$item")"
  done
  debug "links: $(printf '%s\n' "${links[@]@K}")"

  # make sure we're not overwritting anything
  existing_items=()
  for item in "${!links[@]}"; do
    link="${links[$item]}"
    if [[ "$(readlink "$link" 2>/dev/null)" -ef "$item" ]]; then
      debug "removing existing link at $link"
      rm "$link"
    fi
    if item_exists "$link"; then
      existing_items+=("$link")
    fi
  done
  if [[ "${#existing_items[@]}" -gt 0 ]]; then
    echo "The following items will be overwritting and replaced by links:"
    printf '  %s\n' "${existing_items[@]}"
    echo
    verify "Are you sure you want to continue?" &&
      verify "All these items will be deleted..." ||
      fatal 'aborted'
    for item in "${existing_items[@]}"; do
      rm -fr "$item" || fatal "failed to remove '$item'"
    done
    echo # style
  fi

  # apply symlinks
  if [[ "${#links[@]}" -gt 0 ]]; then
    for item in "${!links[@]}"; do
      link="${links[$item]}"
      [[ -d "$item" ]] && itype=dir || itype=file
      _print_pretty_link "$item" | output
      "${itype}_link" "$link" "$item" || fatal "couldn't creating link at '$link'"
    done
  else
    info 'nothing to symlink'
  fi

  # install fonts
  if [[ -d "$font_dir" ]]; then
    echo # style
    info "installing fonts from '$font_dir'"
    _install_fonts "$font_dir" || warn 'font installation failed'
  fi

  shopt -u nullglob globstar
}
