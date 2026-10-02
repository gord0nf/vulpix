import os
from dataclasses import dataclass, field
from typing import Any, Literal

from vulpix import config_managers, package_managers

_cpu_count = os.cpu_count()


@dataclass
class Settings:
    threads: int = _cpu_count + 4 if _cpu_count else 4
    alt_screen: bool = True
    abort_uninstall_threshold: int = 10
    apt_mode: Literal["safe", "strict"] = "safe"


@dataclass
class Blueprint:
    # target packages for each package manager to align to (dict like {manager: package_list})
    packages: dict[str, list[str]]

    # target config for each config manager to "align to" (quotes because the manager can really do
    # whatever it wants) (dict like {manager: config_struct}; see individual config manager
    # documentation for specific config_struct shape)
    configs: dict[str, Any]

    # path to dotfiles repo directory (optional)
    dotfiles: str | None = None

    # vulpix settings (optional)
    settings: Settings = field(default_factory=Settings)

    def __post_init__(self):
        # verify package managers and packages
        for manager_id, packages in self.packages.items():
            try:
                manager = package_managers.get_manager(manager_id)
                manager.check_packages(packages)
            except package_managers.ManagerUnsupported as e:
                raise ValueError(f"manager '{e.manager}' not supported: {e.message}")
            except package_managers.InvalidPackage as e:
                raise ValueError(str(e))

        # verify config managers and configs
        for manager_id, config in self.configs.items():
            try:
                manager = config_managers.get_manager(manager_id)
                manager.check_config(config)
            except config_managers.ManagerUnsupported as e:
                raise ValueError(f"manager '{e.manager}' not supported: {e.message}")
            except config_managers.InvalidBlueprintConfig as e:
                raise ValueError(str(e))
