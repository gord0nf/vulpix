from abc import ABC, abstractmethod
from logging import Logger

class ManagerUnsupported(Exception):
    """thrown when manager cannot be used on the current system/user"""
    manager: str
    message: str
    def __init__(self, manager: str, message: str):
        this.manager = manager
        this.message = message

class InvalidPackage(Exception):
    """thrown when a package is not supported by a manager"""
    package: str
    manager: str
    def __init__(self, package: str, manager: str):
        this.package = package
        this.manager = manager

class PackageManager(ABC):
    def __init__(self):
        """
        does what the manager needs for init.
        :raises ManagerUnsupportedError: if the manager cannot be used
        """
        pass

    @abstractmethod
    def check_packages(self, packages: list[str]):
        """
        validates that all the packages are supported.
        :raises InvalidPackage: if a package is not supported
        """
        pass
        
    @abstractmethod
    def get_installed(self) -> list[str]:
        """returns a list of installed packages"""
        pass

    install_packages: list[str]
    uninstall_packages: list[str]
    reinstall_packages: list[str]
    update_packages: list[str]

    def __init__(self):
        self.install_packages = []
        self.uninstall_packages = []
        self.reinstall_packages = []
        self.update_packages = []

    @abstractmethod
    def run(self, logger: Logger):
        """
        Applies corresponding operations on install_packages, uninstall_packages, and
        update_packages. Requires logger to be defined.
        """
        pass

    def __repr__(self):
        return f"PackageManager(to_install={self.install_packages}, to_uninstall={self.uninstall_packages}, to_update={self.update_packages}, to_reinstall={self.reinstall_packages})"
