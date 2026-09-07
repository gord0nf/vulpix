import sys
import logging

from vulpix import VulpixError, env
from vulpix.core.logging import main as logger
import vulpix.cli as cli

def main():
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
