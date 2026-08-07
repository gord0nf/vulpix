# managers

a "manager" is a package manager that vulpix supports abstraction over.

each manager should have a script in `library/managers/` that exports functions (interface is
defined in [the README](../library/managers/README.md))

## beyond package management

there are some special managers that are functional to vulpix features beyond package managment:

- `manual`: used during bootstrap (see
  [here](../library/managers/manual/README.md#significance-during-bootstrap))

## manager list

### manual

custom package manager that is manually implemented by vulpix (hence "manual" from vulpix's
perspective, and from your perspective too if you peek at the code or contribute).

see [here](../library/managers/manual/README.md) for implementation details.

### apt

    name:           apt
    supports_async: false

abstraction over the [apt package manager](https://wiki.debian.org/Apt). handles
installing/updating/removing apt packages as well as updating apt sources as needed. can run in
strict or safe mode.

> [!IMPORTANT]
>
> the apt manager has two modes:
>
> - safe: does not clobber existing packages that are installed before running vulpix. instead, it
>   internally keeps track of apt packages installed through vulpix, and uses that to aligin
>   blueprint with. for example, a bunch of packages are usually installed by default (like sudo,
>   grep, ...) but running `vulpix` without those in your blueprint will not uninstall them. another
>   example, if you first manually run `apt install bash`, `vulpix install bash` will mark "bash" as
>   to_install instead of to_update because bash is not in its internal list.
> - strict: _all_ apt packages installed on the system are aligned with blueprint. more
>   specifically, uses the top-level packages that are not dependencies of other packages as the
>   list, and makes changes to force that list to align with blueprint. so core utils like sudo have
>   to be explicitly defined in blueprint.

> [!TIP]
>
> the apt manager supports the special package name syntax `package_name?` (the whole id would be
> like `bash?@apt`). this means to install the apt package with that id directly (e.g.
> `apt install ${package_name}`), instead of using the aliased package templates defined within the
> vulpix library.

see [here](../library/managers/apt/README.md) for implementation details.
