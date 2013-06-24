"""
Usage: pl-py2deb [OPTIONS] -- PIP_ACCEL_ARGS [PIP_ACCEL_OPTIONS]

Supported options:

  -c, --config=FILE  override the default configuration file     
  -p, --print-deps   prints a valid value for the `Depends` line of a 
                     debian control file with the package names and
                     pinned versions of all built pacakges
  -v, --verbose      more output
  -y, --yes          automatically confirm installation of system-wide dependencies
  -h, --help         show this message and exit
"""

# Standard library modules
import getopt
import logging
import os
import shutil
import sys

# Internal modules
from py2deb.converter import convert
from py2deb.logger import logger

def main():
    # Command line option defaults
    config_file = None
    print_dependencies = False
    verbose = False
    auto_install = False

    # Parse command line options
    options, pip_args = getopt.gnu_getopt(sys.argv[1:], 'c:pvyh',
            ['config=', 'print-deps', 'verbose', 'yes', 'help'])

    if not pip_args:
        usage()
        return

    # Validate the command line options and map them to variables
    for option, value in options:
        if option in ('-c', '--config'):
            config_file = os.path.abspath(value)
            assert os.path.isfile(config_file), 'Invalid config file'
        elif option in ('-p', '--print-deps'):
            print_dependencies = True
        elif option in ('-v', '--verbose'):
            verbose = True
        elif option in ('-y', '--yes'):
            auto_install = True
        elif option in ('-h', '--help'):
            usage()
            return
        else:
            assert False, "Unrecognized option: %s" % option

    if verbose:
        logger.setLevel(logging.DEBUG)

    # Start converting
    converted = convert(pip_args, config_file=config_file, auto_install=auto_install,
                        verbose=verbose, cleanup=True)

    if print_dependencies:
        print ', '.join(converted)

def usage():
    print __doc__.strip()
