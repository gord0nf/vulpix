"""defines constants for application directories"""

import os
from os.path import expandvars
from pathlib import Path
from typing import Final

from vulpix.core import system


def default_data():
    if system.IS_ROOT:
        if system.OS == "windows":
            return expandvars("$ProgramData/vulpix")
        else:
            return "/var/lib/vulpix"
    else:
        if system.OS == "windows":
            return expandvars("$LOCALAPPDATA/vulpix")
        else:
            return expandvars("$HOME/.local/state/vulpix")


def default_log():
    if system.IS_ROOT:
        if system.OS == "windows":
            return expandvars("$ProgramData/vulpix/log")
        else:
            return "/var/log/vulpix"
    else:
        if system.OS == "windows":
            return expandvars("$LOCALAPPDATA/vulpix/log")
        else:
            return expandvars("$HOME/.local/state/vulpix/log")


def default_config():
    if system.IS_ROOT:
        if system.OS == "windows":
            return expandvars("$ProgramData/vulpix/config")
        else:
            return "/etc/vulpix"
    else:
        if system.OS == "windows":
            return expandvars("$APPDATA/vulpix")
        else:
            return expandvars("$HOME/.config/vulpix")


def default_tmp():
    if "TMP" in os.environ:
        return expandvars("$TMP/vulpix")
    elif "TEMP" in os.environ:
        return expandvars("$TEMP/vulpix")
    else:
        return "/tmp/vulpix"


DATA: Final[Path] = Path(os.getenv("VULPIX_DATA") or default_data())
LOG: Final[Path] = Path(os.getenv("VULPIX_LOG") or default_log())
CONFIG: Final[Path] = Path(os.getenv("VULPIX_CONFIG") or default_config())
TMP: Final[Path] = Path(os.getenv("VULPIX_TMP") or default_tmp())
