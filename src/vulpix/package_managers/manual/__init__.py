"""
a custom cross platform manager with install scripts for a bunch of packages.

the manager owns `$VULPIX_DATA/manual` and is structured like:
```
manual/
├─ packages/
│  ├─ $PACKAGE/
│  │  └─ ...package installation
│  └─ ...other packages
├─ bin/
│  ├─ ...binary symlinks
│  └─ ...directory symlinks
└─ status.yaml
```

`bin` can contain directory symlinks. each immediate subdirectory of `bin` should be added to PATH.
this is necessary because windows without developer mode enabled (which is common for non-admin
users) prevents creation of file symlinks (but not directory symlinks), so we have to cluture PATH
instead.

`status.yaml` is used to determine when to garbage collect packages. when this manager "uninstalls"
a package, it just removes binary linkage, but doesn't actually delete the package until it is not
marked as having a heartbeat for at least 30 days.

each package has a self contained install script as a submodule of the `packages` package in this
directory. the submodule should export `main(install_dir: Path, logger: Logger) -> list[Path]` but
should be callable as well. it's purpose is to do two things:

1. if the install_dir is empty, download and install the package to it
2. if the install_dir is not empty, check package version and update the package if necessary

most importantly: it should return the paths (within the install_dir) of binaries or
directories containing binaries, seperated by newlines. (these become part of their entry in
`status.yaml`)
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from json import JSONDecodeError
from pathlib import Path
from typing import cast

from dacite import DaciteError

from vulpix.core import dirs, dotenv, logging, system
from vulpix.core.tasks import ThreadedTaskQueue, task_function
from vulpix.package_managers import (
    InvalidPackage,
    ManagerTask,
    PackageDiff,
    PackageManager,
)
from vulpix.utils import (
    AtomicChange,
    DataclassFile,
    VulpixError,
    link,
    path_as_salt,
    rm_fr,
    rm_link,
)

from . import packages as library

ROOT_DIR = dirs.VULPIX_DATA / "manual"
BIN_DIR = ROOT_DIR / "bin"
STATUS_PATH = ROOT_DIR / "status.json"
STATUS_TIMEOUT = 10
N_GRACE_DAYS = 30  # number of days before deactivated packages are actually destroyed

type PackageScript = Callable[[str, logging.Logger], list[str]]


def get_package_script(package: str) -> PackageScript:
    module = library.get_package(package)
    if not module:
        raise InvalidPackage(package, "manual")
    main = getattr(module, "main", None)
    if not main or not callable(main):
        raise TypeError(
            f"manual package script for '{package}' did not export main() correctly"
        )
    return cast(PackageScript, main)


def get_package_install_dir(package: str) -> Path:
    return ROOT_DIR / f"packages/{package}"


def run_package_script(package: str, logger: logging.Logger) -> list[str]:
    logger.info(f"running script for package '{package}'")
    package_script = get_package_script(package)
    install_dir = get_package_install_dir(package)
    return package_script(str(install_dir), logger)


# status.yaml operations --------------------------------------------------------------------------


@dataclass
class PackageStatus:
    active: bool
    last_active: date
    binaries: list[str]


@dataclass
class Status:
    by_package: dict[str, PackageStatus] = field(default_factory=dict)
    _logger: logging.Logger = field(
        init=False, repr=False, default=logging.getLogger("main")
    )

    def is_installed(self, package: str) -> bool:
        return package in self.by_package

    def is_active(self, package: str) -> bool:
        return package in self.by_package and self.by_package[package].active

    def destroy_package_entry(self, package: str):
        self._logger.info(f"destroying package entry '{package}'")
        del self.by_package[package]

    def activate_package_entry(self, package: str, bin_paths: list[str]):
        self._logger.info(f"activating package entry '{package}'")
        self.by_package[package] = PackageStatus(
            active=True,
            last_active=date.today(),  # noqa: DTZ011
            binaries=bin_paths,
        )

    def deactivate_package_entry(self, package: str):
        self._logger.info(f"deactivating package entry '{package}'")
        self.by_package[package].active = False

    def _get_bin_link_paths(
        self, package: str, relative_bin: Path, bin_dir: Path
    ) -> tuple[Path, Path]:
        """returns [target path, link path] pair for symlink"""
        install_dir = get_package_install_dir(package).resolve()
        bin = (install_dir / relative_bin).resolve()
        if not bin.exists():
            raise VulpixError(f"invalid binary '{relative_bin}' for {package}")

        if bin.is_dir():
            if bin == install_dir:
                link_name = package
            else:
                link_name = package + "_" + path_as_salt(relative_bin)
        else:
            link_name = bin.name

        return bin, bin_dir / link_name

    def _link_binaries(self, rel_binaries: list[str], package: str) -> list[Path]:
        """returns all dirs to be added to PATH"""
        bin_dirs: list[Path] = [BIN_DIR]
        with AtomicChange(BIN_DIR, preserve_junctions=True) as bin_dir:
            for relative_bin in rel_binaries:
                bin_target, bin_link = self._get_bin_link_paths(
                    package, Path(relative_bin), bin_dir
                )
                self._logger.debug(f"bin link: '{bin_link}' -> '{bin_target}'")
                if bin_link.exists():
                    rm_link(bin_link)
                link(bin_target, bin_link, self._logger)
                if bin_target.is_dir():
                    bin_dirs.append(BIN_DIR / bin_link.relative_to(bin_dir))
        return bin_dirs

    def _unlink_binaries(self, rel_binaries: list[str], package: str) -> list[Path]:
        """returns all dirs to be removed to PATH"""
        bin_dirs: list[Path] = [BIN_DIR]
        with AtomicChange(BIN_DIR, preserve_junctions=True) as bin_dir:
            for relative_bin in rel_binaries:
                bin_target, bin_link = self._get_bin_link_paths(
                    package, Path(relative_bin), bin_dir
                )
                if not bin_link.exists():
                    self._logger.warning(
                        f"expected binary to be linked at '{bin_link}'"
                    )
                    continue

                self._logger.debug(f"unlinking: {bin_link}")
                rm_link(bin_link)
                if bin_target.is_dir():
                    bin_dirs.append(BIN_DIR / bin_link.relative_to(bin_dir))
        return bin_dirs

    def activate_package_binaries(self, package: str):
        """symlink binaries (if necessary) and add path(s) to dotenv PATH"""
        self._logger.info(f"activating '{package}' binaries")
        binaries = self.by_package[package].binaries
        if system.SUPPORTS_SYMLINKS:
            bin_dirs = self._link_binaries(binaries, package)
        else:
            install_dir = get_package_install_dir(package).resolve()
            binaries = [(install_dir / b).resolve() for b in binaries]
            bin_dirs = [b if b.is_dir() else b.parent for b in binaries]

        self._logger.debug(f"adding to path: {bin_dirs}")
        bin_dirs = [str(b) for b in bin_dirs]
        with dotenv.datafile as env:
            for b in bin_dirs:
                if not b in env.PATH:
                    env.PATH.append(b)

    def deactivate_package_binaries(self, package: str):
        """remove symlink binaries (if necessary) and remove path(s) in dotenv PATH"""
        self._logger.info(f"deactivating '{package}' binaries")
        binaries = self.by_package[package].binaries
        if system.SUPPORTS_SYMLINKS:
            bin_dirs = self._unlink_binaries(binaries, package)
        else:
            install_dir = get_package_install_dir(package).resolve()
            binaries = [(install_dir / b).resolve() for b in binaries]
            bin_dirs = [b if b.is_dir() else b.parent for b in binaries]

        self._logger.debug(f"removing from path: {bin_dirs}")
        bin_dirs = [str(b) for b in bin_dirs]
        with dotenv.datafile as env:
            env.PATH = [p for p in env.PATH if p not in bin_dirs]


def handle_status_error(exc_type: type[Exception], exc_value: Exception) -> bool:
    if issubclass(exc_type, (JSONDecodeError, DaciteError)):
        logging.getLogger("main").error(str(exc_value))
        raise VulpixError(f"invalid status.yaml (for manual) at '{STATUS_PATH}'")
    return False


status_datafile = DataclassFile(
    STATUS_PATH, dclass=Status, on_error=handle_status_error
)


# main operations ---------------------------------------------------------------------------------


def destory_package(package: str, status: Status):
    status._logger.info(f"destroying package '{package}'")
    rm_fr(get_package_install_dir(package))
    status.destroy_package_entry(package)


@task_function
def install_package(package: str, logger: logging.Logger):
    """if package not installed, will run install script, then enable the package"""
    logger.info(f"installing package '{package}'")
    with status_datafile as status:
        status._logger = logger
        if status.is_installed(package):
            logger.info(f"package already installed '{package}'")

    # important: do not lock status while running package script
    package_binaries = run_package_script(package, logger)

    with status_datafile as status:
        status.activate_package_entry(package, package_binaries)
        status.activate_package_binaries(package)


@task_function
def uninstall_package(package: str, logger: logging.Logger):
    """will disable the installation"""
    logger.info(f"uninstalling package '{package}'")
    with status_datafile as status:
        status._logger = logger
        if status.is_active(package):
            status.deactivate_package_binaries(package)
            status.deactivate_package_entry(package)
        else:
            logger.info(f"'{package}' not installed or already deactivated")


@task_function
def update_package(package: str, logger: logging.Logger):
    """if package installed, will run install script, then enable the package"""
    logger.info(f"updating package '{package}'")
    with status_datafile as status:
        status._logger = logger
        if not status.is_installed(package):
            raise VulpixError(f"package '{package}' is not installed, so can't update")

    # important: do not lock status while running package script
    # calling on an already installed package should update it
    package_binaries = run_package_script(package, logger)

    with status_datafile as status:
        status._logger = logger
        status.activate_package_entry(package, package_binaries)
        status.activate_package_binaries(package)


@task_function
def reinstall_package(package: str, logger: logging.Logger, queue: ThreadedTaskQueue):
    """will destroy the installation, then run install script, then enable the package"""
    logger.info(f"reinstalling package '{package}'")
    with status_datafile as status:
        status._logger = logger
        destory_package(package, status)

    logger.info("spawning install task")
    task_name = f"install {package}@manual"
    queue.run_task(task_name, install_package, package)


@task_function
def garbage_collection(logger: logging.Logger):
    """actually destroys packages that have been disabled for too long"""
    logger.info("checking for garbage packages")

    cutoff_date = date.today() - timedelta(days=N_GRACE_DAYS)  # noqa: DTZ011
    with status_datafile as status:
        status._logger = logger
        garbage_packages = [
            p for p, s in status.by_package.items() if s.last_active < cutoff_date
        ]
        for package in garbage_packages:
            logger.info(f"'{package}' for garbage collection")
            destory_package(package, status)


class ManualManager(PackageManager):
    def __init__(self):
        # verify stuff exists and is valid
        ROOT_DIR.mkdir(parents=True, exist_ok=True)
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.touch()
        status_datafile.check()

    def check_packages(self, packages: list[str]) -> None:
        for package in packages:
            if not library.check_package(package):
                raise InvalidPackage(package, "manual")

    def get_package_diff(self, blueprint_packages: list[str]) -> PackageDiff:
        diff = PackageDiff()

        with status_datafile as status:
            for package, pstatus in status.by_package.items():
                if package in blueprint_packages:
                    diff.to_update.append(package)
                elif pstatus.active:
                    diff.to_uninstall.append(package)
            for package in blueprint_packages:
                if package not in status.by_package:
                    diff.to_install.append(package)
        return diff

    @task_function
    def apply_changes(self, diff: PackageDiff, queue: ThreadedTaskQueue) -> None:
        spawned_tasks: list[str] = []

        for package in diff.to_uninstall:
            task = ManagerTask.uninstall(package, manager="manual")
            task.run(queue, uninstall_package, args=(package,))
            spawned_tasks.append(task.name)
        for package in diff.to_reinstall:
            task = ManagerTask.reinstall(package, manager="manual")
            task.run(queue, reinstall_package, args=(package,))
            spawned_tasks.append(task.name)
        for package in diff.to_install:
            task = ManagerTask.install(package, manager="manual")
            task.run(queue, install_package, args=(package,))
            spawned_tasks.append(task.name)
        for package in diff.to_update:
            task = ManagerTask.update(package, manager="manual")
            task.run(queue, update_package, args=(package,))
            spawned_tasks.append(task.name)

        # postsetup garbage_collection
        queue.wait_for_tasks(spawned_tasks)
        ManagerTask(verb="postsetup", manager="manual").run(queue, garbage_collection)


package_manager_class = ManualManager
