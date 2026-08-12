# managers

a "manager" is a package manager that vulpix supports abstraction over.

each manager should have a script in `library/managers/` that exports functions (interface is
defined in [the README](../library/managers/README.md))

## special managers

there are some special managers that are functional to vulpix features beyond package managment:

- `manual`: used during bootstrap (see
  [here](../library/managers/manual/README.md#significance-during-bootstrap))
- `assert`: shell of a manager that simply trusts that the package is installed so config can be run

## manager list

### manual

    name:           manual
    supports_async: true

custom package manager that is manually implemented by vulpix (hence "manual" from vulpix's
perspective, and from your perspective too if you peek at the code or contribute).

see [here](../library/managers/manual/README.md) for implementation details.

### assert

    name:           manual
    supports_async: true

assert isn't really a package manager. all it does is check if the package is already installed, and
if it is, it succeeds and continues to config (or whatever else). this is useful for many reasons,
but i can think of two right now:

- if a package comes preinstalled on your os (like bash on linux), you can assert its existence in
  your portable blueprint
- if you want a tool available at the user level blueprint, but it needs to be installed system-wide
  (for example, most apt use cases), you can just "assert" in your user blueprint and defer
  installation to your system-wide/root blueprint, however it decides to manage it.

by default, the manager checks if it exists and if not, fails the installation task. there are some
presets for checking the existence of common packages, else it just checks if the name of the
package is a valid command. you can bypass these checks (see the tip below).

> [!TIP]
>
> the assert manager supports the special package name syntax `package_name!` (the whole id would be
> like `bash!@assert`). in this case, literally no checks are preformed (it's just "trust me bro,
> its installed").

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

since apt usually requires being run as root, it's not recommended to put apt packages in your user
blueprint. instead, you can have a system-level root blueprint that defines all the apt packages for
machine. then, if you require some packages for your user, you can defines those packages with the
[assert](#assert) manager.

see [here](../library/managers/apt/README.md) for implementation details.

### pacman

    name:           apt
    supports_async: true (natively)

abstraction over the [pacman package manager](https://wiki.archlinux.org/title/Pacman), which is
important for both Arch Linux (obviously) as well as MSYS2 on windows. handles
installing/updating/removing pacman packages.
