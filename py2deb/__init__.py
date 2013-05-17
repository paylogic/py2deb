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

from py2deb.util.converter import Converter

def main():

    # Command line option defaults (none :-).
    action = ''
    requirements = ''

    # Parse the command line options.
    options, arguments = getopt.getopt(sys.argv[1:], 'b:r:vh',
            ['build=', 'recall=', 'verbose', 'help'])

    # Print usage if no options are given.
    if not options:
        usage()
        return

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
        converter.convert()

        # Cleanup after ourselves.
        shutil.rmtree(converter.builddir)
    elif action == 'recall':
        print converter.recall_dependencies()

def usage():
    print __doc__.strip()
