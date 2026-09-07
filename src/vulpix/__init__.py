__title__ = "vulpix"
__description__ = "Config-driven system manager regarding package management and configuration."
__version__ = "v1.1"

from typing import Final, Literal
import os
from os.path import expandvars
import sys
import platform
from pathlib import Path

class VulpixError(Exception):
    message: str
    exit_status: int

    def __init__(self, message: str, exit_status: int = 1):
        self.message = message
        self.exit_status = exit_status

class VulpixEnvironment:
    OS: Final[Literal["windows", "linux"]]
    ARCH: Final[Literal["arm32", "arm64", "x32", "x64"]]
    IS_ROOT: Final[bool]

    INSTALL: Final[Path]
    DATA: Final[Path]
    LOG: Final[Path]
    CONFIG: Final[Path]
    TMP: Final[Path]

    def __init__(self):
        match os.getenv("OS", sys.platform).lower():
            case "windows_nt" | "win32" | "cygwin" | "msys":
                self.OS = "windows"
            case "linux" | "linux2":
                self.OS = "linux"
            # TODO: support for android
            case _:
                raise VulpixError("vulpix not supported on your os (override with OS env var)")

        match os.getenv("ARCH", platform.machine()).lower():
            case "arm" | "armv7l" | "armv6l" | "armv5tel":
                self.ARCH = "arm32"
            case "arm64" | "aarch64_be" | "aarch64" | "armv8b" | "armv8l":
                self.ARCH = "arm64"
            case "x86" | "x32" | "i386" | "i686":
                self.ARCH = "x32"
            case "x64" | "x86_64" | "amd" | "amd64":
                self.ARCH = "x64"
            case _:
                raise VulpixError("arch not handled by devs (override with ARCH env var)")

        # required windows env vars
        if self.OS == "windows":
            for required_env in ["PROGRAMFILES", "ProgramData", "APPDATA", "LOCALAPPDATA", "TMP"]:
                if not os.getenv(required_env):
                    raise VulpixError(f"windows environmental var required: {required_env}")

        # check root
        try:
            if self.OS == 'windows':
                import ctypes
                self.IS_ROOT = bool(ctypes.windll.shell32.IsUserAnAdmin())
            self.IS_ROOT = os.geteuid() == 0
        except AttributeError:
            self.IS_ROOT = False

        self.INSTALL = Path(os.getenv("VULPIX_INSTALL", os.getenv("VULPIX")) or self.default_install())
        self.DATA = Path(os.getenv("VULPIX_DATA") or self.default_data())
        self.LOG = Path(os.getenv("VULPIX_LOG") or self.default_log())
        self.CONFIG = Path(os.getenv("VULPIX_CONFIG") or self.default_config())
        self.TMP = Path(os.getenv("VULPIX_TMP") or self.default_tmp())

    def default_install(self):
        if self.IS_ROOT:
            return expandvars("$PROGRAMFILES/vulpix") if self.OS == "windows" else "/opt/vulpix"
        else:
            if self.OS == "windows":
                return expandvars("$LOCALAPPDATA/Programs/vulpix")
            else:
                return expandvars("$HOME/.local/opt/vulpix")

    def default_data(self):
        if self.IS_ROOT:
            if self.OS == "windows":
                return expandvars("$ProgramData/vulpix")
            else:
                return "/var/lib/vulpix"
        else:
            if self.OS == "windows":
                return expandvars("$LOCALAPPDATA/vulpix")
            else:
                return expandvars("$HOME/.local/state/vulpix")

    def default_log(self):
        if self.IS_ROOT:
            if self.OS == "windows":
                return expandvars("$ProgramData/vulpix/log")
            else:
                return "/var/log/vulpix"
        else:
            if self.OS == "windows":
                return expandvars("$LOCALAPPDATA/vulpix/log")
            else:
                return expandvars("$HOME/.local/state/vulpix/log")

    def default_config(self):
        if self.IS_ROOT:
            if self.OS == "windows":
                return expandvars("$ProgramData/vulpix/config")
            else:
                return "/etc/vulpix"
        else:
            if self.OS == "windows":
                return expandvars("$APPDATA/Roaming/vulpix")
            else:
                return expandvars("$HOME/.config/vulpix")

    def default_tmp(self):
        if "TMP" in os.environ:
            return expandvars("$TMP/vulpix")
        elif "TEMP" in os.environ:
            return expandvars("$TEMP/vulpix")
        else:
            return "/tmp/vulpix"

env = VulpixEnvironment()
