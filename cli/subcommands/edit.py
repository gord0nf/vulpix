import os

import env
from log import FatalCliError, main as logger


def main(*args):
    if len(args) > 0:
        logger.warning("ignoring subcommand args...")

    editor = os.getenv("VISUAL", os.getenv("EDITOR"))
    if not editor:
        raise FatalCliError("couldn't get editor; please define VISUAL or EDITOR")

    logger.debug(f"editor: {editor}")
    env.CONFIG_PATH.mkdir(parents=True, exist_ok=True)
    os.chdir(env.CONFIG_PATH)
    os.execvp(editor, [editor, "blueprint.yaml"])
