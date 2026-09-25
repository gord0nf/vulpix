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

from vulpix.core import VulpixError, utils, logging
from vulpix.core.tasks import task_function, ThreadedTaskQueue
from vulpix.package_managers import PackageManager

def template_exists(name: str) -> bool:
    pass # TODO

@task_function
def check_template(package: str, logger: logging.Logger, **_):
    pass # TODO

@task_function
def check_command(package: str, logger: logging.Logger, **_):
    if not utils.command_exists(package):
        raise VulpixError(f"command doesn't exist: {package}")
    logger.info(f"command exists: {package}")

@task_function
def check_force(package: str, logger: logging.Logger, **_):
    logger.info(f"force check: {package}")

class ExpectManager(PackageManager):
    def check_packages(self, *_) -> None:
        pass # expect doesn't have strict packages, see above

    def get_package_diff(self, blueprint_packages: list[str]) -> self.PackageDiff:
        return self.PackageDiff(to_install=blueprint_packages)

    @task_function
    def apply_changes(self, diff: self.PackageDiff, queue: ThreadedTaskQueue, **_) -> None:
        for package in diff.to_install:
            task_name = f"install[{package}@expect]"
            if template_exists(package):
                queue.run_task(task_name, check_template, package)
            elif package.endswith('!'):
                queue.run_task(task_name, check_force, package)
            else:
                queue.run_task(task_name, check_command, package)

package_manager_class = ExpectManager
