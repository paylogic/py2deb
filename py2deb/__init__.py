"""
Usage: py2deb [OPTIONS] -- PIP_INSTALL_ARGS

Supported options:

  -c, --config=FILE     set the user configuration file
  -r, --repo=DIR        override the default repository directory
  -p, --prefix=STR      set package name prefix (defaults to `python-')
  -P, --print-deps      prints a valid value for the `Depends` line of a Debian
                        control file with the package names and pinned versions
                        of all built packages
  -s, --with-stdeb      use the stdeb backend to build the Debian package
  -p, --with-pip-accel  use the pip-accel backend to build the Debian package
  -v, --verbose         make more noise (can be repeated)
  -y, --yes             automatically install missing system packages
  -h, --help            show this message and exit
"""

# Semi-standard module versioning.
__version__ = '0.8.7'

# Standard library modules.
import getopt
import os
import sys

# External dependency.
import coloredlogs

# Modules included in our package.
from py2deb.backends.pip_accel_backend import build as build_with_pip_accel
from py2deb.backends.stdeb_backend import build as build_with_stdeb
from py2deb.config import config, load_config
from py2deb.converter import convert

def main():

    # Initialize logging to the terminal.
    coloredlogs.install()

    # Command line option defaults
    backend = build_with_stdeb
    config_file = None
    repository = None
    name_prefix = None
    print_dependencies = False
    verbose = False
    auto_install = False

    # Parse command line options
    options, arguments = getopt.gnu_getopt(sys.argv[1:], 'c:r:p:Pspyvh',
            ['config=', 'repo=', 'prefix=', 'print-deps', 'with-stdeb', 'with-pip-accel', 'verbose', 'yes', 'help'])

    if not arguments:
        usage()
        return

    # Validate the command line options and map them to variables
    for option, value in options:
        if option in ('-c', '--config'):
            config_file = os.path.abspath(value)
            if not os.path.isfile(config_file):
                msg = "Configuration file doesn't exist! (%s)"
                raise Exception, msg % config_file
        elif option in ('-r', '--repo'):
            repository = os.path.abspath(value)
            if not os.path.isdir(repository):
                msg = "Repository directory doesn't exist! (%s)"
                raise Exception, msg % repository
        elif option in ('-p', '--prefix'):
            name_prefix = value
        elif option in ('-P', '--print-deps'):
            print_dependencies = True
        elif option in ('-s', '--with-stdeb'):
            backend = build_with_stdeb
        elif option in ('-p', '--with-pip-accel'):
            backend = build_with_pip_accel
        elif option in ('-y', '--yes'):
            auto_install = True
        elif option in ('-v', '--verbose'):
            coloredlogs.increase_verbosity()
            verbose = True
        elif option in ('-h', '--help'):
            usage()
            return
        else:
            msg = "Unrecognized option: %s"
            raise Exception, msg % option

    # Initialize the configuration.
    if config_file:
        load_config(config_file)
    if name_prefix:
        config.set('general', 'name-prefix', name_prefix)

    # Start the conversion.
    converted = convert(arguments,
                        backend=backend,
                        repository=repository,
                        auto_install=auto_install,
                        verbose=verbose)

    if print_dependencies:
        print ', '.join(converted)

def usage():
    print __doc__.strip()
