"""
Usage: py2deb [OPTIONS] -- PIP_INSTALL_ARGS

Supported options:

  -c, --config=FILE          set the user configuration file
  -r, --repository=DIR       override the default repository directory
      --name-prefix=STR      set package name prefix (default: python)
      --install-prefix=PATH  set installation prefix path (default: none)
      --report-deps=PATH     generates a valid value for the `Depends` line of
                             a Debian control file with the package names and
                             pinned versions of built (transitive) packages and
                             saves it to the given file
      --with-stdeb           use stdeb backend to build Debian package(s)
      --with-pip-accel       use pip-accel backend to build Debian package(s)
      --install              install py2deb using Debian packages
                             (bootstrapping)
  -y, --yes                  automatically install missing system packages
  -v, --verbose              make more noise (can be repeated)
  -h, --help                 show this message and exit
"""

# Standard library modules.
import getopt
import logging
import os
import sys
import textwrap

# External dependencies.
import coloredlogs

# Modules included in our package.
from py2deb.backends.pip_accel_backend import build as build_with_pip_accel
from py2deb.backends.stdeb_backend import build as build_with_stdeb
from py2deb.config import config, load_config
from py2deb.converter import convert

# Semi-standard module versioning.
__version__ = '0.13.6'

# Initialize a logger for this module.
logger = logging.getLogger()

# The following non-essential Debian packages need to be installed in order for
# py2deb to work properly. Please note that this list does not include the
# dependencies of deb-pkg-tools!
#
# TODO Document why we need these!
debian_package_dependencies = (
    'apt-file',             # Required by stdeb to figure out dependencies on system packages.
    'build-essential',      # Required by stdeb to compile binary packages.
    'debhelper',            # Required by stdeb to build packages.
    'dpkg-dev',             # Required by py2deb to build packages (specifically the program dpkg-buildpackage).
    'python-all',           # Required by py2deb to determine which version of stdeb to use.
    'python-pkg-resources', # Required by py2deb (the Python module pkg_resources).
    'python-setuptools',    # Required by stdeb to build packages.
    'python-support',       # Required by stdeb to avoid "dpkg-checkbuilddeps: Unmet build dependencies: python-support".
)

def main():

    # Initialize logging to the terminal.
    coloredlogs.install()

    # Command line option defaults
    backend = build_with_stdeb
    config_file = None
    repository = None
    name_prefix = None
    install_prefix = None
    report_dependencies = None
    verbose = False
    auto_install = False
    do_install = False

    # Parse command line options
    options, arguments = getopt.gnu_getopt(sys.argv[1:], 'c:r:yvh',
            ['install', 'config=', 'repository=', 'name-prefix=', 'install-prefix=', 'report-deps=', 'with-stdeb', 'with-pip-accel', 'yes', 'verbose', 'help'])

    # Validate the command line options and map them to variables
    for option, value in options:
        if option == '--install':
            do_install = True
        elif option in ('-c', '--config'):
            config_file = os.path.abspath(value)
            if not os.path.isfile(config_file):
                msg = "Configuration file doesn't exist! (%s)"
                raise Exception, msg % config_file
        elif option in ('-r', '--repository'):
            repository = os.path.abspath(value)
            if not os.path.isdir(repository):
                msg = "Repository directory doesn't exist! (%s)"
                raise Exception, msg % repository
        elif option == '--name-prefix':
            name_prefix = value
        elif option == '--install-prefix':
            install_prefix = value
        elif option == '--report-deps':
            report_dependencies = value
        elif option == '--with-stdeb':
            backend = build_with_stdeb
        elif option == '--with-pip-accel':
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
    if install_prefix:
        config.set('general', 'install-prefix', install_prefix)

    if not (do_install or arguments):
        usage()
        return

    if do_install:
        import py2deb.bootstrap
        py2deb.bootstrap.install()

    if arguments:
        converted_dependencies = convert(arguments,
                                         backend=backend,
                                         repository=repository,
                                         auto_install=auto_install,
                                         verbose=verbose)
        if report_dependencies:
            logger.debug("Converted dependencies to be reported: %s", converted_dependencies)
            if os.path.isfile(report_dependencies):
                with open(report_dependencies) as handle:
                    existing_dependencies = [d.strip() for d in handle.read().split(',') if d and not d.isspace()]
                    logger.debug("Read existing dependencies from %s: %s", report_dependencies, existing_dependencies)
                    converted_dependencies = existing_dependencies + converted_dependencies
            logger.debug("Writing dependencies to %s: %s", report_dependencies, converted_dependencies)
            with open(report_dependencies, 'w') as handle:
                handle.write("%s\n" % ", ".join(converted_dependencies))

def usage():
    print __doc__.strip()

def generate_stdeb_cfg():
    print textwrap.dedent('''
        # The py2deb package bundles two copies of stdeb and installs its own
        # top level stdeb module. We explicitly make the python-py2deb package
        # conflict with the python-stdeb package so that the two are not
        # installed together.
        [py2deb]
        Depends: {depends}
        Conflicts: python-stdeb
        Replaces: python-stdeb
    '''.format(depends=', '.join(debian_package_dependencies))).strip()
