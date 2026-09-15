import sys
import logging
import argparse
import re
from pathlib import Path
from typing import Literal
from dataclasses import astuple

from vulpix import __version__, env, VulpixError, core
from vulpix.core import managers, tasks
from vulpix.core.blueprint import Blueprint
from vulpix.core.managers import PackageDiff

HELP = """usage: vulpix [opts] [actions]

If run as root, applies changes at system level, else only applies at user
level. This also effects where it looks for app dirs (like configuration).

options:

  -h, --help        print help
  -v, --version     print version tag
  -V, --verbose     print debug logs
  -b, --blueprint   specify blueprint yaml path, otherwise searches default
                    locations
  -w, --whatif      show what would happen without doing anything
  -e, --edit        opens config directory in $EDITOR or $VISUAL.

actions:

  --sync      [regex]   Syncs system/user with blueprint. If any packages are
                          in the blueprint but are not installed, they will be 
                          installed. If any blueprint packages are already
                          installed, they will be updated.

  --clean     [regex]     Cleans floating packages. If any packages are
                          installed but are not a package specified in blueprint
                          they will be uninstalled.

  --config    [regex]     Runs config scripts as specified in blueprint.

  --reinstall [regex]     Uninstalls then reinstalls specified packages (or all
                          packages if none specified). Prompts to add to
                          blueprint if specified packages isn't there.

  --replay    [phrase]    For replaying logs of tasks for seeing what went wrong/
                          right and debugging. Searches for logs with phrase as
                          substring and prompts which log to replay if there are
                          multiple.

  --dotfiles  [path]      Creates symlinks from stuff in dotfiles path
                          to all the correct locations. If <path> is not
                          supplied, uses the path in blueprint.yaml.
"""

def regex_arg(arg: str) -> re.Pattern[str]:
    try:
        return re.compile(arg)
    except re.error:
        raise argparse.ArgumentTypeError(f"'{arg}' is not a valid regular expression.")

def build_package_filter(sync: re.Pattern, clean: re.Pattern, reinstall: re.Pattern) -> Callable:
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

        # then clean and sync filters
        if clean is not None:
            changes.to_uninstall = filter_packages(changes.to_uninstall, clean)
        if sync is not None:
            changes.to_install = filter_packages(changes.to_install, sync)
            changes.to_update = filter_packages(changes.to_update, sync)

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

def package_config_section():
    pass

def dotfiles_section():
    pass

class Cli(argparse.Namespace):
    logger: Logger

    # settings options
    help: bool = False
    version: bool = False
    verbose: bool = False
    blueprint: str | None = None
    whatif: bool = False
    edit: bool = False

    # action options
    sync: str | None = None
    clean: str | None = None
    config: str | None = None
    reinstall: str | None = None
    dotfiles: str | None = None
    replay: str | None = None

    def __init__(self):
        parser = argparse.ArgumentParser(prog="vulpix", add_help=False)

        parser.add_argument("--help", "-h", action="store_true")
        parser.add_argument("--version", "-v", action="store_true")
        parser.add_argument("--verbose", "-V", action="store_true")
        parser.add_argument("--blueprint", "-b", type=str)
        parser.add_argument("--whatif", "-w", action="store_true")
        parser.add_argument("--edit", "-e", action="store_true")
        
        parser.add_argument("--sync", "-s", type=regex_arg, nargs='?', const='.*', default=None)
        parser.add_argument("--clean", "-x", type=regex_arg, nargs='?', const='.*', default=None)
        parser.add_argument("--reinstall", "-r", type=regex_arg, nargs='?', const='.*', default=None)
        parser.add_argument("--config", "-c", type=regex_arg, nargs='?', const='.*', default=None)
        parser.add_argument("--dotfiles", "-d", nargs='?', const='.*', default=None)
        parser.add_argument("--replay", type=regex_arg, nargs='?', const='.*', default=None)

        parser.parse_args(namespace=self)

    def edit_option(self, blueprint: Path):
        self.logger.info("edit")

    def replay_option(self, search_phrase: str):
        self.logger.info("replay")

    def main(self):
        if self.help:
            print(HELP)
            sys.exit(0)

        if self.version:
            print(__version__)
            sys.exit(0)

        self.logger.debug(str(self))

        blueprint_path = env.CONFIG / "blueprint.yaml"
        if self.blueprint is not None:
            blueprint_path = Path(self.blueprint)

        if not blueprint_path.exists():
            # TODO: ask if you wanna copy the default
            raise VulpixError(f"expected blueprint file at '{blueprint_path}'")

        if self.edit:
            self.edit_option(blueprint_path)
            sys.exit(0)

        if self.replay is not None:
            self.replay_option()
            sys.exit(0)

        from vulpix.blueprint import expand_blueprint
       
        _, blueprint = expand_blueprint(blueprint_path, self.logger)
        self.logger.debug(str(blueprint))

        # dotfiles section
        if self.dotfiles is not None:
            dotfiles_section()

        # package mangagement section
        if any(o is not None for o in [self.sync, self.clean, self.reinstall]):
            package_filter = build_package_filter(self.sync, self.clean, self.reinstall)
            package_manage_section(blueprint, package_filter, self.logger)

        # package configuration section
        if self.config is not None:
            package_config_section()
