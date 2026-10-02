import importlib
import sys
from abc import ABC, abstractmethod
from typing import Any

from vulpix.core.managers import *
from vulpix.core.tasks import task_function


class InvalidBlueprintConfig(Exception):
    """thrown when the blueprint config for a manager is invalid"""

    def __init__(self, manager: str, config_path: list[str], message: str):
        self.manager = manager
        self.location = ".".join(config_path)
        self.message = message

    def __str__(self):
        return f"invalid '{self.manager}' config in blueprint: {self.message} ({self.location})"


class ConfigManager(ABC):
    """base class that all config managers (including external plugins) must inherit from"""

    @abstractmethod
    def check_config(self, config: Any) -> None:
        """
        checks the config object the user has it their blueprint. raises InvalidBlueprintConfig if
        it's not valid.
        """

    @abstractmethod
    @task_function
    def apply_config(self, config: Any, packages: list[str], **_) -> None:
        """
        applies configuration for the specified packages, based on `config` which is the object from
        `config.{manager_name}` section of the user's blueprint (parsed into a dictionary). the
        `packages` array shows the intersection of packages in the blueprint and successfully
        installed/updated/reinstalled packages from package management (if it was run).

        this must be a task_function; it should use the `logger` kwarg for logging, and it has
        the option to spawn more tasks with the `queue` kwarg (like `queue.run_task(...)`).
        """


manager_modules: dict[str, str] = get_manager_modules(namespace=sys.modules[__name__])
manager_cache: dict[str, ConfigManager] = {}


def get_manager(name: str) -> ConfigManager:
    """
    NOTE: the ConfigManager instance of a module is cached and reused when calling this multiple
    times with the same manager. this was done so it doesn't have to reload everything between, for
    example, blueprint validation and package management.
    """

    if name in manager_cache:
        return manager_cache[name]

    if name not in manager_modules:
        raise ManagerUnsupported(name, "cannot find config manager")

    module = importlib.import_module(manager_modules[name])
    manager_instance = get_subclass_export_instance(
        module, "config_manager_class", interface=ConfigManager
    )

    manager_cache[name] = manager_instance
    return manager_instance
