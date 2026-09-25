"""
NOTE: this doesn't handle clearing env.LOG directory (that's the cli's job); logs are appended by
default.
"""

from logging import *

from vulpix.core import env

basicConfig(level=DEBUG, handlers=[])

FILE_FORMATTER = Formatter("%(asctime)s %(threadName)s [%(levelname)s]: %(message)s")

def attach_log_file(logger: Logger) -> None:
    log_path = env.LOG.joinpath(logger.name + ".log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = FileHandler(log_path, encoding="utf-16")
    file_handler.setLevel(DEBUG)
    file_handler.setFormatter(FILE_FORMATTER)
    logger.addHandler(file_handler)
