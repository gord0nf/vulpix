"""
NOTE: this doesn't handle clearing env.LOG directory (that's the cli's job); logs are appended by
default.
"""

import re
from logging import *  # pyright: ignore[reportWildcardImportFromLibrary]

from vulpix.core import dirs

basicConfig(level=DEBUG, handlers=[])

FILE_FORMAT_ENCODE = "%(asctime)s %(threadName)s [%(levelname)s]: %(message)s"
FILE_FORMAT_DECODE = re.compile(r"^.*\[(?P<levelname>[a-zA-Z]+)\]:\s(?P<message>.*)$")
FILE_FORMATTER = Formatter(FILE_FORMAT_ENCODE)

level_by_name = getLevelNamesMapping()


def attach_log_file(logger: Logger) -> None:
    log_path = dirs.VULPIX_LOG.joinpath(logger.name + ".log")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = FileHandler(log_path, encoding="utf-16")
    file_handler.setLevel(DEBUG)
    file_handler.setFormatter(FILE_FORMATTER)
    logger.addHandler(file_handler)


def get_log_file_names() -> list[str]:
    return [
        str(p.relative_to(dirs.VULPIX_LOG).with_suffix(""))
        for p in dirs.VULPIX_LOG.rglob("*.log")
    ]


def replay_log_file(log_name: str, logger: Logger) -> None:
    log_path = dirs.VULPIX_LOG.joinpath(log_name + ".log")
    with open(log_path, "r", encoding="utf-16") as file:
        for line in file:
            match = FILE_FORMAT_DECODE.match(line.rstrip("\n"))
            if match and match.group("levelname") in level_by_name:
                log_level = level_by_name[match.group("levelname")]
                logger.log(log_level, match.group("message"))
