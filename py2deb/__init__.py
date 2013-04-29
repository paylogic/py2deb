import tempfile
import shutil
import sys
import os

from py2deb.util.plpip_extract import get_source_dists
from py2deb.util.converter import Converter
from py2deb.util.package import Package

def main():
    if len(sys.argv) != 2:
        raise Exception('Invalid argument(s): Expecting one text file.')
    
    requirements = os.path.abspath(sys.argv[1])

    if not os.path.isfile(requirements):
        raise Exception('Error: %s is not a file.' % requirements)

    builddir = tempfile.mkdtemp(prefix='py2deb_')
    
    try:
        converter = Converter(builddir)

        # Install global build dependencies and any dependencies needed to
        # evaluate setup.py scripts like the one from MySQL-python which
        # requires libmysqlclient before setup.py works.
        if converter.config.has_section('preinstall'):
            dependencies = []
            for name, value in converter.config.items('preinstall'):
                dependencies.extend(value.split())
            converter._install_build_dep(*dependencies)

        sdists = get_source_dists(['install', '--ignore-installed', '-b', 
                                  builddir, '-r', requirements])
        print '\n\nFinished downloading/extracting all packages, starting conversion... \n'

        converter.packages.extend([Package(p[0], p[1], p[2]) for p in sdists])
        converter.convert()

        # Cleanup after ourselves.
        shutil.rmtree(builddir)
    except Exception, e:
        sys.exit(e)

