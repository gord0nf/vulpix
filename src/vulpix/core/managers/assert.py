from logging import Logger

from vulpix import VulpixError
from vulpix.utils import command_exists
from ._base import PackageManager

class Manager(PackageManager):
    """
    assert isn't really a package manager. all it does is check if the package is already installed,
    and if it is, it succeeds and continues to config (or whatever else). see entry in
    `docs/managers.md` for more details.

    three types of package verification:
    
    - (TODO) if a template exists, runs the template script which can have more complex verification
      logic
    - if a template doesn't exist, just checks that a command with the package name exists
    - if the package name follows the `package_name!` syntax (trailing exclamation mark), no checks
      are done
    """

    def check_packages(self, packages: list[str]):
        pass # assert doesn't have strict packages, see above
        
    def get_installed(self) -> list[str]:
        return [] # assert doesn't have installed state, see above

    logger: Logger

    def template_exists(self, name: str) -> bool:
        pass # TODO

    def check_template(self, name: str):
        pass # TODO

    def check_command(self, name: str):
        if not command_exists(name):
            raise VulpixError(f"command doesn't exist: {name}")
        self.logger.info(f"command exists: {name}")

    def check_force(self, name: str):
        self.logger.info(f"force check: {name}")

    def run(self, logger: Logger):
        self.logger = logger

        # should only be run with install_packages, because it only checks stuff
        if len(self.uninstall_packages) > 0 or len(self.update_packages) > 0:
            raise Exception("invalid usage of assert manager, only handles install_packages")

        for package in self.install_packages:
            if self.template_exists(package):
                self.check_template(package)
            elif package.endswith('!'):
                self.check_force(package)
            else:
                self.check_command(package)
