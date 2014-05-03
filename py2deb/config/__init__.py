# Standard library modules.
import ConfigParser
import os
import logging

# External dependencies.
from humanfriendly import format_path

# Initialize a logger for this module.
logger = logging.getLogger(__name__)

# Initialize the configuration parser.
config = ConfigParser.RawConfigParser()

def load_config(description, filename):
    """
    Load a py2deb configuration file.

    param filename: Filename of configuration file (a string).
    """
    if os.path.isfile(filename):
        logger.debug("Loading %s configuration file: %s", description, format_path(filename))
        config.read(filename)

# Load the configuration file bundled with py2deb.
load_config('bundled', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'py2deb.ini'))

# Load the configuration file(s) on the host system.
load_config('system wide', '/etc/py2deb.ini')
load_config('user', os.path.expanduser('~/.py2deb.ini'))
