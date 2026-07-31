#!/usr/bin/env bash

set -e

[[ -v GLOBAL_ENV ]] || fatal 'GLOBAL_ENV requirement from shared script is not defined'
[[ -f "$GLOBAL_ENV" ]] || touch "$GLOBAL_ENV"

# make sure shells source dotenv  ----

SUPPORTED_SHELLS=('sh' 'bash' 'zsh' 'powershell' 'pwsh')
sh_profiles=("$HOME/.profile")
bash_profiles=("$HOME/.bashrc" "$HOME/.bash_profile")
zsh_profiles=("$HOME/.zshrc" "$HOME/.zprofile")
powershell_profiles=("$HOME/Documents/WindowsPowerShell/Microsoft.PowerShell_profile.ps1")
[[ $OS == 'windows' ]] &&
  pwsh_profiles=("$HOME/Documents/PowerShell/Microsoft.PowerShell_profile.ps1") ||
  pwsh_profiles=("${XDG_CONFIG_HOME:-$HOME/.config}/powershell/Microsoft.PowerShell_profile.ps1")

for shell in "${SUPPORTED_SHELLS[@]}"; do
  declare -n profiles=${shell}_profiles
  for profile in "${profiles[@]}"; do
    if command_exists "$shell" || [[ -f "$profile" ]]; then
      if ! [[ -f "$profile" ]]; then
        mkdir -p "$(dirname "$profile")"
        touch "$profile"
      fi

      if grep -qE '#!/vulpix/dotenv[[:space:]]*$' "$profile"; then
        debug "dotenv already configured: $profile"
        continue
      fi

      commands=("# apply system dot-env used by 'vulpix'")
      case "$shell" in
        *sh)
          commands+=(
            'set -a'
            "source '$GLOBAL_ENV'"
            'set +a'
          )
          ;;
        powershell)
          commands+=(
            "Get-Content '$GLOBAL_ENV' | ForEach-Object {"
            '  $name, $value = $_.split("=")'
            '  if ($name[-1] -eq "+") {'
            '    $name = $name -replace ".$", ""'
            '    $value = "$(Get-Content env:$name)$value"'
            '  }'
            '  Set-Content env:$name $value'
            '}'
          )
          ;;
      esac
      snippet=$(printf '%s #!vulpix/dotenv\n' "${commands[@]}")
      sed -i '/#!vulpix\/dotenv$/d' "$profile"
      echo "$snippet" | prepend_to_file "$profile"
    fi
  done
done
