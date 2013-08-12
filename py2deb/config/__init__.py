# Standard library modules.
import ConfigParser
import os
import logging

# External dependencies.
from humanfriendly import format_path

# Initialize the logger.
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Initialize the configuration parser.
config = ConfigParser.RawConfigParser()

# Load the bundled configuration.
bundled_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'py2deb.ini')
logger.debug("Loading bundled configuration: %s", format_path(bundled_config_file))
config.read(bundled_config_file)

def load_config(filename):
    """
    Load the py2deb configuration file.

    param filename: Filename of user configuration file (a string).
    :returns: A :py:class:`ConfigParser.RawConfigParser` object.
    """
    # Load the configuration bundled with py2deb.
    # Load the configuration provided by the user?
    filename = os.path.abspath(filename)
    logger.debug("Loading user configuration: %s", format_path(filename))
    config.read(filename)
