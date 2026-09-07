import sys
import logging

from vulpix.core.logging import main as logger

console_handler = logging.StreamHandler(sys.stderr)
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

def main():
    logger.info("cli main")
