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

    name:           manual
    supports_async: true

custom package manager that is manually implemented by vulpix (hence "manual" from vulpix's
perspective, and from your perspective too if you peek at the code or contribute).

see [here](../library/managers/manual/README.md) for implementation details.
