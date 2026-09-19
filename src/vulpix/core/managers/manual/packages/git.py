from logging import Logger
from pathlib import Path

from vulpix import env, VulpixError
import vulpix.core.managers.manual.package_utils as putils

SCRIPT_DIR = Path(__file__).resolve().parent
WINDOWS_SCRIPT = SCRIPT_DIR / "git.ps1"

def main(install_dir: Path, logger: Logger) -> list[Path]:
    if env.OS != 'windows':
        logging.error("manual python install is not supported on linux (would have to build from source)")
        raise VulpixError("you should install python using your os package manager")

    cmd = ['powershell', str(WINDOWS_SCRIPT), str(install_dir)]
    binaries = putils.run_external_script(cmd, logger)
    return [Path(b) for b in binaries]

if __name__ == "__main__":
    putils.simple_shell_wrapper(main)
