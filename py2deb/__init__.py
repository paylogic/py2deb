"""
Usage: py2deb [OPTIONS] -- PIP_ARGS

Supported options:

  -c, --config=FILE  set the user configuration file
  -r, --repo=DIR     override the default repository directory
  -p, --prefix=STR   set package name prefix (defaults to `python-')
  -P, --print-deps   prints a valid value for the `Depends` line of a Debian
                     control file with the package names and pinned versions of
                     all built packages
  -v, --verbose      more output
  -y, --yes          automatically confirm installation of system-wide dependencies
  -h, --help         show this message and exit
"""

# Standard library modules
import getopt
import logging
import os
import sys

# Internal modules
from py2deb.config import load_config
from py2deb.converter import convert

def main():

    # Command line option defaults
    config_file = None
    repo_dir = None
    name_prefix = None
    print_dependencies = False
    verbose = False
    auto_install = False

    # Parse command line options
    options, pip_args = getopt.gnu_getopt(sys.argv[1:], 'c:r:p:Pvyh',
            ['config=', 'repo=', 'prefix=', 'print-deps', 'verbose', 'yes', 'help'])

    if not pip_args:
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
            repo_dir = os.path.abspath(value)
            if not os.path.isdir(repo_dir):
                msg = "Repository directory doesn't exist! (%s)"
                raise Exception, msg % repo_dir
        elif option in ('-p', '--prefix'):
            name_prefix = value
        elif option in ('-P', '--print-deps'):
            print_dependencies = True
        elif option in ('-v', '--verbose'):
            verbose = True
        elif option in ('-y', '--yes'):
            auto_install = True
        elif option in ('-h', '--help'):
            usage()
            return
        else:
            msg = "Unrecognized option: %s"
            raise Exception, msg % option

    # Configure the logging level.
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize the configuration.
    config = load_config(filename=config_file)
    if repo_dir:
        config.set('general', 'repository', repo_dir)
    if name_prefix:
        config.set('general', 'name-prefix', name_prefix)

    # Start the conversion.
    converted = convert(pip_args,
                        config=config,
                        auto_install=auto_install,
                        verbose=verbose)

    if print_dependencies:
        print ', '.join(converted)

def usage():
    print __doc__.strip()
