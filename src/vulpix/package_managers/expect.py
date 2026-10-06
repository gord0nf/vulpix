"""
all 'expect' does is check if the package is already installed (it's not a "true" package manager).
see entry in `docs/package_managers.md` for more details.

three types of package verification:

- (TODO) if a template exists, runs the template script which can have more complex verification
  logic
- if a template doesn't exist, just checks that a command with the package name exists
- if the package name follows the `package_name!` syntax (trailing exclamation mark), no checks
  are done (the package in the blueprint is more of a comment at this point)
"""

from vulpix.core import logging
from vulpix.core.tasks import ThreadedTaskQueue, task_function
from vulpix.package_managers import ManagerTask, PackageDiff, PackageManager
from vulpix.utils import VulpixError, command_exists


def template_exists(name: str) -> bool:
    return False  # TODO


@task_function
def check_template(package: str, logger: logging.Logger):
    pass  # TODO


@task_function
def check_command(package: str, logger: logging.Logger):
    if not command_exists(package):
        raise VulpixError(f"command doesn't exist: {package}")
    logger.info(f"command exists: {package}")


@task_function
def check_force(package: str, logger: logging.Logger):
    logger.info(f"force check: {package}")


class ExpectManager(PackageManager):
    def check_packages(self, packages: list[str]) -> None:
        pass  # expect doesn't have strict packages, see above

    def get_package_diff(self, blueprint_packages: list[str]) -> PackageDiff:
        return PackageDiff(to_install=blueprint_packages)

    @task_function
    def apply_changes(self, diff: PackageDiff, queue: ThreadedTaskQueue) -> None:
        for package in diff.to_install:
            if template_exists(package):
                task_func = check_template
            elif package.endswith("!"):
                task_func = check_force
            else:
                task_func = check_command

            task = ManagerTask(verb="check", package=package, manager="expect")
            task.run(queue, task_func, args=(package,))


package_manager_class = ExpectManager
