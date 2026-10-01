import argparse
import os
import re
import subprocess
from collections.abc import Callable
from dataclasses import astuple
from pathlib import Path
from typing import Literal

from vulpix import __version__, config_managers, package_managers
from vulpix.cli import logging
from vulpix.cli.task_section import TaskSection, term
from vulpix.core import VulpixError, env
from vulpix.core.blueprint import Blueprint
from vulpix.core.manager_tasks import ManagerTask


def regex_arg(arg: str) -> re.Pattern[str]:
    try:
        return re.compile(arg)
    except re.error:
        raise argparse.ArgumentTypeError(f"'{arg}' is not a valid regular expression.")


def parse_blueprint(path: Path, logger: logging.Logger) -> Blueprint:
    from vulpix.cli.blueprint import expand_blueprint

    _, blueprint = expand_blueprint(path, logger)
    logger.debug(str(blueprint))
    return blueprint


def build_package_filter(
    apply: re.Pattern[str] | None,
    clean: re.Pattern[str] | None,
    reinstall: re.Pattern[str] | None,
) -> Callable:
    def filter_package_changes(
        manager: str, changes: package_managers.PackageManager.PackageDiff
    ):
        def filter_packages(
            packages: list[str], regex: re.Pattern[str], negate=False
        ) -> list[str]:
            if negate:
                return [p for p in packages if not regex.match(f"{p}@{manager}")]
            return [p for p in packages if regex.match(f"{p}@{manager}")]

        # reinstall takes precedent (this is also different since we are telling it to reinstall
        # instead of install/update, rather than just filtering)
        if reinstall is not None:
            force_reinstall = filter_packages(
                [*changes.to_install, *changes.to_update], reinstall
            )
            changes.to_install = filter_packages(
                changes.to_install, reinstall, negate=True
            )
            changes.to_update = filter_packages(
                changes.to_update, reinstall, negate=True
            )
            changes.to_reinstall.extend(force_reinstall)

        # then clean and apply filters
        if clean is None:
            changes.to_install = []
        else:
            changes.to_uninstall = filter_packages(changes.to_uninstall, clean)
        if apply is None:
            changes.to_install = []
            changes.to_update = []
        else:
            changes.to_install = filter_packages(changes.to_install, apply)
            changes.to_update = filter_packages(changes.to_update, apply)

    return filter_package_changes


def package_manage_section(
    blueprint: Blueprint, package_filter: Callable, logger: logging.Logger
):
    if len(blueprint.packages) == 0:
        logger.warning("no package managers in blueprint, skipping package management")
        return

    with TaskSection(
        "package management", blueprint, logger, emote="(*￣０￣)ノ"
    ) as section:
        for manager_id, packages in blueprint.packages.items():
            manager = package_managers.get_manager(manager_id)
            diff = manager.get_package_diff(packages)
            logger.debug(f"packagemanager {manager_id}: {diff}")

            package_filter(manager_id, diff)
            logger.debug(f"filtered diff: {diff}")
            if not any(len(v) > 0 for v in astuple(diff)):
                logger.warning(
                    f"no regex matches, skipping '{manager_id}' package management"
                )
                continue

            task = ManagerTask("package_manager", manager_id)
            task.run(section, manager.apply_changes, args=(diff,))


def package_config_section(
    blueprint: Blueprint, package_filter: Callable, logger: logging.Logger
):
    if len(blueprint.configs) == 0:
        logger.warning("no config managers in blueprint, skipping config management")
        return

    # config managers shouldn't care about package managers, so we just get a list of the package
    # names and give it to the config managers as a hint of what to config.
    packages = [
        p for manager_packages in blueprint.packages.values() for p in manager_packages
    ]
    packages = list(set(packages))
    packages = package_filter(packages)
    logger.debug(f"config packages: {packages}")
    if len(packages) == 0:
        logger.warning(
            "no packages are visible to config (hidden by filtering or failure); running config anyways"
        )

    with TaskSection("config management", blueprint, logger, emote="(^人^)") as section:
        for manager_id, config in blueprint.configs.items():
            manager = config_managers.get_manager(manager_id)
            logger.debug(f"configmanager {manager_id}")

            task = ManagerTask("config_manager", manager_id)
            task.run(section, manager.apply_config, args=(config, packages))


class Cli(argparse.Namespace):
    logger: logging.Logger

    # generic options
    help: bool = False
    version: bool = False
    verbose: bool = False
    blueprint: str | None = None
    whatif: bool = False
    command: Literal["sync", "dotfiles", "blueprint"] | None = None

    # sync command
    apply: re.Pattern[str] | None = None
    clean: re.Pattern[str] | None = None
    config: re.Pattern[str] | None = None
    reinstall: re.Pattern[str] | None = None

    # dotfiles command
    path: str | None = None

    # blueprint command
    edit: bool = False

    # replay command
    log: re.Pattern[str] | None = None

    def __init__(self):
        cool_dude = term.orchid("b(￣▽￣)d")
        parser = argparse.ArgumentParser(
            prog="vulpix",
            description=f"blueprint-driven system management/configuration tool [ {cool_dude} ]",
        )
        parser.add_argument(
            "-v",
            "--version",
            action="version",
            version=__version__,
            help="print version tag",
        )
        parser.add_argument(
            "-V", "--verbose", action="store_true", help="print debug logs"
        )
        parser.add_argument(
            "-w",
            "--whatif",
            action="store_true",
            help="show what would happen without doing anything",
        )
        parser.add_argument(
            "-b",
            "--blueprint",
            type=str,
            metavar="PATH",
            help="specify blueprint.yaml path, otherwise searches default locations",
        )
        parser.add_argument(
            "--no-fullscreen", action="store_true", help="no fullscreen/alt screen"
        )

        subparsers = parser.add_subparsers(dest="command")

        # sync command
        sync_desc = "syncs system/user with the blueprint."
        sync_parser = subparsers.add_parser(
            "sync",
            help=sync_desc,
            description=sync_desc,
            epilog="if no [opts] are supplied, runs with `--clean --apply --config`.",
        )
        sync_parser.add_argument(
            "-a",
            "--apply",
            type=regex_arg,
            metavar="REGEX",
            nargs="?",
            const=".*",
            default=None,
            help="if any packages are in the blueprint but are not installed, they will be "
            "installed. if any blueprint packages are already installed, they will be updated.",
        )
        sync_parser.add_argument(
            "-x",
            "--clean",
            type=regex_arg,
            metavar="REGEX",
            nargs="?",
            const=".*",
            default=None,
            help="if any packages are installed but are not a package specified in blueprint "
            "they will be uninstalled.",
        )
        sync_parser.add_argument(
            "-c",
            "--config",
            type=regex_arg,
            metavar="REGEX",
            nargs="?",
            const=".*",
            default=None,
            help="runs config managers for the specified packages (or all if no regex). the "
            "config for any packages that fail another operation will not be run.",
        )
        sync_parser.add_argument(
            "-r",
            "--reinstall",
            type=regex_arg,
            metavar="REGEX",
            help="uninstalls then reinstalls matching packages.",
        )

        # dotfiles command
        dotfiles_desc = (
            "creates symlinks from stuff in dotfiles path to all the correct locations."
        )
        dotfiles_parser = subparsers.add_parser(
            "dotfiles", help=dotfiles_desc, description=dotfiles_desc
        )
        dotfiles_parser.add_argument(
            "path",
            nargs="?",
            default=None,
            help="if not supplied, uses the path in the blueprint.",
        )

        # blueprint command
        blueprint_desc = "edit the blueprint."
        blueprint_parser = subparsers.add_parser(
            "blueprint", help=blueprint_desc, description=blueprint_desc
        )
        blueprint_parser.add_argument(
            "-e", "--edit", action="store_true", help="open in $VISUAL/$EDITOR."
        )

        # replay command
        replay_desc = "replay a log file."
        replay_parser = subparsers.add_parser(
            "replay",
            help=replay_desc,
            description=f"{replay_desc} prompts if multiple matches.",
        )
        replay_parser.add_argument(
            "log",
            type=regex_arg,
            metavar="REGEX",
            nargs="?",
            default=".*",
            help="filter log files",
        )

        # actaually parse it! -----------------------------------------
        parser.parse_args(namespace=self)
        if not self.command:
            parser.exit(status=1, message=parser.format_help())

        # main logger
        self.logger = logging.getLogger("main")
        logging.attach_log_file(self.logger)
        logging.attach_console_logging(self.logger, verbose=self.verbose)

        # TaskSection settings
        TaskSection.verbose_loggers = self.verbose
        if self.no_fullscreen:
            TaskSection.alt_screen = False

    def sync_command(self, blueprint_path: Path):
        logging.clear_logs()
        blueprint = parse_blueprint(blueprint_path, self.logger)

        # no opts = --clean --apply --config
        if all(
            o is None for o in [self.apply, self.clean, self.config, self.reinstall]
        ):
            self.clean = re.compile(".*")
            self.apply = re.compile(".*")
            self.config = re.compile(".*")

        if any(o is not None for o in [self.apply, self.clean, self.reinstall]):
            package_filter = build_package_filter(
                self.apply, self.clean, self.reinstall
            )
            package_manage_section(blueprint, package_filter, self.logger)

        if self.config is not None:
            config_pattern = self.config
            package_filter = lambda packages: [
                p for p in packages if config_pattern.match(p)
            ]
            package_config_section(blueprint, package_filter, self.logger)

    def dotfiles_command(self, blueprint_path: Path):
        logging.clear_logs()

    def blueprint_command(self, blueprint: Path):
        logging.clear_logs()
        if self.edit:
            blueprint.parent.mkdir(parents=True, exist_ok=True)
            default_editor = "notepad" if env.OS == "windows" else "nano"
            editor = os.getenv("VISUAL", os.getenv("EDITOR", default_editor))

            self.logger.info(f"opening '{editor} {blueprint}'")
            os.chdir(blueprint.parent)
            subprocess.call([editor, str(blueprint)])
            return

        self.logger.warning("nothing to do")

    def replay_command(self):
        self.logger.info("replay")

    def main(self):
        self.logger.debug(str(self))

        blueprint_path = env.CONFIG / "blueprint.yaml"
        if self.blueprint is not None:
            blueprint_path = Path(self.blueprint)
        self.logger.info(f"using blueprint at '{blueprint_path}'")

        if not blueprint_path.exists():
            # TODO: ask if you wanna copy the default
            raise VulpixError(f"expected blueprint file at '{blueprint_path}'")

        match self.command:
            case "sync":
                self.sync_command(blueprint_path)
            case "dotfiles":
                self.dotfiles_command(blueprint_path)
            case "blueprint":
                self.blueprint_command(blueprint_path)
            case "replay":
                self.replay_command()
            case _:
                raise VulpixError("invalid command")
