import os
import sys
import platform
from pathlib import Path
from os.path import expandvars
from typing import Final, Literal

from vulpix.core import VulpixError


ARCH: Final[Literal["arm32", "arm64", "x32", "x64"]]
match os.getenv("ARCH", platform.machine()).lower():
    case "arm" | "armv7l" | "armv6l" | "armv5tel":
        ARCH = "arm32"
    case "arm64" | "aarch64_be" | "aarch64" | "armv8b" | "armv8l":
        ARCH = "arm64"
    case "x86" | "x32" | "i386" | "i686":
        ARCH = "x32"
    case "x64" | "x86_64" | "amd" | "amd64":
        ARCH = "x64"
    case _:
        raise VulpixError("arch not handled by devs (override with ARCH env var)")


OS: Final[Literal["windows", "linux"]]
match os.getenv("OS", sys.platform).lower():
    case "linux" | "linux2":
        OS = "linux"

    # TODO: support for android

    case "windows_nt" | "win32" | "cygwin" | "msys":
        OS = "windows"

        # check required windows env vars
        for required_env in ["PROGRAMFILES", "ProgramData", "APPDATA", "LOCALAPPDATA", "TMP"]:
            if not os.getenv(required_env):
                raise VulpixError(f"windows environmental var required: {required_env}")

    case _:
        raise VulpixError("vulpix not supported on your os (override with OS env var)")


IS_ROOT: Final[bool]
try:
    if OS == 'windows':
        import ctypes
        IS_ROOT = bool(ctypes.windll.shell32.IsUserAnAdmin())
    IS_ROOT = os.geteuid() == 0
except AttributeError:
    IS_ROOT = False


def default_install():
    if IS_ROOT:
        return expandvars("$PROGRAMFILES/vulpix") if OS == "windows" else "/opt/vulpix"
    else:
        if OS == "windows":
            return expandvars("$LOCALAPPDATA/Programs/vulpix")
        else:
            return expandvars("$HOME/.local/opt/vulpix")

def default_data():
    if IS_ROOT:
        if OS == "windows":
            return expandvars("$ProgramData/vulpix")
        else:
            return "/var/lib/vulpix"
    else:
        if OS == "windows":
            return expandvars("$LOCALAPPDATA/vulpix")
        else:
            return expandvars("$HOME/.local/state/vulpix")

def default_log():
    if IS_ROOT:
        if OS == "windows":
            return expandvars("$ProgramData/vulpix/log")
        else:
            return "/var/log/vulpix"
    else:
        if OS == "windows":
            return expandvars("$LOCALAPPDATA/vulpix/log")
        else:
            return expandvars("$HOME/.local/state/vulpix/log")

def default_config():
    if IS_ROOT:
        if OS == "windows":
            return expandvars("$ProgramData/vulpix/config")
        else:
            return "/etc/vulpix"
    else:
        if OS == "windows":
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


INSTALL: Final[Path] = Path(os.getenv("VULPIX_INSTALL", os.getenv("VULPIX")) or default_install())
DATA: Final[Path] = Path(os.getenv("VULPIX_DATA") or default_data())
LOG: Final[Path] = Path(os.getenv("VULPIX_LOG") or default_log())
CONFIG: Final[Path] = Path(os.getenv("VULPIX_CONFIG") or default_config())
TMP: Final[Path] = Path(os.getenv("VULPIX_TMP") or default_tmp())
