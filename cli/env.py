import sys
import os
from os.path import expandvars
import platform
import logging
from pathlib import Path


def _fatal(*msg):
    logging.critical(*msg)
    raise SystemExit(1)


def _is_root():
    return os.geteuid() == 0


VERBOSE = False
TEST = False
BLUEPRINT_PATH = None

# system env vars ---------------------------------------------------------------------------------

if "OS" not in os.environ:
    match sys.platform:
        case "win32" | "cygwin" | "msys":
            os.environ["OS"] = "windows"
        case "linux" | "linux2":
            os.environ["OS"] = "linux"
        # TODO: support for android
        case _:
            _fatal("vulpix not supported on your os (override with OS env var)")
OS = os.environ["OS"]

if "ARCH" not in os.environ:
    match platform.machine():
        case "arm" | "armv7l" | "armv6l" | "armv5tel":
            os.environ["ARCH"] = "arm32"
        case "arm64" | "aarch64_be" | "aarch64" | "armv8b" | "armv8l":
            os.environ["ARCH"] = "arm64"
        case "x86" | "x32" | "i386" | "i686":
            os.environ["ARCH"] = "x32"
        case "x64" | "x86_64":
            os.environ["ARCH"] = "x64"
        case _:
            _fatal("arch not handled by devs (override with ARCH env var)")
ARCH = os.environ["ARCH"]


# check for windows env vars
if OS == "windows":
    for var in ["PROGRAMFILES" "ProgramData" "APPDATA" "LOCALAPPDATA" "TMP"]:
        if not os.getenv(var):
            _fatal("windows environmental var required: ", var)


# vulpix app vars ---------------------------------------------------------------------------------

if "VULPIX_INSTALL" not in os.environ:
    if "VULPIX" in os.environ:
        # cli requires $VULPIX as dir with vulpix source
        os.environ["VULPIX_INSTALL"] = os.environ["VULPIX"]
    else:
        if _is_root():
            if OS == "windows":
                os.environ["VULPIX_INSTALL"] = expandvars("$PROGRAMFILES/vulpix")
            else:
                os.environ["VULPIX_INSTALL"] = "/opt/vulpix"
        else:
            if OS == "windows":
                os.environ["VULPIX_INSTALL"] = expandvars(
                    "$LOCALAPPDATA/Programs/vulpix"
                )
            else:
                os.environ["VULPIX_INSTALL"] = expandvars("$HOME/.local/opt/vulpix")
INSTALL_PATH = Path(os.environ["VULPIX_INSTALL"])

if "VULPIX_DATA" not in os.environ:
    if _is_root():
        if OS == "windows":
            os.environ["VULPIX_DATA"] = expandvars("$ProgramData/vulpix")
        else:
            os.environ["VULPIX_DATA"] = "/var/lib/vulpix"
    else:
        if OS == "windows":
            os.environ["VULPIX_DATA"] = expandvars("$LOCALAPPDATA/vulpix")
        else:
            os.environ["VULPIX_DATA"] = expandvars("$HOME/.local/state/vulpix")
DATA_PATH = Path(os.environ["VULPIX_INSTALL"])


if "VULPIX_LOG" not in os.environ:
    if _is_root():
        if OS == "windows":
            os.environ["VULPIX_LOG"] = expandvars("$ProgramData/vulpix/log")
        else:
            os.environ["VULPIX_LOG"] = "/var/log/vulpix"
    else:
        if OS == "windows":
            os.environ["VULPIX_LOG"] = expandvars("$LOCALAPPDATA/vulpix/log")
        else:
            os.environ["VULPIX_LOG"] = expandvars("$HOME/.local/state/vulpix/log")
LOG_PATH = Path(os.environ["VULPIX_LOG"])

if "VULPIX_CONFIG" not in os.environ:
    if _is_root():
        if OS == "windows":
            os.environ["VULPIX_CONFIG"] = expandvars("$ProgramData/vulpix/config")
        else:
            os.environ["VULPIX_CONFIG"] = "/etc/vulpix"
    else:
        if OS == "windows":
            os.environ["VULPIX_CONFIG"] = expandvars("$APPDATA/Roaming/vulpix")
        else:
            os.environ["VULPIX_CONFIG"] = expandvars("$HOME/.config/vulpix")
CONFIG_PATH = Path(os.environ["VULPIX_CONFIG"])

if "VULPIX_TMP" not in os.environ:
    if "TMP" in os.environ:
        os.environ["VULPIX_TMP"] = expandvars("$TMP/vulpix")
    else:
        os.environ["VULPIX_TMP"] = "/tmp/vulpix"
TMP_PATH = Path(os.environ["VULPIX_TMP"])

if "FONT_INSTALL" not in os.environ:
    if OS == "windows":
        pass  # TODO
    elif _is_root():
        os.environ["FONT_INSTALL"] = "/usr/share/fonts"
    else:
        os.environ["FONT_INSTALL"] = expandvars("$HOME/.local/share/fonts")
FONT_INSTALL = Path(os.environ["FONT_INSTALL"])
