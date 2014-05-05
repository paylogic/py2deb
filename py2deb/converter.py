# Standard library modules.
import glob
import logging
import os
import shutil
import tempfile

# External dependencies.
import pip_accel
import pip.exceptions
from humanfriendly import format_path
from pip_accel.deps import sanity_check_dependencies

# Modules included in our package.
from py2deb.backends.pip_accel_backend import build as build_with_pip_accel
from py2deb.backends.stdeb_backend import build as build_with_stdeb
from py2deb.config import config
from py2deb.exceptions import BackendFailed
from py2deb.package import Package
from py2deb.util import check_supported_platform

# Initialize a logger for this module.
logger = logging.getLogger(__name__)

# Increase the verbosity of the stdeb logger.
logging.getLogger('stdeb').setLevel(logging.DEBUG)

def convert(pip_install_args, repository=None, packages_to_rename={}, backend=build_with_stdeb, auto_install=False, verbose=False):
    """
    Convert Python packages to Debian packages. This function is a wrapper for
    the real conversion function (:py:func:`convert_real()`). If the requested
    backend fails, the wrapper will retry the build with the alternative
    backend.
    """
    # Make sure we're running on a supported configuration.
    check_supported_platform()
    # If the user requested to build packages with a custom installation
    # prefix, the pip-accel backend is our only option.
    if config.has_option('general', 'install-prefix'):
        return convert_real(pip_install_args,
                            repository=repository,
                            packages_to_rename=packages_to_rename,
                            backend=build_with_pip_accel,
                            auto_install=auto_install,
                            verbose=verbose)
    # Try to build the package with the requested backend but fall back to
    # the alternative backend if the requested backend fails.
    try:
        return convert_real(pip_install_args,
                            repository=repository,
                            packages_to_rename=packages_to_rename,
                            backend=backend,
                            auto_install=auto_install,
                            verbose=verbose)
    except BackendFailed, e:
        if backend == build_with_stdeb:
            logger.exception(e)
            logger.warn("py2deb's stdeb backend failed, falling back to pip-accel backend.")
            alternative_backend = build_with_pip_accel
        elif backend == build_with_pip_accel:
            logger.exception(e)
            logger.warn("py2deb's pip-accel backend failed, falling back to stdeb backend.")
            alternative_backend = build_with_stdeb
        else:
            raise
        return convert_real(pip_install_args,
                            repository=repository,
                            packages_to_rename=packages_to_rename,
                            backend=alternative_backend,
                            auto_install=auto_install,
                            verbose=verbose)

def convert_real(pip_install_args, repository=None, packages_to_rename={}, backend=build_with_stdeb, auto_install=False, verbose=False):
    """
    Convert Python packages to Debian packages.
    """
    # Initialize the build directory.
    build_dir = tempfile.mkdtemp(prefix='py2deb_')
    logger.debug("Created build directory: %s", format_path(build_dir))
    try:
        # Find package replacements.
        replacements = dict(config.items('replacements'))
        # Tell pip to extract into our build directory.
        pip_install_args = list(pip_install_args) + ['-b', build_dir]
        # Generate list of requirements.
        name_prefix = config.get('general', 'name-prefix')
        primary_packages, packages_to_build = \
            get_required_packages(pip_install_args=pip_install_args,
                                  name_prefix=name_prefix,
                                  replacements=replacements,
                                  build_dir=build_dir,
                                  config=config)
        logger.debug("Primary packages (given on the command line): %r", primary_packages)
        logger.debug("Packages to build (all dependencies except those with replacements): %r", packages_to_build)
        for package in packages_to_build:
            name_override = packages_to_rename.get(package.name.lower())
            if name_override:
                logger.info("Resetting name of package %s to %s ..", package.name, name_override)
                package.debian_name = name_override
        repository = repository or config.get('general', 'repository')
        for package in packages_to_build:
            result = find_existing_debs(package, repository)
            if result:
                logger.info("Skipping conversion of %s (existing archive found: %s).",
                             package.name, format_path(result[-1]))
            else:
                if package.name != package.debian_name:
                    logger.info("Converting %s to %s ..", package.name, package.debian_name)
                else:
                    logger.info("Converting %s ..", package.name)
                sanity_check_dependencies(package.name, auto_install)
                pathname = backend(dict(package=package,
                                        config=config,
                                        verbose=verbose,
                                        auto_install=auto_install))
                old_path = os.path.realpath(pathname)
                new_path = os.path.realpath(os.path.join(repository, os.path.basename(pathname)))
                if new_path != old_path:
                    logger.debug("Moving %s to %s ..", format_path(old_path), format_path(new_path))
                    shutil.move(old_path, new_path)
                logger.info("Finished converting %s to %s (%s).",
                            package.name, package.debian_name,
                            format_path(new_path))
        return [p.debian_dependency for p in primary_packages]
    finally:
        # Clean up the build directory.
        logger.debug("Cleaning up build directory: %s", build_dir)
        shutil.rmtree(build_dir)

def find_existing_debs(package, repository):
    """
    Find existing ``*.deb`` package archives that were previously generated.
    """
    return glob.glob(os.path.join(repository, package.debian_file_pattern))

def get_required_packages(pip_install_args, name_prefix, replacements, build_dir, config):
    """
    Find the Python package(s) required to install the Python package(s) that
    the user requested to be converted. This includes transitive dependencies.

    :param pip_install_args: The arguments to be passed to ``pip install`` (a
                             list of strings).
    :param name_prefix: The string prefixed to names of converted packages.
    :param replacements: A dictionary of replacement packages.
    :param build_dir: Pathname of temporary build directory (a string).
    :param config: :py:class:`ConfigParser.RawConfigParser` object.
    :returns: Two lists with :py:class:`py2deb.package.Package` objects. The
              first list contains the package(s) that py2deb was directly
              requested to build by the user while the second list also
              contains all transitive dependencies.
    """
    pip_arguments = ['install', '--ignore-installed'] + pip_install_args
    # Create a dictionary of all packages downloaded by pip-accel.
    all_packages = {}
    # Also keep a list of the packages that the user requested to install. This
    # excludes transitive dependencies.
    primary_packages = []
    for requirement in get_source_dists(pip_arguments, build_dir):
        package = Package(requirement.name, requirement.version,
                          requirement.source_directory, name_prefix, config)
        all_packages[package.name] = package
        if requirement.is_direct:
            primary_packages.append(package)
    # Create a list of packages to ignore.
    packages_with_replacements = []
    for pkg_name, package in all_packages.iteritems():
        if pkg_name in replacements:
            packages_with_replacements.extend(get_related_packages(pkg_name, all_packages))
    # Yield packages that should be build.
    packages_to_build = []
    for pkg_name, package in all_packages.iteritems():
        if pkg_name not in packages_with_replacements:
            packages_to_build.append(package)
        else:
            logger.warn("%s is in the ignore list (it won't be converted).", pkg_name)
    return sorted_packages(primary_packages), sorted_packages(packages_to_build)

def get_source_dists(pip_arguments, build_dir, max_retries=10):
    """
    Download and unpack the source distributions for all dependencies
    specified in the pip command line arguments.
    """
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

def sorted_packages(packages):
    return sorted(packages, key=lambda p: p.name.lower())
