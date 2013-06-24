# Standard library module.
import logging

# External dependency.
import coloredlogs

logger = logging.getLogger('py2deb')
logger.setLevel(logging.INFO)
logger.addHandler(coloredlogs.ColoredStreamHandler())