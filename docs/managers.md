# managers

a "manager" is a package manager that vulpix supports abstraction over.

there are two types of managers:

- package managers ([docs](./package_managers.md))
- config managers ([docs](./config_managers.md))

managers are imported like a plugin system. vulpix comes with some default managers, but other
python repos can register their own managers (package or config) as long as they follow an
interface. you're encouraged to [create your own](#custom-managers).

## custom managers

regarding the actual manager, all it has to be is a module that when imported makes a variable named
`package_manager_class`/`config_manager_class` available. this variable should be the definition of
a subclass of the `PackageManager`/`ConfigManager` base class.

regarding making your module visible to vulpix, you have two options (see
[here](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) for more
info):

1. entrypoint metadata (recommended): include the code below in your `pyproject.toml`

```toml
# for package managers:
[project.entry-points.'vulpix.package_managers']
my_package_manager_name = 'my_p_manager_module'

# or for config managers:
[project.entry-points.'vulpix.config_managers']
my_config_manager_name = 'my_c_manager_module'
```

2. namespace package: you can have your module exist in the `vulpix.package_managers` or 
   `vulpix.config_managers` namespace.
   [more details](https://packaging.python.org/en/latest/guides/packaging-namespace-packages/).
