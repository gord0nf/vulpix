import shutil
import sys
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
 
def get_logger(log_name: str, verbose: bool = False, log_file: bool = True) -> Logger:
    logger = getLogger(log_name)
    logger.verbose = verbose
    logger.setLevel(DEBUG)

    if log_file:
        file_handler = FileHandler(env.LOG.joinpath(log_name + ".log"))
        file_handler.setLevel(DEBUG)
        file_handler.setFormatter(FILE_FORMATTER)
        logger.addHandler(file_handler)

    console_handler = StreamHandler(sys.stderr)
    console_handler.setFormatter(CONSOLE_FORMATTER)
    console_handler.setLevel(DEBUG if verbose else INFO)
    logger.addHandler(console_handler)

    return logger
