from dataclasses import dataclass, field

class ManagerUnsupported(Exception):
    """thrown when manager cannot be used on the current system/user"""
    manager: str
    message: str
    def __init__(self, manager: str, message: str):
        self.manager = manager
        self.message = message

class InvalidPackage(Exception):
    """thrown when a package is not supported by a manager"""
    package: str
    manager: str
    def __init__(self, package: str, manager: str):
        self.package = package
        self.manager = manager

@dataclass
class PackageDiff():
    to_install: list[str] = field(default_factory=list)
    to_update: list[str] = field(default_factory=list)
    to_reinstall: list[str] = field(default_factory=list)
    to_uninstall: list[str] = field(default_factory=list)
