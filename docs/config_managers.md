# config managers

config managers are given the "config" object defined in your blueprint and a list of packages to
configure, and they decide how to configure the packages.

## vulpix defaults

### `scripts`

basically, config data defined in blueprint gets passed to custom config scripts that you have to
code, which should ideally configure stuff functionally (in other words, you are in charge of the
connection between config data in your blueprint and the actual config for the software). a bunch of
utility functions are also passed. these "custom config scripts" can also be stored in your dotfiles
repo.

## create your own

see [custom managers docs](./managers.md#custom-managers).

your Python module must export a `package_manager_class` variable that contains a subclass of
[`ConfigManager`](../src/vulpix/config_managers/__init__.py).
