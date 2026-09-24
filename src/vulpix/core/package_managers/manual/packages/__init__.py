import sys
import types
import logging
import subprocess
import importlib
import importlib.util
from typing import Callable

from vulpix.core import VulpixError

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
    print("\n".join(bin_paths)) # return line seperated list for shell

def run_external_script(script: str, *args: list[str], logger: logging.Logger) -> list[str]:
    cmd = [script, *args]
    if script.endswith(".ps1"):
        cmd.insert(0, "powershell")

    logger.debug(f"running external {cmd}")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in process.stderr:
        logger.info(line.strip())
    stdout, _ = process.communicate()
    if process.returncode != 0:
        raise VulpixError("external script failed")

    if stdout:
        return stdout.splitlines()
    return []
