import sys
import logging

from vulpix import VulpixError, env
from vulpix.core.logging import main as logger
from vulpix.utils import Colors
from vulpix.cli import Cli

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

def init_console_logging(logger, verbose: bool):
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(ColoredLogFormatter("%(levelname)s> %(message)s"))
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(console_handler)

def main():
    cli = Cli(logger)
    init_console_logging(logger, cli.verbose)

    try:
        cli.main()
    except VulpixError as e:
        logger.critical(e.message)
        sys.exit(e.exit_status)
    except Exception as e:
        if logger.level == logging.DEBUG:
            logger.exception("exception raised")
        logger.warning(f"see error details at '{env.LOG}'")
        logger.critical("an unexpected, uncaught error occured")
        sys.exit(1)

if __name__ == "__main__":
    main()
