import sys
import threading
from typing import TextIO

from blessed import Terminal

from vulpix.core import dirs
from vulpix.core.logging import *

term = Terminal()
term_lock = threading.RLock()

LOG_COLORS = {
    DEBUG: term.purple,
    INFO: term.blue,
    WARNING: term.yellow,
    ERROR: term.red,
    CRITICAL: term.bold_red,
}


class ColoredLogFormatter(Formatter):
    def format(self, record):
        log_color = LOG_COLORS.get(record.levelno, None)
        if log_color:
            record.levelname = log_color(record.levelname)
        return super().format(record)


def attach_console_logging(
    logger: Logger, verbose: bool, prefix: tuple[str, str] = ("", "")
):
    handler = StreamHandler(sys.stderr)
    formatter = ColoredLogFormatter(f"{prefix[0]}%(levelname)s>{prefix[1]} %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(DEBUG if verbose else INFO)
    handler.lock = term_lock  # pyright: ignore # needs to be an RLock, idk why it wants Lock...

    logger.addHandler(handler)


_console_streams = [sys.stderr, sys.stdout]


def console_log_to(stream: TextIO, logger: Logger):
    for handler in logger.handlers:
        if isinstance(handler, StreamHandler) and handler.stream in _console_streams:
            handler.stream = stream


def clear_logs():
    for p in dirs.VULPIX_LOG.rglob("*.log"):
        p.unlink()
