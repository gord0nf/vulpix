import sys
import logging
import argparse
from pathlib import Path

from vulpix import __version__, env, VulpixError, core

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

    def __init__(self, logger: Logger):
        self.logger = logger
        parser = argparse.ArgumentParser(prog="vulpix", add_help=False)

        parser.add_argument("--help", "-h", action="store_true")
        parser.add_argument("--version", "-v", action="store_true")
        parser.add_argument("--verbose", "-V", action="store_true")
        parser.add_argument("--blueprint", "-b", type=str)
        parser.add_argument("--whatif", "-w", action="store_true")
        parser.add_argument("--edit", "-e", action="store_true")
        
        parser.add_argument("--sync", "-s", nargs='?', const='.*', default=None)
        parser.add_argument("--clean", "-x", nargs='?', const='.*', default=None)
        parser.add_argument("--config", "-c", nargs='?', const='.*', default=None)
        parser.add_argument("--reinstall", "-r", nargs='?', const='.*', default=None)
        parser.add_argument("--dotfiles", "-d", nargs='?', const='.*', default=None)
        parser.add_argument("--replay", nargs='?', const='.*', default=None)

        parser.parse_args(namespace=self)

    def edit_option(self, blueprint: Path):
        self.logger.info("edit")

    def replay_option(self):
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

        core.apply(blueprint, self.logger)
