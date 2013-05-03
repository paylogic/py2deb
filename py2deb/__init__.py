"""
Usage: pl-py2deb OPTIONS

Supported options:

  -b, --build=FILE   build Debian packages for all requirements in the given
                     requirements.txt file (as accepted by pip)
  -r, --recall=FILE  recall the Debian package names of previously converted
                     packages based on a requirements.txt file
  -h, --help         show this message and exit
"""

import shutil
import sys
import os
import getopt

from py2deb.util.plpip_extract import get_source_dists
from py2deb.util.converter import Converter
from py2deb.util.package import Package

def main():

    # Command line option defaults (none :-).
    action = ''
    requirements = ''

    # Parse the command line options.
    options, arguments = getopt.getopt(sys.argv[1:], 'b:r:vh',
            ['build=', 'recall=', 'verbose', 'help'])

    # Map the command line options to variables and validate the arguments.
    for option, value in options:
        if option in ('-b', '--build'):
            action = 'build'
            requirements = os.path.abspath(value)
            assert os.path.isfile(requirements), "Requirements file does not exist!"
        elif option in ('-r', '--recall'):
            action = 'recall'
            requirements = os.path.abspath(value)
            assert os.path.isfile(requirements), "Requirements file does not exist!"
        elif option in ('-h', '--help'):
            usage()
            return
        else:
            assert False, "Unhandled option!"

        converter = Converter(requirements)

    if action == 'build':
        # Install global build dependencies and any dependencies needed to
        # evaluate setup.py scripts like the one from MySQL-python which
        # requires libmysqlclient before setup.py works.
        if converter.config.has_section('preinstall'):
            dependencies = []
            for name, value in converter.config.items('preinstall'):
                dependencies.extend(value.split())
            converter._install_build_dep(*dependencies)

        sdists = get_source_dists(['install', '--ignore-installed', '-b', 
                                  converter.builddir, '-r', requirements])
        print '\n\nFinished downloading/extracting all packages, starting conversion... \n'

        # Remove packages if they're in the ignore list.
        sdists = [p for p in sdists if not converter.config.has_option('ignore', p[0].lower())]

        converter.packages.extend([Package(p[0], p[1], p[2]) for p in sdists])
        converter.convert()

        # Cleanup after ourselves.
        shutil.rmtree(converter.builddir)
    elif action == 'recall':
        print converter.recall_dependencies()

def usage():
    print __doc__.strip()
