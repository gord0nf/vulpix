import logging
import shutil
import sys

from vulpix import env

FILE_FORMATTER = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s")

def get_logger(log_name: str, log_file: bool = True) -> Logger:
    logger = logging.getLogger(log_name)
    logger.setLevel(logging.DEBUG)

    if log_file:
        file_handler = logging.FileHandler(env.LOG.joinpath(log_name + ".log"))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(FILE_FORMATTER)
        logger.addHandler(file_handler)

    return logger


def clear_logs():
    shutil.rmtree(env.LOG)

main = get_logger("main")
