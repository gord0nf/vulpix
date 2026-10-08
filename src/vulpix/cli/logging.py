import sys
import threading
from dataclasses import dataclass
from json import JSONDecodeError
from typing import TextIO

from blessed import Terminal
from dacite import DaciteError

from vulpix.core import dirs
from vulpix.core.logging import *
from vulpix.utils import DataclassFile

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


# task status logs ------------------------------------------------


@dataclass
class TaskStatusLog:
    tasks: dict[str, bool]  # like {task_name: status}


def handle_taskstatus_error(_, exc_value: Exception):
    try:
        raise exc_value
    except JSONDecodeError, DaciteError:
        logger = getLogger("main")
        logger.debug("task status parse failed", exc_info=True)
        logger.warning("couldn't parse the status of task logs")


task_status_path = dirs.VULPIX_LOG / "tasks.json"
task_status_datafile = DataclassFile(
    task_status_path, dclass=TaskStatusLog, on_error=handle_taskstatus_error
)
