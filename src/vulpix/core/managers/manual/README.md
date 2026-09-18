# manual manager

the manual manager provides custom installation and package management for vulpix.

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

`status.yaml` is used to determine when to garbage collect packages. when this manager "uninstalls"
a package, it just removes binary linkage, but doesn't actually delete the package until it is not
marked as having a heartbeat for at least 30 days.

each package has a self contained install script as a submodule of the `packages` package in this
directory. the submodule should export `main(install_dir: Path, logger: Logger) -> list[Path]` but
should be callable as well. it's purpose is to do two things:

1. if the install_dir is empty, download and install the package to it
2. if the install_dir is not empty, check package version and update the package if necessary

most importantly: it should return the paths (within the install_dir) of binaries or
directories containing binaries, seperated by newlines. (these become part of their entry in
`status.yaml`)
