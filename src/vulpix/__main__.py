import sys

from vulpix import VulpixError, env
from vulpix.logging import get_logger
from vulpix.cli import Cli

def main():
    cli = Cli()
    cli.logger = get_logger("main", verbose=cli.verbose)

    try:
        cli.main()
    except VulpixError as e:
        cli.logger.critical(e.message)
        sys.exit(e.exit_status)
    except Exception as e:
        if cli.verbose:
            cli.logger.exception("exception raised")
        else:
            cli.logger.warning(f"see error details at '{env.LOG}'")
        cli.logger.critical("an unexpected, uncaught error occured")
        sys.exit(1)

if __name__ == "__main__":
    main()
