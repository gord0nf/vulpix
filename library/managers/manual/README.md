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

packages that supported being bootstrap have `library/packages/$PACKAGE/manual.bootstrap.sh` (bash;
platform agnostic) or `library/packages/$PACKAGE/manual.bootstrap.ps1` (windows only). instead of
first sourcing `library/managers/manual.sh`, as is standard in production, the bootstrap script
calls the `manual.bootstrap.{sh,ps1}` script directly.

properties of `manual.bootstrap.{sh,ps1}`:

- self contained; not dependent on any shell session functions or environment variables
- requires first argument to be `<install_dir>`. it's important that the parent bootstrap script
  computes the correct manual install dir for the package.
- should print logs like "$TYPE: ..." to stderr (e.g. 'FATAL: download stuff failed' or 'INFO: ...')
- returns
    - `manual.bootstrap.sh`: directories relative to install_dir containing binaries, each on
      separate line
    - `manual.bootstrap.ps1`: powershell array of directories relative to install_dir containing
      binaries

> [!NOTE]
>
> if you want, you can migrate these dependencies to other managers after vulpix's bootstrap. its
> just much simpler to default to the manual manager during bootstrap.
