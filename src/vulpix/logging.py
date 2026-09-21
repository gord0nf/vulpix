import sys
import shutil
import threading

from logging import *

from vulpix import env
from vulpix.utils import Colors

class ColoredLogFormatter(Formatter):
    COLORS = {
        DEBUG: Colors.PURPLE,
        INFO: Colors.BLUE,
        WARNING: Colors.YELLOW,
        ERROR: Colors.RED,
        CRITICAL: Colors.BOLD + Colors.RED,
    }
    def format(self, record):
        log_color = self.COLORS.get(record.levelno, Colors.RESET)
        record.levelname = f"{log_color}{record.levelname}{Colors.RESET}"
        return super().format(record)

FILE_FORMATTER = Formatter("%(asctime)s %(threadName)s [%(levelname)s]: %(message)s")
CONSOLE_FORMATTER = ColoredLogFormatter("%(levelname)s> %(message)s")

console_lock = threading.RLock()
 
def get_logger(log_name: str, verbose: bool = False, log_file: bool = True) -> Logger:
    logger = getLogger(log_name)
    logger.setLevel(DEBUG)

    if log_file:
        log_path = env.LOG.joinpath(log_name + ".log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = FileHandler(log_path, encoding="utf-16")
        file_handler.setLevel(DEBUG)
        file_handler.setFormatter(FILE_FORMATTER)
        logger.addHandler(file_handler)

    console_handler = StreamHandler(sys.stderr)
    console_handler.setFormatter(CONSOLE_FORMATTER)
    console_handler.setLevel(DEBUG if verbose else INFO)
    console_handler.lock = console_lock
    logger.addHandler(console_handler)

    return logger

def _is_console_handler(handler: Handler) -> bool:
    return isinstance(handler, StreamHandler) and handler.stream == sys.stderr

def logger_is_verbose(logger: Logger) -> bool:
    for handler in logger.handlers:
        if _is_console_handler(handler) and handler.level <= DEBUG:
            return True
    return False

def hide_logger(logger: Logger):
    for handler in logger.handlers:
        if _is_console_handler(handler):
            logger.removeHandler(handler)

def console_log_prefix(logger: Logger, prefix: str):
    for handler in logger.handlers:
        if _is_console_handler(handler) and handler.formatter:
            old_fmt = handler.formatter._fmt
            handler.setFormatter(ColoredLogFormatter(prefix + old_fmt))

# main is an exception because it represents per run logs that need to be cleared every run, no
# matter what cli.py wants to do (e.g. replaying logs)
MAIN_LOG_FILE = env.LOG / "main.log"
MAIN_LOG_FILE.unlink(missing_ok=True)

def clear_logs():
    for item in env.LOG.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
