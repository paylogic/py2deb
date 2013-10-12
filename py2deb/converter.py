# Standard library modules.
import glob
import logging
import os
import shutil
import sys
import tempfile

# External dependencies.
import pip_accel
import pip.exceptions
from debian.debfile import DebFile
from humanfriendly import format_path

# Modules included in our package.
from py2deb.backends.stdeb_backend import build as build_with_stdeb
from py2deb.config import config
from py2deb.package import Package
from py2deb.util import check_supported_platform

# Initialize a logger for this module.
logger = logging.getLogger(__name__)

def convert(pip_install_args, repository=None, backend=build_with_stdeb, auto_install=False, verbose=False):
    """
    Convert Python packages downloaded using pip-accel to Debian packages.
    """
    # Make sure we're running on a supported configuration.
    check_supported_platform()
    # Initialize the build directory.
    build_dir = tempfile.mkdtemp(prefix='py2deb_')
    logger.debug("Created build directory: %s", format_path(build_dir))
    # Find package replacements.
    replacements = dict(config.items('replacements'))
    # Tell pip to extract into the build directory
    pip_install_args.extend(['-b', build_dir])
    # Generate list of requirements.
    requirements = get_required_packages(pip_install_args,
                                         name_prefix=config.get('general', 'name-prefix'),
                                         replacements=replacements,
                                         build_dir=build_dir,
                                         config=config)
    logger.debug("Required packages: %r", requirements)
    converted = []
    repository = repository or config.get('general', 'repository')
    for package in requirements:
        result = find_existing_debs(package, repository)
        if result:
            archive = result[-1]
            logger.info("Skipping conversion of %s (existing archive found: %s).",
                         package.name, format_path(archive))
        else:
            logger.info("Converting %s to %s ..", package.name, package.debian_name)
            pathname = backend(dict(package=package,
                                    replacements=replacements,
                                    config=config,
                                    verbose=verbose,
                                    auto_install=auto_install))
            filename = os.path.basename(pathname)
            if not os.path.samefile(pathname, os.path.join(repository, filename)):
                logger.debug("Moving %s to %s ..", filename, format_path(repository))
                shutil.move(pathname, repository)
            logger.info("Finished converting %s to %s (%s).",
                        package.name, package.debian_name,
                        format_path(os.path.join(repository, filename)))
            archive = os.path.join(repository, os.path.basename(pathname))
        debfile = DebFile(archive)
        converted.append('%(Package)s (=%(Version)s)' % debfile.debcontrol())
    # Clean up the build directory.
    shutil.rmtree(build_dir)
    logger.debug("Removed build directory: %s", build_dir)
    return converted

def find_existing_debs(package, repository):
    """
    Find existing ``*.deb`` package archives that were previously generated.
    """
    return glob.glob(os.path.join(repository, package.debian_file_pattern))

def get_required_packages(pip_install_args, name_prefix, replacements, build_dir, config):
    """
    Find the packages that have to be converted to Debian packages (excludes
    packages that have replacements).
    """
    pip_arguments = ['install', '--ignore-installed'] + pip_install_args
    # Create a dictionary of packages downloaded by pip-accel.
    packages = {}
    for name, version, directory in get_source_dists(pip_arguments, build_dir):
        package = Package(name, version, directory, name_prefix, config)
        packages[package.name] = package
    # Create a list of packages to ignore.
    to_ignore = []
    for pkg_name, package in packages.iteritems():
        if pkg_name in replacements:
            to_ignore.extend(get_related_packages(pkg_name, packages))
    # Yield packages that should be build.
    to_build = []
    for pkg_name, package in packages.iteritems():
        if pkg_name not in to_ignore:
            to_build.append(package)
        else:
            logger.warn("%s is in the ignore list and will not be build.", pkg_name)
    return sorted(to_build, key=lambda p: p.name.lower())

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

def get_source_dists(pip_arguments, build_dir, max_retries=10):
    """
    Download and unpack the source distributions for all dependencies
    specified in the pip command line arguments.
    """
    with RedirectOutput(sys.stderr):
        pip_accel.initialize_directories()
        logger.debug("Passing the following arguments to pip-accel: %s", ' '.join(pip_arguments))
        for i in xrange(max_retries):
            logger.debug("Attempt %i/%i of getting source distributions using pip-accel.",
                         i+1, max_retries)
            try:
                return pip_accel.unpack_source_dists(pip_arguments, build_directory=build_dir)
            except pip.exceptions.DistributionNotFound:
                pip_accel.download_source_dists(pip_arguments, build_dir)
        else:
            raise Exception, "pip-accel failed to get the source dists %i times." % max_retries

class RedirectOutput:

    """
    Make sure all output generated by pip and its subprocesses (python setup.py
    ...) is redirected to the standard error stream. This way we can be sure
    that the standard output stream can be reliably used for our purposes
    (specifically: reporting Debian package dependencies).
    """

    def __init__(self, target):
        self.target = target
        self.stdout = sys.stdout

    def __enter__(self):
        sys.stdout = self.target

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self.stdout
