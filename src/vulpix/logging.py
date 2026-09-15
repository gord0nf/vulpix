import logging
import shutil
import sys

from vulpix import env
from vulpix.utils import Colors

class ColoredLogFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Colors.PURPLE,
        logging.INFO: Colors.BLUE,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BOLD + Colors.RED,
    }
    def format(self, record):
        log_color = self.COLORS.get(record.levelno, Colors.RESET)
        record.levelname = f"{log_color}{record.levelname}{Colors.RESET}"
        return super().format(record)

FILE_FORMATTER = logging.Formatter("%(asctime)s %(threadName)s [%(levelname)s]: %(message)s")
CONSOLE_FORMATTER = ColoredLogFormatter("%(levelname)s> %(message)s")
 
def get_logger(log_name: str, verbose: bool = False, log_file: bool = True) -> Logger:
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)

    if log_file:
        file_handler = logging.FileHandler(env.LOG.joinpath(log_name + ".log"))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(FILE_FORMATTER)
        logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(CONSOLE_FORMATTER)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(console_handler)

    return logger
