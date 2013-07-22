# Standard library modules.
import ConfigParser
import os
import logging

# External dependencies.
from humanfriendly import format_path

# Initialize the logger.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def load_config(filename=None):
    """
    Load the py2deb configuration file.

    param filename: Filename of user configuration file (a string, optional).
    :returns: A :py:class:`ConfigParser.RawConfigParser` object.
    """
    config = ConfigParser.RawConfigParser()
    # Load the configuration bundled with py2deb.
    directory = os.path.dirname(os.path.abspath(__file__))
    bundled = os.path.join(directory, 'py2deb.ini')
    logger.debug("Loading bundled configuration: %s", format_path(bundled))
    config.read(bundled)
    # Load the configuration provided by the user?
    if filename:
        logger.debug("Loading user configuration: %s", format_path(filename))
        config.read(filename)
    return config
