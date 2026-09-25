from pathlib import Path

from vulpix.core import VulpixError, env, logging
from vulpix.package_managers.manual.packages import run_external_script, simple_shell_wrapper

WINDOWS_SCRIPT = str(Path(__file__).resolve().parent / "python.ps1")

def main(install_dir: str, logger: logging.Logger) -> list[str]:
    if env.OS != 'windows':
        logging.error("manual python install is not supported on linux (would have to build from source)")
        raise VulpixError("you should install python using your os package manager")

    return run_external_script(WINDOWS_SCRIPT, install_dir, logger=logger)

if __name__ == "__main__":
    simple_shell_wrapper(main)
