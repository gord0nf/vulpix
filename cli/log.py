import logging
import shutil
import sys

import env
import shell


class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: shell.Colors.PURPLE,
        logging.INFO: shell.Colors.BLUE,
        logging.WARNING: shell.Colors.YELLOW,
        logging.ERROR: shell.Colors.RED,
        logging.CRITICAL: shell.Colors.BOLD + shell.Colors.RED,
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelno, shell.Colors.RESET)
        record.levelname = f"{log_color}{record.levelname}{shell.Colors.RESET}"
        return super().format(record)


CONSOLE_FORMATTER = ColoredFormatter("%(levelname)s> %(message)s")
FILE_FORMATTER = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")


def get_logger(log_name: str, log_file: bool = True) -> logging.Logger:
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG if env.VERBOSE else logging.INFO)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(CONSOLE_FORMATTER)
    logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(env.LOG_PATH.joinpath(log_name + ".log"))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(FILE_FORMATTER)
        logger.addHandler(file_handler)

    return logger


def clear_logs():
    shutil.rmtree(env.LOG_PATH)


# MAIN CONTEXT LOGGER
main = get_logger("main")


class FatalCliError(SystemExit):
    """For when you want to exit cleanly from cli (versus just saying 'an error occured')"""

    def __init__(self, message: str):
        main.critical(message)
        super().__init__(1)
