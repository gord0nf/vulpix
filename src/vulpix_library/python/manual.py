from pathlib import Path

from vulpix import env, VulpixError
from vulpix.logging import Logger
from vulpix_library import utils

WINDOWS_SCRIPT = str(Path(__file__).resolve().parent / "manual.ps1")

def main(install_dir: str, logger: Logger) -> list[str]:
    if env.OS != 'windows':
        logging.error("manual python install is not supported on linux (would have to build from source)")
        raise VulpixError("you should install python using your os package manager")

    return utils.run_external_script(WINDOWS_SCRIPT, install_dir, logger=logger)

if __name__ == "__main__":
    utils.simple_shell_wrapper(main)
