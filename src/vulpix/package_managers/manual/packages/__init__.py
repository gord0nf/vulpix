import importlib
import importlib.util
import sys
import types
from collections.abc import Callable

from vulpix.utils import logging, run_cmd

# package interface -------------------------------------------------------------------------------


def check_package(package: str) -> bool:
    return importlib.util.find_spec(f"{__name__}.{package}") is not None


def get_package(package: str) -> types.ModuleType | None:
    try:
        module = importlib.import_module(f".{package}", package=__name__)
    except ModuleNotFoundError:
        return None
    return module


# utils for package scripts -----------------------------------------------------------------------


def simple_shell_wrapper(main: Callable[[str, logging.Logger], list[str]]):
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("main")
    if len(sys.argv) != 2:
        logger.critical("expected exactly 1 arg, no more no less good sir!")
        sys.exit(1)
    bin_paths = main(sys.argv[1], logger)
    print("\n".join(bin_paths))  # return line seperated list for shell


def run_external_script(script: str, *args: str, logger: logging.Logger) -> list[str]:
    cmd = [script, *args]
    if script.endswith(".ps1"):
        cmd.insert(0, "powershell")

    stdout = run_cmd(*cmd, logger=logger, return_stdout=True)
    return stdout or []
