# Bootstrap script for py2deb.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: October 12, 2013
# URL: https://github.com/paylogic/py2deb
#
# This Python module implements the `py2deb --install' command. It converts
# py2deb and its dependencies to Debian packages and installs these packages on
# the local system. By creating a Python virtual environment, installing py2deb
# in that environment and executing `py2deb --install' one can bootstrap an
# installation of py2deb managed using Debian packages.

# Standard library modules.
import logging
import shutil
import tempfile

# External dependencies.
from humanfriendly import concatenate
from deb_pkg_tools import debian_package_dependencies as deb_pkg_tools_dependencies
from deb_pkg_tools.utils import execute
from deb_pkg_tools.repo import activate_repository, deactivate_repository, update_repository
from py2deb import convert, debian_package_dependencies as py2deb_dependencies

# Initialize a logger for this module.
logger = logging.getLogger(__name__)

def install():
    # Make sure stdeb is not installed.
    logger.info("Making sure python-stdeb is not installed (py2deb contains a fork of stdeb).")
    execute('apt-get', 'purge', '--yes', 'python-stdeb', sudo=True, logger=logger)
    # Install Debian package dependencies of py2deb and deb-pkg-tools.
    dependencies = set(py2deb_dependencies) | set(deb_pkg_tools_dependencies)
    logger.info("Installing prerequisites (%s) ..",
                concatenate(sorted(dependencies)))
    execute('apt-get', 'install', '--yes', *sorted(dependencies), sudo=True, logger=logger)
    # Initialize the apt-file cache.
    logger.info("Initializing apt-file cache ..")
    execute('apt-file', 'update', sudo=True, logger=logger)
    # Prepare a temporary directory tree to hold the generated packages.
    directory = tempfile.mkdtemp()
    try:
        # Use py2deb to convert itself and its dependencies to Debian packages.
        logger.info("Converting py2deb and dependencies to Debian packages ..")
        convert(['py2deb'], repository=directory)
        # Convert the directory of packages to a repository.
        update_repository(directory)
        # Make it possible to install packages from the repository.
        activate_repository(directory)
        try:
            # Try to install the generated packages from the repository.
            logger.info("Installing py2deb using Debian packages ..")
            execute('apt-get', 'install', 'python-py2deb', sudo=True, logger=logger)
        finally:
            # Always deactivate the temporary repository after use.
            deactivate_repository(directory)
    finally:
        # Always cleanup the temporary directory tree.
        shutil.rmtree(directory)
