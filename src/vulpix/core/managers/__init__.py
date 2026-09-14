import importlib
from logging import Logger

from vulpix import VulpixError
from vulpix.core.managers._utils import *

class Manager:
    def check_packages(packages: list[str]) -> None:
        """:raises InvalidPackage: if a package is not supported"""
        raise NotImplementedError("manager did not export check_packages()")

    def get_package_diff(blueprint_packages: list[str]) -> PackageDiff:
        raise NotImplementedError("manager did not export get_package_diff()")

    def apply_changes(diff: PackageDiff, logger: Logger) -> None:
        raise NotImplementedError("manager did not export get_package_diff()")

_required_manager_module_exports = [attr for attr in dir(Manager) if not attr.startswith("__")]

def get_manager(id: str) -> Manager:
    """
    imports the corresponding manager module and loads the core functions into a Manager object.

    NOTE: this was done because importing acts as a cache, so we can call get_manager() during\
    blueprint validation and again during package management, and it doesn't have to reload
    everything.
    """

    try:
        module = importlib.import_module(f".{id}", package=__name__)
    except ModuleNotFoundError:
        raise ManagerUnsupported(id, "manager does not exist")
    
    # load manager methods with monkey patching
    manager = Manager()
    for method_name in _required_manager_module_exports:
        method = getattr(module, method_name, None)
        if not method or not callable(method):
            raise Exception(f"manager did not export {method_name} for {id}")
        setattr(manager, method_name, method)

    return manager
