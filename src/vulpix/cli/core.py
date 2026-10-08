import argparse
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from vulpix import config_managers, package_managers, utils
from vulpix.cli import logging
from vulpix.cli.task_section import TaskSection, emotes, term
from vulpix.core import VulpixError, blueprint, dirs, dotenv, dotfiles
from vulpix.core.manager_tasks import ManagerTask, completed_package_tasks


def build_package_filter(
    apply: re.Pattern[str] | None,
    clean: re.Pattern[str] | None,
    reinstall: re.Pattern[str] | None,
) -> Callable:
    def filter_package_changes(manager: str, changes: package_managers.PackageDiff):
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
            changes.to_uninstall = []
        else:
            changes.to_uninstall = filter_packages(changes.to_uninstall, clean)
        if apply is None:
            changes.to_install = []
            changes.to_update = []
        else:
            changes.to_install = filter_packages(changes.to_install, apply)
            changes.to_update = filter_packages(changes.to_update, apply)

    return filter_package_changes


def task_summary(tasks: dict[ManagerTask, bool]) -> str:
    fmark, smark = term.red("failure"), term.green("success")
    failed = [
        f"  - {task.name} ({fmark})" for task, success in tasks.items() if not success
    ]
    succeeded = [
        f"  - {task.name} ({smark})" for task, success in tasks.items() if success
    ]
    failed.sort()
    succeeded.sort()
    return "\n".join([*failed, *succeeded]) + "\n"


def print_section_summary(tasks: dict[ManagerTask, bool], logger: logging.Logger):
    tasks_failed = any(not status for status in tasks.values())
    if tasks_failed:
        logger.warning(
            "some package tasks failed (`vulpix replay <task>` to check logs)"
        )

    em = emotes["failure"] if tasks_failed else emotes["success"]
    print(f"[{em}] summary:\n" + task_summary(tasks))


class Cli(argparse.Namespace):
    type Command = Literal["sync", "dotfiles", "blueprint", "replay", "dotenv"]

    logger: logging.Logger

    # generic options
    help: bool = False
    version: bool = False
    verbose: bool = False
    blueprint: str | None = None
    whatif: bool = False
    command: Command | None = None

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
    list: bool = False

    # dotenv command
    shell: Literal["sh", "pwsh"] | None

    def init_console_logging(self):
        """this is the minimium required logger after settings have been populated"""
        self.logger = logging.getLogger("main")
        logging.attach_console_logging(self.logger, verbose=self.verbose)

        # TaskSection settings
        TaskSection.verbose_loggers = self.verbose
        if self.no_fullscreen:
            TaskSection.alt_screen = False

    def init_file_logging(self):
        """
        this initializes a main portion of the cli by clearing log files and attaching main log
        file. this is seperate from __init__() because some subcommands require logs... those
        subcommands just have fileless main logging.
        """
        logging.clear_logs()
        logging.attach_log_file(self.logger)

    # cli utils -----------------------------------------------------------------------------------

    def get_blueprint_path(self) -> Path:
        blueprint_path = dirs.VULPIX_CONFIG / "blueprint.yaml"
        if self.blueprint is not None:
            blueprint_path = Path(self.blueprint)

        self.whatif_log(f"blueprint: {blueprint_path}")
        if not blueprint_path.exists():
            # TODO: ask if you wanna copy the default
            raise VulpixError(f"expected blueprint file at '{blueprint_path}'")

        return blueprint_path

    _cached_bp: blueprint.ExpandedBlueprint | None = None

    def get_expanded_blueprint(self) -> blueprint.ExpandedBlueprint:
        if self._cached_bp:
            return self._cached_bp

        path = self.get_blueprint_path()
        with blueprint.datafile(path, self.logger) as bp:
            expanded_bp = blueprint.ExpandedBlueprint.expand(bp, path, self.logger)

        self.logger.debug(str(expanded_bp))
        self._cached_bp = expanded_bp
        return expanded_bp

    def whatif_log(self, log: str):
        if self.whatif:
            self.logger.info(log)
        else:
            self.logger.debug(log)

    def package_manage_section(self, package_filter: Callable):
        bp = self.get_expanded_blueprint()
        if len(bp.packages) == 0:
            self.logger.warning(
                "no package managers in blueprint, skipping package management"
            )
            return

        manager_diffs: dict[str, package_managers.PackageDiff] = {}
        for manager_id, packages in bp.packages.items():
            manager = package_managers.get_manager(manager_id)
            diff = manager.get_package_diff(packages)
            self.logger.debug(f"(og) {manager_id}: {diff}")

            package_filter(manager_id, diff)
            self.whatif_log(f"{manager_id}: {diff}")
            if diff.is_empty():
                self.logger.warning(
                    f"no regex matches, skipping '{manager_id}' manager"
                )
                continue

            manager_diffs[manager_id] = diff

        # actually run it
        if not self.whatif:
            with TaskSection(
                "package management",
                bp,
                logger=self.logger,
                emote=emotes["section"],
            ) as section:
                for manager_id, diff in manager_diffs.items():
                    manager = package_managers.get_manager(manager_id)
                    task = ManagerTask("package_manager", manager_id)
                    task.run(section, manager.apply_changes, args=(diff,))

            # section summary
            package_tasks = completed_package_tasks(section.completed_tasks)
            if len(package_tasks) > 0:
                print_section_summary(package_tasks, self.logger)

    def package_config_section(self, package_filter: Callable):
        bp = self.get_expanded_blueprint()
        if len(bp.configs) == 0:
            self.logger.warning(
                "no config managers in blueprint, skipping config management"
            )
            return

        # config managers shouldn't care about package managers, so we just get a list of the package
        # names and give it to the config managers as a hint of what to config.
        packages = [
            p for manager_packages in bp.packages.values() for p in manager_packages
        ]
        packages = list(set(packages))
        packages = package_filter(packages)

        self.whatif_log(f"config managers: {list(bp.configs.keys())}")
        self.whatif_log(f"config packages: {packages}")
        if len(packages) == 0:
            self.logger.warning(
                "no packages are visible to config (hidden by filtering or failure); running config anyways"
            )

        # actually run it
        if not self.whatif:
            with TaskSection(
                "config management",
                bp,
                logger=self.logger,
                emote=emotes["section"],
            ) as section:
                for manager_id, config in bp.configs.items():
                    manager = config_managers.get_manager(manager_id)
                    task = ManagerTask("config_manager", manager_id)
                    task.run(section, manager.apply_config, args=(config, packages))

            # section summary
            package_tasks = completed_package_tasks(section.completed_tasks)
            if len(package_tasks) > 0:
                print_section_summary(package_tasks, self.logger)

    # command methods ------------------------------------------------------------------------------

    def sync_command(self):
        self.init_file_logging()

        # check core files first
        dotenv.datafile.check()
        self.get_expanded_blueprint()

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
            self.package_manage_section(package_filter)

        if self.config is not None:
            config_pattern = self.config
            package_filter = lambda packages: [
                p for p in packages if config_pattern.match(p)
            ]
            self.package_config_section(package_filter)

    def dotfiles_command(self):
        self.init_file_logging()

        dotfiles_path = self.path
        if not dotfiles_path:
            bp = self.get_expanded_blueprint()
            if bp.dotfiles:
                dotfiles_path = bp.dotfiles
        if not dotfiles_path:
            raise VulpixError("could not locate dotfiles; specify in blueprint or arg")
        dotfiles_path = Path(dotfiles_path)
        font_dir = dotfiles_path / "fonts"  # optional

        # get dotfiles
        self.logger.info(f"finding dotfiles at '{dotfiles_path}'")
        links = dotfiles.iter_dotfiles(
            dotfiles_path, ignore_paths=[font_dir], logger=self.logger
        )
        if len(links) == 0:
            self.logger.warning("no dotfiles found")

        # check existing link targets
        if not self.whatif:
            existing_targets = []
            for item, link in links:
                if link.exists():
                    try:
                        utils.rm_link(link)
                    except OSError, ValueError:
                        self.logger.debug("link already exists", exc_info=True)
                        existing_targets.append(link)
            if len(existing_targets) > 0:
                print()  # style
                self.logger.warning(
                    "the following items will be overwritting and replaced by links:"
                )
                print("\n".join(["  - " + str(t) for t in existing_targets]) + "\n")
                if not utils.verify("are you sure you want to continue?"):
                    raise VulpixError("dotfiles aborted")

                for target in existing_targets:
                    utils.rm_fr(target)
                print()  # style

        # link dotfiles
        _max_item_len = max(len(utils.pretty_path(l[0])) for l in links)
        for item, link in links:
            self.logger.info(utils.pretty_link_log(item, link, _max_item_len))
            if not self.whatif:
                utils.link(item, link, self.logger)

        # install fonts
        if font_dir.exists() and font_dir.is_dir():
            d = utils.pretty_path(font_dir)
            if self.whatif:
                self.logger.info(f"would install fonts from {d}")
            else:
                self.logger.info(f"installing fonts from {d}")
                dotfiles.install_fonts(font_dir, self.logger)

    def blueprint_command(self):
        self.init_file_logging()

        if self.edit:
            utils.open_in_editor(self.get_blueprint_path(), self.logger)
            return

        self.logger.warning("nothing to do")

    def dotenv_command(self):
        self.init_file_logging()

        if self.shell is None:
            dotenv.datafile.check()
            utils.open_in_editor(dotenv.path, self.logger)
            return

        self.logger.debug(f"converting '{dotenv.path}'")
        with dotenv.datafile as env:
            match self.shell:
                case "sh":
                    source = env.as_sh()
                case "pwsh":
                    source = env.as_pwsh()
                case _:
                    raise ValueError("invalid shell option")
        print(source)

    def replay_command(self):
        log_names = logging.get_log_file_names()
        if self.list:
            for name in log_names:
                print(name)
            return

        if len(log_names) == 0:
            self.logger.warning("no log files")
            return

        if self.log:
            log_names = [l for l in log_names if self.log.search(l)]
            if len(log_names) == 0:
                raise VulpixError("no log files matching regex")

        if len(log_names) == 1:
            log_name = log_names[0]
        else:
            log_name = utils.prompt_choice("select log", log_names)

        if not self.verbose:
            self.logger.warning("use --verbose to see debug logs")
        logging.console_log_to(sys.stdout, self.logger)  # temp log to stdout
        logging.replay_log_file(log_name, self.logger)
        logging.console_log_to(sys.stderr, self.logger)

    # main ----------------------------------------------------------------------------------------

    def main(self):
        self.logger.debug(str(self))
        match self.command:
            case "sync":
                command = self.sync_command
            case "dotfiles":
                command = self.dotfiles_command
            case "blueprint":
                command = self.blueprint_command
            case "dotenv":
                command = self.dotenv_command
            case "replay":
                command = self.replay_command
            case _:
                raise VulpixError("invalid command")
        command()
