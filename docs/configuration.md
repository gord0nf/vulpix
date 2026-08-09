# configuration

## blueprint

the blueprint is the primary source of truth that acts as a "blueprint" for your system/user. it is
a yaml file (`blueprint.yaml`) located in the config directory. it contains the following
information:

- vulpix settings
- target packages
- target configuration (see [config scripts](#config-scripts))

the vulpix cli applies the blueprint to the system. see `config.default/blueprint.yaml` for an
example. the blueprint is located at `$VULPIX_CONFIG/blueprint.yaml`.

### yaml schema

```yaml
required: [packages]
properties:
    # blueprint meta
    extends:
        description:
            paths to other yaml blueprints to merge the current ontop of (arrays are concated)
        type: array
        items:
            type: string
    profile:
        description: 'alias for extends: $VULPIX_CONFIG/profiles/${value}.yaml'
        type: string

    # main blueprint stuff
    packages:
        description: list of packages for package managers to align to
        type: array
        items:
            description: package like package_name@manager
            type: string
    config:
        type: object
        description: custom, user-defined configuration for use by config-scripts
        properties:
            global: {} # user defined value/properties
        patternProperties:
            '.*': # package name
                {} # user defined value/properties

    # vulpix settings
    dotfiles:
        description: path to dotfiles directory
        type: string
    max_bg_processes:
        description: number to cap async background processes at (default=5)
        type: number
```

## config scripts

the root level `config` property in the [blueprint](#blueprint) has each key corresponding to a
package, with the exception of 'global'. this corresponds to scripts in `$VULPIX_CONFIG/config` that
apply the config details of the blueprint to the system:

```
$VULPIX_CONFIG/config/
├─ shared/
│  ├─ utils.sh
│  └─ ...whatever other shared stuff
├─ global.d/
│  ├─ 00-some-system-script.sh
│  ├─ 00-windows-only-script.ps1
│  ├─ 50-upstream-script.sh
│  └─ ...whatever other scripts
├─ $PACKAGE.d/
│  └─ ...whatever scripts that config $PACKAGE (same format as above)
└─ ...other *.d dirs for package config linkage
```

all of these scripts are optional. they will be run in the 'package coniguration' section of vulpix,
in a [certain order](#execution-order).

> [!NOTE]
>
> `package.d/` style directories can contain powershell scripts but these are only run on windows.

you can think of the `config` blueprint property, being your custom configuration blueprint that
models the system. in this case, your config scripts would be the bridge that actually applies the
config blueprint. this is useful to put in your dotfiles repo.

### developing

> [!TIP]
>
> you should be mindful of [how much](#connection-with-cli) these scripts are executed with the cli
> because it can siginficantly hinder cli execution if they contain heavy operations.

in general, each script should:

- do the minimal possible to achieve goal
- be re-executable, because they probably will be executed relatively often

#### accessing blueprint configuration

use the hardcoded `blueprint_query()` or its wrapper, `config_query()`. these function use yq so
they support complex expressions, but note that the
[two yq implmentations](https://linuxcommandlibrary.com/man/yq#caveats) sometimes have different
syntax. if the query result is an array and a nameref is passed as the second arg, it automagically
loads it into a bash array.

NOTE: `config_query()` just prepends '.config.$package' to the query and runs `blueprint_query()`

#### shared utilities

in addition to all the utililties in `utils.sh` in this repo, all of
`$VULPIX_CONFIG/config/shared/*.sh` are sourced before executing any config script.

### important notes

#### execution order

vulpix supports and provides extra functionality for the `00-script.sh` syntax (i.e. prepending
numbers to the script to define the order it should run; if you've configured linux system tools,
you'll recognize this syntax). any script at the same level (same starting numbers) in any package's
config will be run _in parallel_.

config scripts that do not follow the `00-script.sh` naming syntax will be run in parallel at the
end.

##### example

```
$VULPIX_CONFIG/config/
├─ global.d/
│  ├─ 00-system.sh
│  ├─ 10-env.sh
│  ├─ 10-windows-env.ps1
│  └─ 50-tidy-user.sh
├─ bash.d/
│  ├─ 00-system-env-vars.sh
│  ├─ 30-fancy-prompt.sh
│  └─ other-stuff.sh
└─ mpd.d/
   ├─ 10-systemctl-service-enabled.sh
   ├─ 30-config-file.sh
   └─ 50-tidy-music-dir.sh
```

for example, in the above sample `$VULPIX_CONFIG/config`, the scripts will be run in parallel in the
following rounds (assuming all the packages are in the cli scope):

1. `global.d/00-system.sh`, `bash.d/00-system-env-vars.sh`
2. `global.d/10-env.sh`, `global.d/10-windows-env.ps1` (if windows),
   `mpd.d/10-systemctl-service-enabled.sh`
3. `bash.d/30-fancy-prompt.sh`, `mpd.d/30-config-file.sh`
4. `global.d/50-tidy-user.sh`, `50-tidy-music-dir.sh`
5. `bash.d/other-stuff.sh`

#### connection with cli

any running of `vulpix config ...` always runs the scripts in `global.d/`. so you'd want to keep
these lightweight.

`vulpix config all|...packages` runs config for the specified packages (in addition to global
config).

`vulpix` with no subcommand automagically runs `vulpix config all` as its final step.

#### default configuration scripts

`bootstrap.sh` will copy everything in `config.default/` to `$VUPLIX_CONFIG`.
`config.default/config/` contain scripts that are **HIGHLY RECOMMENDED**, because they:

## dotfiles repos

vulpix works well with 'dotfiles' repos. you can use your preferred tool
([there's a lot of them](https://dotfiles.github.io/utilities/)) and it should work nicely.

dotfiles repos are cool because you can store your `blueprint.yaml` and config scripts there along
with all the package-specific configuration files that, along with the config scripts, make up your
entire system config. apply dotfiles, then run vulpix config, and your good to go.

### managing with vulpix

vulpix also implements its own dotfiles manager if you want to use it. i made this mainly because i
wanted cross-platform dotfiles symlinking. you can specify the directory to look for dotfiles for in
your `blueprint.yaml` or pass it directly to the cli. `vulpix dotfiles <path>` creates symlinks to
all the standard locations (uses blueprint if no `<path>`).

TODO: allow passing github url to dotfiles subcommand.

it expects the following directory structure and symlinks as follows:

```
dotfiles/
├─ .config/
│  ├─ $tool/ -> ~/.config/$tool, ~\AppData\Local\$tool
│  │  └─ ...tool config
│  └─ ...
├─ fonts/ -> wherever your os stores fonts (copies fonts, no symlink)
├─ ...$homedir/ -> ~/$homedir
└─ ...$homefile -> ~/$homefile
```

you can also have a `.vuplixignore` to specify anything that shouldn't be symlinked (although it
doesn't handle all the fancyness that .gitignore handles, like globs).
