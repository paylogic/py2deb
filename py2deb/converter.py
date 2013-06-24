# Standard library modules
import fnmatch
import glob
import os
import shutil
import sys
import tempfile
from ConfigParser import ConfigParser

# External dependencies
import pip_accel
import pip.exceptions
from debian.deb822 import Deb822
from debian.debfile import DebFile

# Internal modules
from py2deb.config import config_dir
from py2deb.logger import logger
from py2deb.package import Package
from py2deb.util import run

def convert(pip_args, auto_install=False, verbose=False, config_file=None, cleanup=True):
    """
    Creates debian packages by converting python packages gained through pip-accel.
    """
    # Initialize build directory
    build_dir = tempfile.mkdtemp(prefix='py2deb_')
    logger.debug('Created build directory: %s', build_dir)

    # Initialize config
    config = ConfigParser()
    if config_file:
        config.read(os.path.abspath(config_file))
    else:
        config.read(os.path.join(config_dir, 'py2deb.ini'))

    # Prefix
    prefix = config.get('general', 'prefix')
    # Destination of built packages
    repository = os.path.abspath(config.get('general', 'repository'))
    # Replacements
    replacements = dict(config.items('replacements'))
    # Tell pip to extract into the build directory
    pip_args.extend(['-b', build_dir])

    converted = []
    for package in get_required_packages(pip_args, prefix, replacements):
        result = find_build(package, repository)
        if result:
            logger.info('%s has been found in %s, skipping build.',
                         package.debian_name, repository)
            debfile = DebFile(result[-1])
        else:
            logger.info('Starting conversion of %s', package.name)
            debianize(package, verbose)
            patch_rules(package)
            patch_control(package, replacements, config)
            apply_script(package, config, verbose)
            sanity_check_dependencies(package, auto_install)
            debfile = build(package, repository, verbose)
            logger.info('%s has been converted to %s', package.name, package.debian_name)
        converted.append('%(Package)s (=%(Version)s)' % debfile.debcontrol())

    # Clean up if needed
    if cleanup:
        shutil.rmtree(build_dir)
        logger.debug('Removed build directory: %s', build_dir)

    return converted

def find_build(package, repository):
    return glob.glob(os.path.join(repository, package.debian_file_pattern))

def get_required_packages(pip_args, prefix, replacements):
    """
    Generator for packages that need to be converted.
    """
    pip_arguments = ['install', '--ignore-installed'] + pip_args

    # Create a dict of packages downloaded by pip-accel
    packages = {}
    for name, version, directory in get_source_dists(pip_arguments):
        package = Package(name, version, directory, prefix)
        packages[package.name] = package

    # Create a list of packages to ignore
    to_ignore = []
    for pkg_name, package in packages.iteritems():
        if pkg_name in replacements:
            to_ignore.extend(get_related_packages(pkg_name, packages))

    # Yield packages that should be build
    for pkg_name, package in packages.iteritems():
        if pkg_name not in to_ignore:
            yield package
        else:
            logger.info('%s is in the ignore list and will not be build.', pkg_name)

def get_related_packages(pkg_name, packages):
    """
    Creates a list of all related packages.
    """
    related = []
    if pkg_name in packages:
        related.append(pkg_name)
        for dependency in packages.get(pkg_name).py_dependencies:
            related.extend(get_related_packages(dependency, packages))
    return related

def get_source_dists(pip_arguments, max_retries=10):
    """
    Download and unpack the source distributions for all dependencies
    specified in the pip command line arguments.
    """
    pip_accel.initialize_directories()
    logger.debug('Passing the follow arguments to pip-accel: %s', ' '.join(pip_arguments))
    for i in xrange(max_retries):
        logger.debug('Attempt %i/%i of getting source distributions through pip-accel.', 
                     i+1, max_retries)
        try:
            return pip_accel.unpack_source_dists(pip_arguments)
        except pip.exceptions.DistributionNotFound:
            pip_accel.download_source_dists(pip_arguments)
    else:
        raise Exception, 'pip-accel failed to get the source distributions %i times.' % max_retries

def debianize(package, verbose):
    """
    Debianize a python package using stdeb.
    """
    logger.info('Debianizing %s', package.name)
    python = os.path.join(sys.prefix, 'bin', 'python')
    command = ' '.join([python, 'setup.py', '--command-packages=stdeb.command',
                        'debianize', '--ignore-install-requires'])
    if run(command, package.directory, verbose):
        raise Exception, 'Failed to debianize %s' % package.name

    logger.info('Debianized %s', package.name)

def patch_rules(package):
    """
    Patch rules file to prevent dh_python2 to guess dependencies.
    This only has effect if the 0.6.0+git release of stdeb is used.
    """
    logger.info('Patching rules file of %s', package.name)
    patch = '\noverride_dh_python2:\n\tdh_python2 --no-guessing-deps\n'
    rules_file = os.path.join(package.directory, 'debian', 'rules')

    lines = []
    with open(rules_file, 'r') as rules:
        lines = rules.readlines()
        for i in range(len(lines)):
            if '%:' in lines[i]:
                lines.insert(i-1, patch)
                break
        else:
            raise Exception, 'Failed to patch %s' % rules_file

    with open(rules_file, 'w+') as rules:
        rules.writelines(lines)
    logger.info('The rules file of %s has been patched', package.name)

def patch_control(package, replacements, config):
    """
    Patch control file to add dependencies.
    """
    logger.info('Patching control file of %s', package.name)
    control_file = os.path.join(package.directory, 'debian', 'control')

    with open(control_file, 'r') as control:
        paragraphs = list(Deb822.iter_paragraphs(control))
        assert len(paragraphs) == 2, 'Unexpected control file format for %s.' % package.name

    with open(control_file, 'w+') as control:
        # This patch adds dependencies
        control_dict_pkg = control_patch_pkg(package, replacements)
        for field in control_dict_pkg:
            paragraphs[1].merge_fields(field, control_dict_pkg)

        # This patch adds fields defined in the config
        control_dict_conf = control_patch_cfg(package, config)
        for field in control_dict_conf:
            paragraphs[1].merge_fields(field, control_dict_conf)

        paragraphs[1]['Package'] = package.debian_name

        paragraphs[0].dump(control)
        control.write('\n')
        paragraphs[1].dump(control)
    logger.info('The control file of %s has been patched', package.name)

def control_patch_pkg(package, replacements):
    """
    Creates a Deb822 dictionary used to patch
    the dependency field in a control file.
    """
    return Deb822(dict(Depends=', '.join(package.debian_dependencies(replacements))))

def control_patch_cfg(package, config):
    """
    Creates a Deb822 dictionary used to patch the
    second paragraph of a control file by using
    fields defined in a config file.
    """
    items = {}
    if config.has_section(package.name):
        items = dict(config.items(package.name))

    # Remove fields supported by Py2Deb but not by debian
    for to_remove in ('script'):
        items.pop(to_remove, None)

    return Deb822(items)

def apply_script(package, config, verbose):
    """
    Checks if a line of shell script is defined in the config and
    executes it with the directory of the package as the current
    working directory.
    """
    if config.has_option(package.name, 'script'):
        command = config.get(package.name, 'script')
        logger.info('Applying the following script on %s in %s: %s',
                     package.name, package.directory, command)

        if run(command, package.directory, verbose):
            raise Exception, 'Failed to apply script on %s' % package.name

        logger.info('The script has been applied.')

def sanity_check_dependencies(package, auto_install):
    logger.debug('Performing a sanity check on %s', package.name)
    result = pip_accel.deps.sanity_check_dependencies(package.name)
    assert result, 'Failed sanity check on %s' % package.name
    logger.debug('Sanity check completed')

def build(package, repository, verbose):
    """
    Builds the debian package using dpkg-buildpackage.
    """
    logger.info('Building %s', package.debian_name)
    command = 'dpkg-buildpackage -us -uc'

    if run(command, package.directory, verbose):
        raise Exception, 'Failed to build %s' % package.debian_name

    topdir = os.path.dirname(package.directory)
    for item in os.listdir(topdir):
        if fnmatch.fnmatch(item, '%s_*.deb' % package.debian_name):
            source = os.path.join(topdir, item)
            shutil.move(source, repository)
            logger.info('Build succeeded, moving %s to %s', item, repository)
            return DebFile(os.path.join(repository, item))
    else:
        raise Exception, 'Could not find build of %s' % package.debian_name