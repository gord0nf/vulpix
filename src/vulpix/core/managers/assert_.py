"""
all 'assert' does is check if the package is already installed (it's not a "true" package manager).
see entry in `docs/managers.md` for more details.

three types of package verification:

- (TODO) if a template exists, runs the template script which can have more complex verification
  logic
- if a template doesn't exist, just checks that a command with the package name exists
- if the package name follows the `package_name!` syntax (trailing exclamation mark), no checks
  are done (the package in the blueprint is more of a comment at this point)
"""

from logging import Logger

from vulpix import VulpixError
from vulpix.utils import command_exists
from vulpix.core.managers._utils import PackageDiff

def template_exists(name: str) -> bool:
    pass # TODO

def check_template(name: str, logger: Logger):
    pass # TODO

def check_command(name: str, logger: Logger):
    if not command_exists(name):
        raise VulpixError(f"command doesn't exist: {name}")
    logger.info(f"command exists: {name}")

def check_force(name: str, logger: Logger):
    logger.info(f"force check: {name}")

# exports -----------------------------------------------------------------------------------------

def check_packages(packages: list[str]) -> None:
    pass # assert doesn't have strict packages, see above

def get_package_diff(blueprint_packages: list[str]) -> PackageDiff:
    return PackageDiff(to_install=blueprint_packages)

def apply_changes(diff: PackageDiff, logger: Logger) -> None:
    for package in diff.to_install:
        if template_exists(package):
            check_template(package, logger)
        elif package.endswith('!'):
            check_force(package, logger)
        else:
            check_command(package, logger)
