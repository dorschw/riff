from sys import stderr

from loguru import logger  # noqa: TID251

logger.remove()
logger.add("riff.log")
logger.add(stderr, level="WARNING", format="{message}")
