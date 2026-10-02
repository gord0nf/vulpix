"""defines constants about the current system/user"""

import os
import platform
import sys
from typing import Final, Literal

from vulpix.core import VulpixError

type Os = Literal["windows", "linux"]  # macos not supported
type Arch = Literal["arm32", "arm64", "x32", "x64"]


def get_arch() -> Arch:
    match os.getenv("ARCH", platform.machine()).lower():
        case "arm" | "armv7l" | "armv6l" | "armv5tel":
            return "arm32"
        case "arm64" | "aarch64_be" | "aarch64" | "armv8b" | "armv8l":
            return "arm64"
        case "x86" | "x32" | "i386" | "i686":
            return "x32"
        case "x64" | "x86_64" | "amd" | "amd64":
            return "x64"
        case _:
            raise VulpixError("arch not handled by devs (override with ARCH env var)")


def get_os() -> Os:
    match os.getenv("OS", sys.platform).lower():
        case "linux" | "linux2":
            return "linux"

        # TODO: support for android

        case "windows_nt" | "win32" | "cygwin" | "msys":
            # check required windows env vars
            for required_env in [
                "PROGRAMFILES",
                "ProgramData",
                "APPDATA",
                "LOCALAPPDATA",
                "TMP",
            ]:
                if not os.getenv(required_env):
                    raise VulpixError(
                        f"windows environmental var required: {required_env}"
                    )

            return "windows"

        case _:
            raise VulpixError(
                "vulpix not supported on your os (override with OS env var)"
            )


def check_root() -> bool:
    try:
        if OS == "windows":
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except AttributeError:
        return False


ARCH: Final[Arch] = get_arch()
OS: Final[Os] = get_os()
IS_ROOT: Final[bool] = check_root()
