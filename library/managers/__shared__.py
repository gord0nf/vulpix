from abc import ABC, abstractmethod
from logging import Logger

class InvalidPackageError(Exception):
    """thrown when a package is not supported by a manager"""
    pass

class ManagerUnsupported(Exception):

class PackageManager(ABC):
    @abstractmethod
    def check_packages(self, packages: list[str]):
        """
        validates that all the packages are supported.
        @throws InvalidPackageError if a package is not supported
        """
        pass
        
    @abstractmethod
    def get_installed() -> list[str]:
        """returns a list of installed packages"""
        pass

    install_packages: list[str] = []
    uninstall_packages: list[str] = []
    update_packages: list[str] = []

    @abstract_method
    def run(self, logger: Logger):
        """
        Applies corresponding operations on install_packages, uninstall_packages, and
        update_packages.
        """
        pass
