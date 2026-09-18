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

import yaml
import logging
import dacite
import importlib
import importlib.util
from filelock import FileLock, Timeout
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, List

from vulpix import env, VulpixError, utils
from vulpix.core import tasks
from vulpix.core.managers._utils import PackageDiff, InvalidPackage

ROOT_DIR = env.DATA / "manual"
BIN_DIR = ROOT_DIR / "bin"
STATUS_YAML = ROOT_DIR / "status.yaml"
STATUS_LOCK = FileLock(STATUS_YAML.with_suffix(".lock"))
STATUS_TIMEOUT = 10
N_GRACE_DAYS = 30 # number of days before deactivated packages are actually destroyed

main_logger = logging.getLogger("main")

type PackageScript = Callable[[Path, logging.Logger], List[Path]]

def get_package_script(package: str) -> PackageScript:
    try:
        module = importlib.import_module(f".packages.{package}", package=__name__)
    except ModuleNotFoundError:
        raise InvalidPackage(package, "manual")

    main = getattr(module, "main", None)
    if not main or not callable(main):
        raise Exception(f"manual package script for '{package}' did not export main() correctly")
    return main

def get_package_install_dir(package: str) -> Path:
    return ROOT_DIR / f"packages/{package}"

def run_package_script(package: str, logger: logging.Logger) -> list[Path]:
    logger.info(f"running script for package '{package}'")
    package_script = get_package_script(package)
    install_dir = get_package_install_dir(package)

    with utils.AtomicChange(install_dir) as dir:
        binaries = package_script(dir, logger)
    return binaries

# status.yaml operations --------------------------------------------------------------------------

class Status:
    @dataclass
    class PackageStatus:
        active: bool
        last_active: date
        binaries: list[str]

    logger: logging.Logger
    by_package: dict[str, PackageStatus]

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def __enter__(self):
        self.logger.debug(f"loading: {STATUS_YAML}")
        try:
            STATUS_LOCK.acquire(timeout=STATUS_TIMEOUT)
        except Timeout:
            raise VulpixError(f"manual couldn't aquire lock {STATUS_LCOK}")

        with open(STATUS_YAML, "r") as file:
            status = yaml.safe_load(file)
        if status is None:
            status = {}
        if not isinstance(status, dict):
            raise VulpixError(f"invalid status.yaml at '{STATUS_YAML}': not a dict")
        try:
            self.by_package = {
                k: dacite.from_dict(data_class=self.PackageStatus, data=v) for k, v in status.items()
            }
        except dacite.DaciteError as e:
            self.logger.error(str(e))
            raise VulpixError(f"invalid status.yaml at '{STATUS_YAML}'")
        return self
    
    def __exit__(self, exc_type, *_):
        if exc_type is not None:
            return False

        self.logger.debug(f"writing: {STATUS_YAML}")
        with open(STATUS_YAML, "r+") as file:
            file.seek(0)
            file.truncate(0)
            yaml.dump({k: asdict(v) for k, v in self.by_package.items()}, file)

        STATUS_LOCK.release()

    # helper methods ------------------------------------------------------------------------------

    def is_installed(self, package: str) -> bool:
        return package in self.by_package

    def is_active(self, package: str) -> bool:
        return package in self.by_package and self.by_package[package].active

    def destroy_package_entry(self, package: str):
        self.logger.info(f"destroying package entry '{package}'")
        del self.by_package[package]

    def activate_package_entry(self, package: str, bin_paths: list[str]):
        self.logger.info(f"activating package entry '{package}'")
        self.by_package[package] = self.PackageStatus(
            active=True,
            last_active=date.today(),
            binaries=bin_paths
        )

    def deactivate_package_entry(self, package: str):
        self.logger.info(f"deactivating package entry '{package}'")
        self.by_package[package].active = False

    def _get_bin_link_paths(self, package: str, relative_bin: Path, bin_dir: Path) -> tuple[Path, Path]:
        """returns [target path, link path] pair for symlink"""
        install_dir = get_package_install_dir(package).resolve()
        bin = (install_dir / relative_bin).resolve()
        if not bin.exists():
            raise VulpixError(f"invalid binary '{relative_bin}' for {package}")

        if bin.is_dir():
            if bin == install_dir:
                link_name = package
            else:
                salt = str(relative_bin).replace(":", "!").replace("/", "%").replace("\\", "%")
                link_name = package + "_" + salt
        else:
            link_name = bin.name

        return bin, bin_dir / link_name

    def activate_package_binaries(self, package: str):
        self.logger.info(f"activating '{package}' binaries")
        binaries = self.by_package[package].binaries
        with utils.AtomicChange(BIN_DIR) as bin_dir:
            for relative_bin in binaries:
                bin_target, bin_link = self._get_bin_link_paths(package, Path(relative_bin), bin_dir)
                self.logger.debug(f"bin link: '{bin_link}' -> '{bin_target}'")
                if bin_link.exists():
                    utils.rm_link(bin_link)
                utils.link(bin_target, bin_link, self.logger)

    def deactivate_package_binaries(self, package: str):
        self.logger.info(f"deactivating '{package}' binaries")
        binaries = self.by_package[package].binaries
        with utils.AtomicChange(BIN_DIR) as bin_dir:
            for relative_bin in binaries:
                bin_target, bin_link = self._get_bin_link_paths(package, Path(relative_bin), bin_dir)
                if not bin_link.exists():
                    self.logger.warning(f"expected binary to be linked at '{bin_link}'")
                    continue

                self.logger.debug(f"unlinking: {bin_link}")
                utils.rm_link(bin_link)

# main operations ---------------------------------------------------------------------------------

def destory_package(package: str, status: Status):
    status.logger.info(f"destroying package '{package}'")
    utils.rm_fr(get_package_install_dir(package))
    status.destroy_package_entry(package)

@tasks.task_function
def install_package(package: str, logger: logging.Logger, **_):
    """if package not installed, will run install script, then enable the package"""
    logger.info(f"installing package '{package}'")
    status = Status(logger)
    with status:
        if status.is_installed(package):
            logger.info(f"package already installed '{package}'")

    # important: do not lock status while running package script
    package_binaries = run_package_script(package, logger)

    with status:
        status.activate_package_entry(package, [str(b) for b in package_binaries])
        status.activate_package_binaries(package)

@tasks.task_function
def uninstall_package(package: str, logger: logging.Logger, **_):
    """will disable the installation"""
    logger.info(f"uninstalling package '{package}'")
    with Status(logger) as status:
        if status.is_active(package):
            status.deactivate_package_binaries(package)
            status.deactivate_package_entry(package)
        else:
            logger.info(f"'{package}' not installed or already deactivated")

@tasks.task_function
def update_package(package: str, logger: logging.Logger, **_):
    """if package installed, will run install script, then enable the package"""
    logger.info(f"updating package '{package}'")
    status = Status(logger)
    with status:
        if not status.is_installed(package):
            raise VulpixError(f"package '{package}' is not installed, so can't update")

    # important: do not lock status while running package script
    # calling on an already installed package should update it
    package_binaries = run_package_script(package, logger)

    with status:
        status.activate_package_entry(package, [str(b) for b in package_binaries])
        status.activate_package_binaries(package)

@tasks.task_function
def reinstall_package(package: str, logger: logging.Logger, queue: tasks.ThreadedTaskQueue, **_):
    """will destroy the installation, then run install script, then enable the package"""
    logger.info(f"reinstalling package '{package}'")
    with Status(logger) as status:
        destory_package(package, status)

    logger.info("spawning install task")
    task_name = f"install {package}@manual"
    queue.run_foreground_task(task_name, install_package, package)
    if not queue.completed_tasks[task_name]:
        raise VulpixError(f"spawned install task '{task_name}' failed")

@tasks.task_function
def garbage_collection(logger: logging.Logger, **_):
    """actually destroys packages that have been disabled for too long"""
    logger.info('checking for garbage packages')

    cutoff_date = date.today() - timedelta(days=N_GRACE_DAYS)
    with Status(logger) as status:
        garbage_packages = [p for p, s in status.by_package.items() if s.last_active < cutoff_date]
        for package in garbage_packages:
            logger.info(f"'{package}' for garbage collection")
            destory_package(package, status)

# exports -----------------------------------------------------------------------------------------

# verify stuff exists
ROOT_DIR.mkdir(parents=True, exist_ok=True)
BIN_DIR.mkdir(parents=True, exist_ok=True)
STATUS_YAML.touch()

def check_packages(packages: list[str]) -> None:
    for package in packages:
        module_name = f"{__name__}.packages.{package}"
        if importlib.util.find_spec(module_name) is None:
            raise InvalidPackage(package, "manual")

def get_package_diff(blueprint_packages: list[str]) -> PackageDiff:
    diff = PackageDiff()

    with Status(main_logger) as status:
        for package in status.by_package.keys():
            if package in blueprint_packages:
                diff.to_update.append(package)
            else: 
                diff.to_uninstall.append(existing_package)
        for package in blueprint_packages:
            if package not in status.by_package:
                diff.to_install.append(package)
    return diff

@tasks.task_function
def apply_changes(diff: PackageDiff, queue: tasks.ThreadedTaskQueue, **_) -> None:
    spawned_tasks: list[str] = []

    for package in diff.to_uninstall:
        task_name = f"uninstall {package}@manual"
        queue.run_task(task_name, uninstall_package, package)
        spawned_tasks.append(task_name)
    for package in diff.to_reinstall:
        task_name = f"reinstall {package}@manual"
        queue.run_task(task_name, reinstall_package, package)
        spawned_tasks.append(task_name)
    for package in diff.to_install:
        task_name = f"install {package}@manual"
        queue.run_task(task_name, install_package, package)
        spawned_tasks.append(task_name)
    for package in diff.to_update:
        task_name = f"update {package}@manual"
        queue.run_task(task_name, update_package, package)
        spawned_tasks.append(task_name)

    # postsetup garbage_collection
    queue.wait_for_tasks(spawned_tasks)
    queue.run_task("postsetup manual", garbage_collection)
