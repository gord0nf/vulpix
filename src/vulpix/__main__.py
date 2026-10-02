import sys

from vulpix.cli import Cli
from vulpix.core import env
from vulpix.utils import VulpixError


def main():
    cli = Cli()
    try:
        cli.main()
    except VulpixError as e:
        cli.logger.critical(e.message)
        sys.exit(e.exit_status)
    except Exception:
        cli.logger.debug("exception raised", exc_info=True)
        cli.logger.warning(f"see error details at '{env.LOG}'")
        cli.logger.critical("an unexpected, uncaught error occured")
        sys.exit(1)


if __name__ == "__main__":
    main()
