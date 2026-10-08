# vulpix

a cross-platform, blueprint-driven system management/configuration tool.

it uses `blueprint.yaml` to abstract two main things:

1. package management: abstracting over package managers (like apt, pip, pacman)
2. configuration management: abstracting over package config managers

> [!IMPORTANT]
>
> vulpix uses a plugin-like architecture for both package and config managers
> ([read this](docs/managers.md)). basically, vulpix is just a pretty cli wrapper around other
> package managers; it doesn't actually do any of the stuff. while it comes with common package
> managers (apt, pip pacman, etc.) and a default config manager, you are encouraged to build
> your own.

some extra features:

- dotfiles setup: looks for optional dotfiles repo and symlinks everything to correct locations
- multithreaded management (depending on manager support)
- you can have a system-wide blueprint that gets run by the root/admin user, in addition to a
  blueprint for specific users 
    - for example, the `apt` manager cannot be used by non-root blueprint

check out the [docs](docs/)!

## installing

if you already have python installed, just:

    pip install vulpix

or if not, you can run the bootstrap script, which installs python, then `pip install`s:

    curl -fsSL https://raw.githubusercontent.com/gord0nf/vulpix/refs/heads/main/bootstrap.sh | bash

windows has its own bootstrap script:

    iwr -Uri "https://raw.githubusercontent.com/gord0nf/vulpix/refs/heads/main/bootstrap.ps1" | iex

## usage

    usage: vulpix [OPTIONS] <COMMAND>

    blueprint-driven system management/configuration tool [ b(￣▽￣)d ]

    positional arguments:
      {sync,dotfiles,blueprint,dotenv,replay}
        sync                syncs system/user with the blueprint
        dotfiles            symlinks dotfiles to system locations
        blueprint           open blueprint in $VISUAL/$EDITOR
        dotenv              source vulpix dotenv in your shell
        replay              replay a log file

    options:
      -h, --help            show this help message and exit
      -v, --version         print version tag
      -V, --verbose         print debug logs
      -w, --whatif          show what would happen without doing anything
      -b, --blueprint PATH  specify blueprint.yaml path, otherwise searches default locations
      --no-fullscreen       no fullscreen/alt screen

and for each subcommand:

    usage: vulpix sync [-h] [-a [REGEX]] [-x [REGEX]] [-r REGEX] [-c [REGEX]]

        syncs system/user with the blueprint

        options:
          -h, --help            show this help message and exit
          -a, --apply [REGEX]   if any packages are in the blueprint but are not installed, they will be installed. if any blueprint packages are already installed, they
                                will be updated.
          -x, --clean [REGEX]   if any packages are installed but are not a package specified in blueprint they will be uninstalled.
          -r, --reinstall REGEX
                                uninstalls then reinstalls matching packages
          -c, --config [REGEX]  runs config managers for the specified packages (or all if no regex). if any other operations are run, only packages corresponding to
                                successful tasks will be run (if at least one task that references a package fails, its config will not be run).

        if no [opts] are supplied, runs with `--clean --apply --config`.


    usage: vulpix dotfiles [-h] [path]

        symlinks dotfiles to system locations

        positional arguments:
          path        if not supplied, uses the path in the blueprint

        options:
          -h, --help  show this help message and exit


    usage: vulpix blueprint [-h]

        open blueprint in $VISUAL/$EDITOR

        options:
          -h, --help  show this help message and exit

    
    usage: vulpix dotenv [-h] [{sh,pwsh}]

        use like `eval "$(vulpix dotenv sh)"` or `vulpix dotenv pwsh | Invoke-Expression` in your profile.

        do not specify <shell> to open dotenv json in $VISUAL/$EDITOR.

        positional arguments:
          {sh,pwsh}

        options:
          -h, --help  show this help message and exit


    usage: vulpix replay [-h] [-l] [REGEX]

        replay a log file prompts if multiple matches

        positional arguments:
          REGEX       filter log files

        options:
          -h, --help  show this help message and exit
          -l, --list  list available logs
