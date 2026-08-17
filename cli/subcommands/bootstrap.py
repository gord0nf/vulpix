import os

import env
from log import main as logger


def main(*args):
    if len(args) > 0:
        logger.warning("ignoring subcommand args...")

    script = env.INSTALL_PATH / "bootstrap.sh"
    logger.info("running bootstrap script")
    logger.debug(f"bootstrap script: {script}")
    os.execvp("bash", ["bash", script])
