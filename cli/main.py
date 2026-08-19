import sys
import logging
import argparse

import env

VERSION = "v1.1"
HELP = """usage: vulpix [opts] [subcommand]

If run as root, applies changes at system level, else only applies at user
level. This also effects where it looks for app dirs (like configuration).

options:

  -h, --help        print help
  -v, --version     print version tag
  -V, --verbose     print debug logs
  -b, --blueprint   specify blueprint yaml path, otherwise searches default
                    locations

subcommands:

  [none]    ...packages   Syncs system/user with blueprint. Equivalent of running
                          'clean', then 'install ...packages', then 'config
                          ...packages' subcommands, where ...packages are the
                          packages passed as args. If no packages are passed,
                          execution is the same, but the '--all' arg is appended
                          to the 'config' cmd.

  clean                   Cleans floating packages. If any packages are
                          installed but are not a package specified in blueprint
                          they will be uninstalled.

  install   ...packages   Syncs *installation* of packages with blueprint. If
                          any packages in the blueprint or args are not
                          installed, they will be installed. If a package passed
                          as an arg is not in the blueprint, it will prompt and
                          require the package to be added to the blueprint
                          before continuing. If any packages are passed,
                          installation sync will only occur for the specified
                          packages, else the entire blueprint is synced.

  config    ...packages|all Syncs *config* of packages with blueprint. It
                            always runs the global config. If any packages are
                          passed as args, it runs the config corresponding to
                          those packages. If 'all' is passed, all packages'
                          configs are ran.

  reinstall ...packages    Uninstalls then reinstalls specified packages (or all
                          packages if none specified). Prompts to add to
                          blueprint if specified packages isn't there.

  replay    <phrase>      For replaying logs of tasks for seeing what went wrong/
                          right and debugging. Searches for logs with phrase as
                          substring and prompts which log to replay if there are
                          multiple.

  dotfiles  <path>        Creates symlinks from stuff in dotfiles path
                          to all the correct locations. If <path> is not
                          supplied, uses the path in blueprint.yaml.

  edit                    Opens config directory in $EDITOR or $VISUAL.

  bootstrap               Updates vulpix and reruns bootstrap script. Use if you
                          1) want to update vulpix, or 2) broke something.

NOTE: ...packages are passed like package_name@manager (example: neovim@manual)."""


class ProgramArgs(argparse.Namespace):
    help: bool = False
    version: bool = False
    test: bool = False
    verbose: bool = False
    blueprint: str
    subcommand: str
    subcommand_args: list[str]


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--version", "-v", action="store_true")
    parser.add_argument("--verbose", "-V", action="store_true")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--blueprint", "-b", type=str)
    parser.add_argument("subcommand", type=str, nargs="?")
    parser.add_argument("subcommand_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(namespace=ProgramArgs())
    return args


def main():
    args = parse_args()

    if args.help:
        print(HELP)
        sys.exit(0)
    if args.version:
        print(VERSION)
        sys.exit(0)

    if args.verbose:
        env.VERBOSE = True
    if args.test:
        env.TEST = True
    if args.blueprint is not None:
        env.BLUEPRINT_PATH = args.blueprint

    # init main logger with env defined above
    from log import main as logger

    logger.debug(args)

    try:
        import subcommands

        subcommands.run_subcommand(args.subcommand, args.subcommand_args)
    except Exception:
        if logger.level == logging.DEBUG:
            logger.exception("exception raised")
        logger.warning(f"see error details at '{env.LOG_PATH}'")
        logger.critical("an unexpected, uncaught error occured")
        logging.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    main()
