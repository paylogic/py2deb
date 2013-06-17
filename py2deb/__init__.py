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

import shutil
import sys
import os
import getopt

from py2deb.util.converter import Converter
from py2deb.config import config_dir

def main():
    # Command line option defaults
    config_file = os.path.join(config_dir, 'control.ini')
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

    converter = Converter(requirements, follow_dependencies)

    if action == 'build':

        converter.convert()

        # Cleanup after ourselves.
        shutil.rmtree(converter.builddir)

    elif action == 'recall':
        print converter.recall_dependencies()

def usage():
    print __doc__.strip()
