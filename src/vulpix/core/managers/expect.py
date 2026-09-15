"""
all 'expect' does is check if the package is already installed (it's not a "true" package manager).
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
from vulpix.core import tasks
from vulpix.core.managers._utils import PackageDiff

def template_exists(name: str) -> bool:
    pass # TODO

@tasks.task_function
def check_template(package: str, logger: Logger, **_):
    pass # TODO

@tasks.task_function
def check_command(package: str, logger: Logger, **_):
    if not command_exists(package):
        raise VulpixError(f"command doesn't exist: {package}")
    logger.info(f"command exists: {package}")

@tasks.task_function
def check_force(package: str, logger: Logger, **_):
    logger.info(f"force check: {package}")

# exports -----------------------------------------------------------------------------------------

def check_packages(packages: list[str]) -> None:
    pass # expect doesn't have strict packages, see above

def get_package_diff(blueprint_packages: list[str]) -> PackageDiff:
    return PackageDiff(to_install=blueprint_packages)

@tasks.task_function
def apply_changes(diff: PackageDiff, queue: ThreadedTaskQueue, **_) -> None:
    for package in diff.to_install:
        task_name = f"install {package}@expect"
        if template_exists(package):
            queue.run_task(task_name, check_template, package)
        elif package.endswith('!'):
            queue.run_task(task_name, check_force, package)
        else:
            queue.run_task(task_name, check_command, package)
