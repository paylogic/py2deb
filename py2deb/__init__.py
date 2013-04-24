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

        # Fail dependencies
        if converter.config.has_option('general', 'preinstall'):
            fdep = converter.config.get('general', 'preinstall')
            converter._install_build_dep(fdep)

        sdists = get_source_dists(['install', '--ignore-installed', '-b', 
                                  builddir, '-r', requirements])
        print '\n\nFinished downloading/extracting all packages, starting conversion... \n'

        converter.packages.extend([Package(p[0], p[1], p[2]) for p in sdists])
        converter.convert()
    except Exception, e:
        sys.exit(e)
    finally:
        shutil.rmtree(builddir)
