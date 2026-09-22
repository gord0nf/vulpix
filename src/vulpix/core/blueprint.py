import os
from typing import Literal, Dict, List
from dataclasses import dataclass, field

from vulpix.core import package_managers

_cpu_count = os.cpu_count()

@dataclass
class Settings:
    threads: int = _cpu_count + 4 if _cpu_count else 4
    alt_screen: bool = True
    abort_uninstall_threshold: int = 10
    apt_mode: Literal["safe", "strict"] = "safe"

@dataclass
class Blueprint:
    # target packages established as to base everything on blueprint (dict like [manager]=package_list)
    packages: Dict[str, List[str]]

    # path to dotfiles repo directory
    dotfiles: str | None = None

    # pretty self explanatory...
    settings: Settings = field(default_factory=Settings)

    def __post_init__(self):
        # verify valid managers and packages
        for manager_id, packages in self.packages.items():
            try:
                manager = package_managers.get_manager(manager_id)
                manager.check_packages(packages)
            except package_managers.ManagerUnsupported as e:
                raise ValueError(f"unsupported manager '{e.manager}': {e.message}")
            except package_managers.InvalidPackage as e:
                raise ValueError(f"invalid package '{e.package}' for '{e.manager}' manager")

