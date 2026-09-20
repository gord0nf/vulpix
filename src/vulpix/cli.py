import sys
import os
import logging
import argparse
import re
from pathlib import Path
from typing import Literal
from dataclasses import astuple
import subprocess

from vulpix import __version__, env, VulpixError, core
from vulpix.core import managers, tasks
from vulpix.core.blueprint import Blueprint
from vulpix.core.managers import PackageDiff

HELP = """usage: vulpix [opts] [command]

If run as root, applies changes at system level, else only applies at user
level. This also effects where it looks for app dirs (like configuration).

options:

  -h, --help                print help
  -v, --version             print version tag
  -V, --verbose             print debug logs
  -w, --whatif              show what would happen without doing anything
  -b, --blueprint           specify blueprint.yaml path, otherwise searches
                            default locations

commands:

  sync      [opts]      Syncs system/user with the blueprint. If no [opts]
                        are supplied, runs with `--clean --apply --config`.
  dotfiles  [path]      Creates symlinks from stuff in dotfiles path to all
                        the correct locations. If [path] is not supplied,
                        uses the path in the blueprint.
  blueprint [opts]      Edit the blueprint.
  replay    [regex]     Replay a log file (prompts if multiple matches).

sync command:

  sync -a, --apply     [regex]  If any packages are in the blueprint but are
                                not installed, they will be installed. If
                                any blueprint packages are already installed,
                                they will be updated.
  sync -x, --clean     [regex]  If any packages are installed but are not a
                                package specified in blueprint they will be
                                uninstalled.
  sync -c, --config    [regex]  Runs config scripts as specified in blueprint.
  sync -r, --reinstall <regex>  Uninstalls then reinstalls matching packages.

blueprint command:

  blueprint -e, --edit      Open in $VISUAL/$EDITOR.
"""

def regex_arg(arg: str) -> re.Pattern[str]:
    try:
        return re.compile(arg)
    except re.error:
        raise argparse.ArgumentTypeError(f"'{arg}' is not a valid regular expression.")

def parse_blueprint(path: Path, logger: logging.Logger) -> Blueprint:
    from vulpix.blueprint import expand_blueprint
   
    _, blueprint = expand_blueprint(path, logger)
    logger.debug(str(blueprint))
    return blueprint

def build_package_filter(
    apply: re.Pattern | None,
    clean: re.Pattern | None,
    reinstall: re.Pattern | None
) -> Callable:
    def filter_package_changes(manager: str, changes: PackageDiff):
        def filter_packages(packages: list[str], regex: re.Pattern, negate=False) -> list[str]:
            if negate:
                return [p for p in packages if not re.match(regex, f"{p}@{manager}")]
            return [p for p in packages if re.match(regex, f"{p}@{manager}")]

        # reinstall takes precedent (this is also different since we are telling it to reinstall
        # instead of install/update, rather than just filtering)
        if reinstall is not None:
            force_reinstall = filter_packages([*changes.to_install, *changes.to_update], reinstall)
            changes.to_install = filter_packages(changes.to_install, reinstall, negate=True)
            changes.to_update = filter_packages(changes.to_update, reinstall, negate=True)
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

def package_manage_section(blueprint: Blueprint, package_filter: Callable, logger: Logger):
    with tasks.ThreadedTaskQueue(blueprint.settings.threads, logger) as task_queue:
        for manager_id, packages in blueprint.packages.items():
            manager = managers.get_manager(manager_id)
            diff = manager.get_package_diff(packages)
            logger.debug(f"{manager_id}: {diff}")

            package_filter(manager_id, diff)
            logger.debug(f"filtered diff: {diff}")
            if not any(len(v) > 0 for v in astuple(diff)):
                logger.warning(f"no regex matches, skipping '{manager_id}' package management")
                continue

            task_queue.run_task(f"{manager_id} manager", manager.apply_changes, diff)

def package_config_section(pakage_filter: re.Pattern):
    pass

class Cli(argparse.Namespace):
    logger: Logger

    # generic options
    help: bool = False
    version: bool = False
    verbose: bool = False
    blueprint: str | None = None
    whatif: bool = False
    command: Literal["sync", "dotfiles", "blueprint"] | None = None

    # sync command
    apply: re.Pattern | None = None
    clean: re.Pattern | None = None
    config: re.Pattern | None = None
    reinstall: re.Pattern | None = None

    # dotfiles command
    path: str | None = None

    # blueprint command
    edit: bool = False

    # replay command
    log: re.Pattern | None = None

    def __init__(self):
        parser = argparse.ArgumentParser(prog="vulpix", add_help=False)
        parser.add_argument("--help", "-h", action="store_true")
        parser.add_argument("--version", "-v", action="store_true")
        parser.add_argument("--verbose", "-V", action="store_true")
        parser.add_argument("--blueprint", "-b", type=str)
        parser.add_argument("--whatif", "-w", action="store_true")

        subparsers = parser.add_subparsers(dest="command", required=False)

        # sync command
        sync_parser = subparsers.add_parser("sync")
        sync_parser.add_argument("--apply", "-a", type=regex_arg, nargs='?', const='.*', default=None)
        sync_parser.add_argument("--clean", "-x", type=regex_arg, nargs='?', const='.*', default=None)
        sync_parser.add_argument("--config", "-c", type=regex_arg, nargs='?', const='.*', default=None)
        sync_parser.add_argument("--reinstall", "-r", type=regex_arg)

        # dotfiles command
        dotfiles_parser = subparsers.add_parser("dotfiles")
        dotfiles_parser.add_argument("path", nargs="?", default=None)

        # blueprint command
        blueprint_parser = subparsers.add_parser("blueprint")
        blueprint_parser.add_argument("--edit", "-e", action="store_true")

        # replay command
        replay_parser = subparsers.add_parser("replay")
        replay_parser.add_argument("log", type=regex_arg, nargs='?', default='.*')

        parser.parse_args(namespace=self)

        if self.version:
            print(__version__)
            sys.exit(0)

        if self.help or self.command is None:
            print(HELP)
            sys.exit(0)

    def sync_command(self, blueprint_path: Path):
        blueprint = parse_blueprint(blueprint_path, self.logger)

        # no opts = --clean --apply --config
        if all(o is None for o in [self.apply, self.clean, self.config, self.reinstall]):
            self.clean = re.compile('.*')
            self.apply = re.compile('.*')
            self.config = re.compile('.*')

        if any(o is not None for o in [self.apply, self.clean, self.reinstall]):
            package_filter = build_package_filter(self.apply, self.clean, self.reinstall)
            package_manage_section(blueprint, package_filter, self.logger)

        if self.config is not None:
            package_config_section(self.config)

    def dotfiles_command(self, blueprint_path: Path):
        pass

    def blueprint_command(self, blueprint: Path):
        if self.edit:
            blueprint.parent.mkdir(parents=True, exist_ok=True)
            default_editor = 'notepad' if env.OS == 'windows' else 'nano'
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
