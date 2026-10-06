"""defines constants for application directories"""

import os
from pathlib import Path
from typing import Final

from vulpix.core import system


def data(app: str) -> Path:
    if system.IS_ROOT:
        if system.OS == "windows":
            return Path(os.environ["ProgramData"]) / app
        else:
            return Path("/var/lib/") / app
    else:
        if system.OS == "windows":
            return Path(os.environ["LOCALAPPDATA"]) / app
        else:
            return Path.home() / ".local/state" / app


def log(app: str) -> Path:
    if system.IS_ROOT:
        if system.OS == "windows":
            return Path(os.environ["ProgramData"]) / app / "log"
        else:
            return Path("/var/log") / app
    else:
        if system.OS == "windows":
            return Path(os.environ["LOCALAPPDATA"]) / app / "log"
        else:
            return Path.home() / ".local/state" / app / "log"


def config(app: str) -> Path:
    if system.IS_ROOT:
        if system.OS == "windows":
            return Path(os.environ["ProgramData"]) / app / "config"
        else:
            return Path("/etc") / app
    else:
        if system.OS == "windows":
            return Path(os.environ["APPDATA"]) / app
        else:
            return Path.home() / ".config" / app


def tmp(app: str) -> Path:
    tmp = os.getenv("TMP") or os.getenv("TEMP") or "/tmp"
    return Path(tmp) / app


VULPIX_DATA: Final[Path] = Path(os.getenv("VULPIX_DATA") or data("vulpix"))
VULPIX_LOG: Final[Path] = Path(os.getenv("VULPIX_LOG") or log("vulpix"))
VULPIX_CONFIG: Final[Path] = Path(os.getenv("VULPIX_CONFIG") or config("vulpix"))
VULPIX_TMP: Final[Path] = Path(os.getenv("VULPIX_TMP") or tmp("vulpix"))
