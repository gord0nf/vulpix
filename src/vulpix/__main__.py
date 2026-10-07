import sys

from vulpix.cli import parse_cli
from vulpix.core import dirs
from vulpix.utils import VulpixError


def main():
    cli = parse_cli()
    cli.init_console_logging()
    try:
        cli.main()
    except VulpixError as e:
        cli.logger.critical(e.message)
        sys.exit(e.exit_status)
    except Exception:
        cli.logger.debug("exception raised", exc_info=True)
        cli.logger.warning(f"see error details at '{dirs.VULPIX_LOG}'")
        cli.logger.critical("an unexpected, uncaught error occured")
        sys.exit(1)


if __name__ == "__main__":
    main()
