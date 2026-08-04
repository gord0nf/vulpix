# manual manager

the manual manager provides custom installation and package management for vulpix.

## installation

the manager owns `$VULPIX_DATA/manual` and is structured like:

```
manual/
├─ packages/
│  ├─ $PACKAGE/
│  │  └─ ...package installation
│  └─ ...other packages
├─ bin/
│  ├─ ...binary symlinks
│  └─ ...directory symlinks
└─ status.yaml
```

`bin` can contain directory symlinks. each immediate subdirectory of `bin` should be added to PATH.
this is necessary because windows without developer mode enabled (which is common for non-admin
users) prevents creation of file symlinks (but not directory symlinks), so we have to cluture PATH
instead.

`status.yaml` is used to determine when to garbage collect packages. when this manager "uninstalls"
a package, it just removes binary linkage, but doesn't actually delete the package until it is not
marked as having a heartbeat for at least 30 days.

`status.yaml` schema:

```yaml
type: object
additionalProperties: false
patternProperties:
    '.*': # package name
        type: object
        properties:
            active:
                type: boolean
            last_active:
                type: string
                format: date
            binaries:
                type: array
                items:
                    type: string
```

### installation scripts

each package has a manual install script at `library/packages/$PACKAGE/manual.sh`. it should take
the following args: `manual.sh <install_dir>`. it's purpose is to do two things:

1. if the install_dir is empty, download and install the package to it
2. if the install_dir is not empty, check package version and update the package if necessary

most importantly: it should return the paths (relative to the install_dir) of binaries or
directories containing binaries, seperated by newlines. (these become part of their entry in
`status.yaml`)

## significance during bootstrap

the manual manager kinda special because it is (hopefully) garunteed to work on any system.
therefore, it is used by the vulpix bootstrap scripts (`bootstrap.sh` and `bootstrap.ps1`) to
install dependencies.

if bash is installed, any package can be bootstrapped by downloading and sourcing `utils.sh` and
`library/managers/manual'/utils.sh`, then running `library/packages/${package}/manual.sh` (make sure
the parent script computes MANUAL_ROOT correctly!). NOTE: `bootstrap.sh` only supports directory
returns from manual.sh.

if on windows and bash isn't installed, a package can be bootstrapped by running
`library/packages/$PACKAGE/manual.bootstrap.ps1` with WindowsPowershell .

properties of `manual.bootstrap.ps1`:

- requires first argument to be `<InstallDir>` (make sure the parent script computes MANUAL_ROOT
  correctly!)
- manaul logs like `Write-Host 'LOG_LEVEL: MESSAGE'`
- return: directories (no files) relative to install_dir containing binaries, each on separate line

> [!NOTE]
>
> if you want, you can migrate these dependencies to other managers after vulpix's bootstrap. its
> just much simpler to default to the manual manager during bootstrap.
