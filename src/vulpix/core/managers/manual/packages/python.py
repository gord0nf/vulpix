import sys
import logging
import subprocess
from pathlib import Path

from vulpix import env, VulpixError
from vulpix.core.managers.manual import utils

SCRIPT_DIR = Path(__file__).resolve().parent
WINDOWS_SCRIPT = SCRIPT_DIR / "python.ps1"
UNIX_SCRIPT = SCRIPT_DIR / "python.sh"

def main(install_dir: Path, logger: logging.Logger) -> list[Path]:
    if env.OS == 'windows':
        cmd = ['powershell', str(WINDOWS_SCRIPT)]
    else:
        cmd = ['bash', str(UNIX_SCRIPT)]
    cmd.append(str(install_dir))
    logger.debug(f"running {cmd}")

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for line in process.stderr:
        logger.info(line.strip())
    stdout, _ = process.communicate()
    if process.returncode != 0:
        raise VulpixError("python@manual script failed")

    binaries = []
    if stdout:
        binaries = [Path(line.strip()) for line in stdout if line.strip()]
    return binaries

if __name__ == "__main__":
    logger = logging.getLogger("main")
    if len(sys.argv) != 2:
        logger.critical("expected exactly 1 arg, no more no less good sir!")
        sys.exit(1)
    bin_paths = main(Path(sys.argv[1]), logger)
    print("\n".join([str(p) for p in bin_paths])) # return line seperated list for shell
