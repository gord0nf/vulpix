import sys
import shutil
import threading
from blessed import Terminal

from vulpix.core.logging import *

term = Terminal()
term_lock = threading.RLock()

class ColoredLogFormatter(Formatter):
    COLORS = {
        DEBUG: term.purple,
        INFO: term.blue,
        WARNING: term.yellow,
        ERROR: term.red,
        CRITICAL: term.bold_red
    }
    def format(self, record):
        log_color = self.COLORS.get(record.levelno, None)
        if log_color:
            record.levelname = log_color(record.levelname)
        return super().format(record)

def attach_console_logging(logger: Logger, verbose: bool, prefix: tuple[str, str] = ("", "")):
    handler = StreamHandler(sys.stderr)
    formatter = ColoredLogFormatter(f"{prefix[0]}%(levelname)s>{prefix[1]} %(message)s")
    handler.setFormatter(formatter)
    handler.setLevel(DEBUG if verbose else INFO)
    handler.lock = term_lock
    
    logger.addHandler(handler)

# main is an exception because it represents per run logs that need to be cleared every run, no
# matter what the cli wants to do (e.g. replaying logs)
MAIN_LOG_FILE = env.LOG / "main.log"
MAIN_LOG_FILE.unlink(missing_ok=True)

def clear_logs():
    """this skips root level files (like main.log) because those should be handled manually"""
    for item in env.LOG.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
