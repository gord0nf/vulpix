import argparse
import re

from vulpix import __version__
from vulpix.cli import core
from vulpix.cli.task_section import emotes


def regex_arg(arg: str) -> re.Pattern[str]:
    try:
        return re.compile(arg)
    except re.error:
        raise argparse.ArgumentTypeError(f"'{arg}' is not a valid regular expression.")


def parse_cli() -> core.Cli:
    parser = argparse.ArgumentParser(
        prog="vulpix",
        description="blueprint-driven system management/configuration tool "
        f"[ {emotes['cool_dude']} ]",
        usage="%(prog)s [OPTIONS] <COMMAND>",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
        help="print version tag",
    )
    parser.add_argument("-V", "--verbose", action="store_true", help="print debug logs")
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
    dotfiles_desc = "symlinks dotfiles to system locations."
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

    # dotenv command
    dotenv_desc = "source vulpix dotenv in your shell."
    dotenv_parser = subparsers.add_parser(
        "dotenv",
        help=dotenv_desc,
        description='use like `eval "$(vulpix dotenv sh)"` or '
        "`vulpix dotenv pwsh | Invoke-Expression` in your profile.\n\n"
        "do not specify <shell> to open dotenv json in $VISUAL/$EDITOR.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    dotenv_parser.add_argument("shell", choices=["sh", "pwsh"], nargs="?")

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
    replay_parser.add_argument(
        "-l", "--list", action="store_true", help="list available logs."
    )

    # actaually parse it! -----------------------------------------
    cli = core.Cli()
    parser.parse_args(namespace=cli)
    if not cli.command:
        parser.exit(status=1, message=parser.format_help())

    return cli
