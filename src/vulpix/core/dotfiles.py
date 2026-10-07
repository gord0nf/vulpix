"""utils for symlinking a dotfiles repo to system"""

import shutil
import winreg
from pathlib import Path

from vulpix.core import dirs, logging, system
from vulpix.utils import LoggedCommand, command_exists

font_patterns = ["*.ttf", "*.otf", "*.ttc", "*.fon"]


def install_fonts(font_dir: Path, logger: logging.Logger):
    dirs.FONT_INSTALL.mkdir(parents=True, exist_ok=True)

    font_files = [p for g in font_patterns for p in font_dir.rglob(g)]
    if len(font_files) == 0:
        logger.warning("no font files in directory")
        return
    for f in font_files:
        logger.debug(f"copying {f}")
        try:
            shutil.copy2(f, dirs.FONT_INSTALL)
        except FileExistsError, PermissionError:
            logger.debug("copy failed, continuing", exc_info=True)

    match system.OS:
        case "windows":
            reg_key = (
                winreg.HKEY_LOCAL_MACHINE
                if system.IS_ROOT
                else winreg.HKEY_CURRENT_USER
            )
            reg_path = r"Software\Microsoft\Windows NT\CurrentVersion\Fonts"
            logger.debug(f"populating {reg_key} {reg_path}")
            with winreg.OpenKey(reg_key, reg_path, 0, winreg.KEY_WRITE) as key:
                for f in font_files:
                    path = dirs.FONT_INSTALL / f.name
                    winreg.SetValueEx(key, f.stem, 0, winreg.REG_SZ, str(path))

        case "linux":
            for p in dirs.FONT_INSTALL.rglob("*"):
                p.chmod(0o755 if p.is_dir() else 0o644)
            if command_exists("fc-cache"):
                LoggedCommand("fc-cache", logger=logger).run()


type LinkPair = tuple[Path, Path]


def iter_dotfiles(
    dotfiles_dir: Path, ignore_paths: list[Path], logger: logging.Logger
) -> list[LinkPair]:
    # get ignored paths
    ignore_file = dotfiles_dir / ".vulpixignore"
    ignore_paths.append(ignore_file)
    if ignore_file.exists():
        with open(ignore_file, "r") as file:
            lines = [l.strip() for l in file]
            ignore_paths.extend(
                [dotfiles_dir / l.strip() for l in lines if l and l[0] != "#"]
            )
    logger.debug(f"ignoring: {ignore_paths}")

    dotfiles: list[LinkPair] = []

    for item in dotfiles_dir.glob("*"):
        if any(i.samefile(item) for i in ignore_paths):
            continue

        if item.is_dir():
            match item.name:
                case ".config":
                    for tool in item.glob("*"):
                        if not tool.is_dir() or any(
                            i.samefile(tool) for i in ignore_paths
                        ):
                            continue
                        dotfiles.append((tool, dirs.config(tool.name)))
                    continue

        dotfiles.append((item, Path.home() / item.name))

    return dotfiles
