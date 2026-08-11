# vulpix

a cross-platform manager that does magic based on a blueprint (a yaml file) that describes the
desired state of the machine and/or user.

### features

if magic isn't specific enough for you:

- installs/removes packages to align with the blueprint, optionally asyncronously (which makes it
  pretty fast!)

    - the goal is a functional, config-driven, atomic wrapper around package manager(s)
    - since it's a wrapper around other managers, it's not perfect (for example, the apt
      implementation isn't completely atomic)
    - implements it own "manual" manager, which works really well if you don't want to rely on a
      fancy package manager that you don't know what's actually happening behind the scenes...

> [!IMPORTANT]
>
> vulpix is a wrapper around common package managers (e.g. apt); it doesn't do the
> installing/removing itself. although, it does implement a "manual" manager with custom install
> scripts.

- looks for optional dotfiles repo (specified in blueprint) and symlinks everything to correct
  locations.

- allows config yaml in blueprint that you can use to config stuff functionally.

    - basically, config data defined in blueprint gets passed to custom config scripts that you have
      to code, which should ideally configure stuff functionally (in other words, you are in charge
      of the connection between config data in your blueprint and the actual config for the
      software).
    - a bunch of utility functions are also passed
    - these "custom config scripts" can also be stored in your dotfiles repo.

- you can have a root-level blueprint for system-wide packages/config (packages installed globally)
  , in addition to packages/config for specific users (packages installed at user level). plus, you
  can also have "profiles" for further differentiation at the user level.

## installation (bootstrapping)

> [!NOTE]
>
> dependencies:
>
> - bash: primary language of vulpix so obvious dep; prerequisite for linux, installed automatically
>   for windows (see [below](#windows)) by bootstrap script
> - yq: installed automatically by bootstrap script

### linux

run `bootstrap.sh` and follow prompts. this will clone or download this repo (depending on the
availability of git, curl, or wget) to `/opt/vulpix` or `~/.local/opt/vulpix` (depending on root vs
user install preference):

    curl -fsSL https://raw.githubusercontent.com/gord0nf/vulpix/refs/heads/main/bootstrap.sh | bash

alternatively, clone this repo in the desired location and run `bootstrap.sh`.

### windows

run `bootstrap.ps1` and follow prompts. this will clone or download this repo (depending on the
availability of git) to `$ProgramFiles\vulpix` or `$LOCALAPPDATA\Programs\vulpix` (depending on root
vs user install preference):

    iwr -Uri "https://raw.githubusercontent.com/gord0nf/vulpix/refs/heads/main/bootstrap.ps1" | iex

alternatively, clone this repo in the desired location and run `bootstrap.ps1`.

alternatively, you can also use the [linux](#linux) installation if you have bash installed already.

> [!NOTE]
>
> if bootstrap.ps1 cannot find bash, it will install it via
> [Git for Windows](https://git-scm.com/install/windows) (the main alternative is WSL, but that's
> less efficient so it requires explicit setup).

> [!WARNING]
>
> windows hasn't fully been tested so there's likely lots of bugs... await v1.1 for windows-oriented
> fixes/features.

## usage

    usage: vulpix [opts] [subcommand]

    If run as root, applies changes at system level, else only applies at user
    level. This also effects where it looks for app dirs (like configuration).

    options:

      -h, --help        print help
      -v, --version     print version tag
      -b, --blueprint   specify blueprint yaml path, otherwise searches default
                        locations

    subcommands:

      [none]    ...packages   Syncs system/user with blueprint. Equivalent of running
                              'clean', then 'install ...packages', then 'config
                              ...packages' subcommands, where ...packages are the
                              packages passed as args. If no packages are passed,
                              execution is the same, but the '--all' arg is appended
                              to the 'config' cmd.

      clean                   Cleans floating packages. If any packages are
                              installed but are not a package specified in blueprint
                              they will be uninstalled.

      install   ...packages   Syncs *installation* of packages with blueprint. If
                              any packages in the blueprint or args are not
                              installed, they will be installed. If a package passed
                              as an arg is not in the blueprint, it will prompt and
                              require the package to be added to the blueprint
                              before continuing. If any packages are passed,
                              installation sync will only occur for the specified
                              packages, else the entire blueprint is synced.

      config    ...packages|all Syncs *config* of packages with blueprint. It
                                always runs the global config. If any packages are
                              passed as args, it runs the config corresponding to
                              those packages. If 'all' is passed, all packages'
                              configs are ran.

      reinstall ...packages    Uninstalls then reinstalls specified packages (or all
                              packages if none specified). Prompts to add to
                              blueprint if specified packages isn't there.

      replay    <phrase>      For replaying logs of tasks for seeing what went wrong/
                              right and debugging. Searches for logs with phrase as
                              substring and prompts which log to replay if there are
                              multiple.

      dotfiles  <path>        Creates symlinks from stuff in dotfiles path
                              to all the correct locations. If <path> is not
                              supplied, uses the path in blueprint.yaml.

      edit                    Opens config directory in \$EDITOR or \$VISUAL.

      bootstrap               Updates vulpix and reruns bootstrap script. Use if you
                              1) want to update vulpix, or 2) broke something.

    NOTE: ...packages are passed like package_name@manager (example: neovim@manual).
