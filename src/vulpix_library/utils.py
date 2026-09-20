import sys
import logging
import subprocess
from typing import Callable

from vulpix import VulpixError

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
