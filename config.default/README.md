# default vulpix config

## global config scripts

the `config/global.d/00-*.sh` scripts do some pretty important stuff:

- init the global .env file (see below)
- make `vulpix` executable
    - add `bin/` of this repo to PATH to make `vulpix` accessible
    - make $VULPIX env var permanent, which is required to execute `vulpix`
- add binaries installed by the 'manual' manager to PATH

make sure you know what you're doing before editing them.

### global .env

> [!TIP]
>
> if you have vulpix config in your dotfiles repo, add ~/.config/vulpix/.env to your `.gitignore`.

the global config scripts create `$VULPIX_CONFIG/.env`, which is formatted like a standard
[dotenv](https://github.com/php-xdg/dotenv-spec) file. the global scripts also make sure the
profiles of common shells (sh, bash, powershell, zsh, etc.) source the global .env and export all
the variables as env vars.

i'm not really sure if the 'dot-env' standard supports the `VAR+=...` syntax, but since most shells
are cool with it, the global .env uses it.

paths in .env should propably be stored in unix format, because they can be translated in config
scripts if windows path is needed.
