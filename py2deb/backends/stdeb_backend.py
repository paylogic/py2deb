# Standard library modules.
import fnmatch
import logging
import os
import pipes
import shutil
import sys
import time

# External dependencies.
from deb_pkg_tools.control import merge_control_fields
from deb_pkg_tools.package import clean_package_tree
from debian.deb822 import Deb822
from pip_accel.deps import sanity_check_dependencies
from stdeb import __version__ as stdeb_version

# Modules included in our package.
from py2deb.util import patch_control_file, run

# Initialize a logger for this module.
logger = logging.getLogger(__name__)

def build(context):
    debianize(context['package'], context['verbose'])
    patch_control(context['package'], context['config'])
    apply_script(context['package'], context['config'], context['verbose'])
    sanity_check_dependencies(context['package'].name, context['auto_install'])
    clean_package_tree(context['package'].directory)
    return dpkg_buildpackage(context['package'], context['verbose'])

def debianize(package, verbose):
    """
    Debianize a Python package using stdeb.
    """
    if os.path.isfile(os.path.join(package.directory, 'debian', 'control')):
        logger.warn("Package was previously Debianized: Overwriting existing files!")
        shutil.rmtree(os.path.join(package.directory, 'debian'))
    logger.debug('Debianizing %s', package.name)
    python = os.path.join(sys.prefix, 'bin', 'python')
    command = [python, 'setup.py', '--command-packages=stdeb.command', 'debianize']
    if stdeb_version == '0.6.0': # The "old" version of stdeb.
        command.append('--ignore-install-requires')
    if run(' '.join(command), package.directory, verbose):
        raise Exception, "Failed to debianize package! (%s)" % package.name
    logger.debug('Debianized %s', package.name)

def patch_control(package, config):
    """
    Patch the control file of a 'Debianized' Python package (see
    :py:func:`debianize()`) to modify the package metadata and inject the
    Python package's dependencies as Debian package dependencies.
    """
    logger.debug('Patching control file of %s', package.name)
    control_file = os.path.join(package.directory, 'debian', 'control')
    with open(control_file, 'r') as handle:
        paragraphs = list(Deb822.iter_paragraphs(handle))
        logger.debug("Original control fields: %r", paragraphs[1])
        assert len(paragraphs) == 2, 'Unexpected control file format for %s.' % package.name
    with open(control_file, 'w') as handle:
        # Patch the metadata and dependencies:
        #  - Make sure the package name uses our prefix.
        #  - Make sure the word py2deb occurs in the package description. This
        #    makes `apt-cache search py2deb' report packages created by py2deb.
        overrides = dict(Package=package.debian_name,
                         Description=time.strftime('Packaged by py2deb on %B %e, %Y at %H:%M'),
                         Depends=', '.join(package.debian_dependencies))
        paragraphs[1] = merge_control_fields(paragraphs[1], overrides)
        logger.debug("Patched control fields (phase 1/2): %r", paragraphs[1])
        # Patch any fields for which overrides are present in the configuration
        # file bundled with py2deb or provided by the user.
        paragraphs[1] = patch_control_file(package, paragraphs[1])
        logger.debug("Patched control fields (phase 2/2): %r", paragraphs[1])
        # Save the patched control file.
        paragraphs[0].dump(handle)
        handle.write('\n')
        paragraphs[1].dump(handle)
    logger.debug('The control file of %s has been patched', package.name)

def apply_script(package, config, verbose):
    """
    Checks if a line of shell script is defined in the config and
    executes it with the directory of the package as the current
    working directory.
    """
    if config.has_option(package.name, 'script'):
        command = config.get(package.name, 'script')
        logger.debug('Applying the following script on %s in %s: %s',
                     package.name, package.directory, command)
        if run(command, package.directory, verbose):
            raise Exception, 'Failed to apply script on %s' % package.name
        logger.debug('The script has been applied.')

def dpkg_buildpackage(package, verbose):
    """
    Builds the Debian package using dpkg-buildpackage.
    """
    logger.info('Building %s', package.debian_name)
    # XXX Always run the `dpkg-buildpackage' command in a clean environment.
    # Without this and `py2deb' is running in a virtual environment, the
    # pathnames inside the generated Debian package will refer to the virtual
    # environment instead of the system wide Python installation!
    command = '. /etc/environment && dpkg-buildpackage -us -uc'
    if verbose:
        os.environ['DH_VERBOSE'] = '1'
    if stdeb_version == '0.6.0+git': # The "new" version of stdeb.
        # XXX stdeb 0.6.0+git uses dh_python2, which guesses dependencies
        # by default. We don't want this so we override this behavior.
        os.environ['DH_OPTIONS'] = '--no-guessing-deps'
    if run(command, package.directory, verbose):
        raise Exception, 'Failed to build %s' % package.debian_name
    logger.debug("Scanning for generated Debian packages ..")
    parent_directory = os.path.dirname(package.directory)
    for filename in os.listdir(parent_directory):
        if filename.endswith('.deb'):
            pathname = os.path.join(parent_directory, filename)
            logger.debug("Considering file: %s", pathname)
            if fnmatch.fnmatch(filename, '%s_*.deb' % package.debian_name):
                logger.info('Build of %s succeeded, checking package with Lintian ..', pathname)
                os.system('lintian %s >&2' % pipes.quote(pathname))
                return pathname
    else:
        raise Exception, 'Could not find build of %s' % package.debian_name

