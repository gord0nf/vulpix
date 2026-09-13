import os
from typing import Literal, Dict, List
from dataclasses import dataclass, field

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
        # validate that all the packages and managers are valid!
        pass # TODO

        # validate that scope_packages is a subset of packages!
        pass # TODO
