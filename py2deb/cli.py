# Command line interface for the `py2deb' program.
#
# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: May 22, 2017
# URL: https://py2deb.readthedocs.io

"""
Usage: py2deb [OPTIONS] ...

Convert Python packages to Debian packages according to the given
command line options (see below). The command line arguments are the
same as accepted by the `pip install' command because py2deb invokes
pip during the conversion process. This means you can name the
package(s) to convert on the command line but you can also use
`requirement files' if you prefer.

If you want to pass command line options to pip (e.g. because you want
to use a custom index URL or a requirements file) then you will need
to tell py2deb where the options for py2deb stop and the options for
pip begin. In such cases you can use the following syntax:

  $ py2deb -r /tmp -- -r requirements.txt

So the `--' marker separates the py2deb options from the pip options.

Supported options:

  -c, --config=FILENAME

    Load a configuration file. Because the command line arguments are processed
    in the given order, you have the choice and responsibility to decide if
    command line options override configuration file options or vice versa.
    Refer to the documentation for details on the configuration file format.

    The default configuration files /etc/py2deb.ini and ~/.py2deb.ini are
    automatically loaded if they exist. This happens before environment
    variables and command line options are processed.

    Can also be set using the environment variable $PY2DEB_CONFIG.

  -r, --repository=DIRECTORY

    Change the directory where *.deb archives are stored. Defaults to
    the system wide temporary directory (which is usually /tmp). If
    this directory doesn't exist py2deb refuses to run.

    Can also be set using the environment variable $PY2DEB_REPOSITORY.

  --use-system-package=PYTHON_PACKAGE_NAME,DEBIAN_PACKAGE_NAME

    Exclude a Python package (the name before the comma) from conversion and
    replace references to the Python package with a specific Debian package
    name. This allows you to use system packages for specific Python
    requirements.

  --name-prefix=PREFIX

    Set the name prefix used during the name conversion from Python to
    Debian packages. Defaults to `python'. The name prefix and package
    names are always delimited by a dash.

    Can also be set using the environment variable $PY2DEB_NAME_PREFIX.

  --no-name-prefix=PYTHON_PACKAGE_NAME

    Exclude a Python package from having the name prefix applied
    during the package name conversion. This is useful to avoid
    awkward repetitions.

  --rename=PYTHON_PACKAGE_NAME,DEBIAN_PACKAGE_NAME

    Override the package name conversion algorithm for the given pair
    of package names. Useful if you don't agree with the algorithm :-)

  --install-prefix=DIRECTORY

    Override the default system wide installation prefix. By setting
    this to anything other than `/usr' or `/usr/local' you change the
    way py2deb works. It will build packages with a file system layout
    similar to a Python virtual environment, except there will not be
    a Python executable: The packages are meant to be loaded by
    modifying Python's module search path. Refer to the documentation
    for details.

    Can also be set using the environment variable $PY2DEB_INSTALL_PREFIX.

  --install-alternative=LINK,PATH

    Use Debian's `update-alternatives' system to add an executable
    that's installed in a custom installation prefix (see above) to
    the system wide executable search path. Refer to the documentation
    for details.

  --python-callback=EXPRESSION

    Set a Python callback to be called during the conversion process. Refer to
    the documentation for details about the use of this feature and the syntax
    of EXPRESSION.

    Can also be set using the environment variable $PY2DEB_CALLBACK.

  --report-dependencies=FILENAME

    Add the Debian relationships needed to depend on the converted
    package(s) to the given control file. If the control file already
    contains relationships the additional relationships will be added
    to the control file; they won't overwrite existing relationships.

  -y, --yes

    Instruct pip-accel to automatically install build time dependencies
    where possible. Refer to the pip-accel documentation for details.

    Can also be set using the environment variable $PY2DEB_AUTO_INSTALL.

  -v, --verbose

    Make more noise :-).

  -h, --help

    Show this message and exit.
"""

# Standard library modules.
import getopt
import logging
import os
import sys

# External dependencies.
import coloredlogs
from deb_pkg_tools.control import patch_control_file
from humanfriendly.terminal import usage, warning

# Modules included in our package.
from py2deb.converter import PackageConverter

# Initialize a logger.
logger = logging.getLogger(__name__)


def main():
    """Command line interface for the ``py2deb`` program."""
    # Configure terminal output.
    coloredlogs.install()
    try:
        # Initialize a package converter.
        converter = PackageConverter()
        # Parse and validate the command line options.
        options, arguments = getopt.getopt(sys.argv[1:], 'c:r:yvh', [
            'config=', 'repository=', 'use-system-package=', 'name-prefix=',
            'no-name-prefix=', 'rename=', 'install-prefix=',
            'install-alternative=', 'python-callback=', 'report-dependencies=',
            'yes', 'verbose', 'help',
        ])
        control_file_to_update = None
        for option, value in options:
            if option in ('-c', '--config'):
                converter.load_configuration_file(value)
            elif option in ('-r', '--repository'):
                converter.set_repository(value)
            elif option == '--use-system-package':
                python_package_name, _, debian_package_name = value.partition(',')
                converter.use_system_package(python_package_name, debian_package_name)
            elif option == '--name-prefix':
                converter.set_name_prefix(value)
            elif option == '--no-name-prefix':
                converter.rename_package(value, value)
            elif option == '--rename':
                python_package_name, _, debian_package_name = value.partition(',')
                converter.rename_package(python_package_name, debian_package_name)
            elif option == '--install-prefix':
                converter.set_install_prefix(value)
            elif option == '--install-alternative':
                link, _, path = value.partition(',')
                converter.install_alternative(link, path)
            elif option == '--python-callback':
                converter.set_python_callback(value)
            elif option == '--report-dependencies':
                control_file_to_update = value
                if not os.path.isfile(control_file_to_update):
                    msg = "The given control file doesn't exist! (%s)"
                    raise Exception(msg % control_file_to_update)
            elif option in ('-y', '--yes'):
                converter.set_auto_install(True)
            elif option in ('-v', '--verbose'):
                coloredlogs.increase_verbosity()
            elif option in ('-h', '--help'):
                usage(__doc__)
                return
            else:
                assert False, "Unhandled option!"
    except Exception as e:
        warning("Failed to parse command line arguments: %s", e)
        sys.exit(1)
    # Convert the requested package(s).
    try:
        if arguments:
            archives, relationships = converter.convert(arguments)
            if relationships and control_file_to_update:
                patch_control_file(control_file_to_update, dict(depends=relationships))
        else:
            usage(__doc__)
    except Exception:
        logger.exception("Caught an unhandled exception!")
        sys.exit(1)
