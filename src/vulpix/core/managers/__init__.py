import pkgutil
import importlib

from ._base import * 

# load into dict, which is the source of truth for available managers
definition_by_id: dict[str, type[PackageManager]] = {}

for finder, module_name, is_pkg in pkgutil.iter_modules(__path__):
    if module_name.startswith('_'):
        continue

    module = importlib.import_module(f".{module_name}", package=__name__)
    PackageManagerClass = getattr(module, "Manager", None)
    if not isinstance(PackageManagerClass, type) or not issubclass(PackageManagerClass, PackageManager):
        raise Exception(f"invalid manager export for {module_name}")
    definition_by_id[module_name] = PackageManagerClass
