import logging
import shutil
import sys

import env

CONSOLE_FORMATTER = logging.Formatter("%(message)s")
FILE_FORMATTER = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")


# https://stackoverflow.com/a/48201163
class ExitOnExceptionHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        if record.levelno == logging.CRITICAL:
            raise SystemExit(1)


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
