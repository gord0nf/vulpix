"""
contains manager utils. managers can either be namespace packages or packages regsistered under
an entry point group.
"""

import pkgutil
from abc import ABC
from types import ModuleType
from importlib.metadata import entry_points

class ManagerUnsupported(Exception):
    """thrown when manager cannot be used on the current system/user"""
    manager: str
    message: str
    def __init__(self, manager: str, message: str):
        self.manager = manager
        self.message = message

def _get_namespace_modules(namespace_pkg: ModuleType) -> dict[str, str]:
    modules = pkgutil.iter_modules(namespace_pkg.__path__, namespace_pkg.__name__ + ".")
    return {m.name.split(".")[-1]: m.name for m in modules}

def _get_entry_point_modules(group: str) -> dict[str, str]:
    return {e.name: e.module for e in entry_points(group=group)}

def get_manager_modules(namespace: ModuleType) -> dict[str, str]:
    """returns dicts like {manager_name: import_string}"""
    namespace_modules = _get_namespace_modules(namespace)
    entry_point_modules = _get_entry_point_modules(namespace.__name__)
    return namespace_modules | entry_point_modules

def get_subclass_export_instance[T: ABC](module: ModuleType, export: str, interface: type[T]) -> T:
    if not hasattr(module, export):
        raise ManagerUnsupported(module.__name__, f"module imported but expected '{export}' to be exported")
    manager_class = getattr(module, export)
    if not issubclass(manager_class, interface):
        raise ManagerUnsupported(module.__name__, f"module imported but '{export}' is not subclass of {interface}")
    return manager_class()
