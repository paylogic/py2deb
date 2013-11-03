# Standard library modules.
import ConfigParser
import logging
import os
import pipes
import shutil
import subprocess
import sys
import tempfile

# External dependencies.
from deb_pkg_tools.control import merge_control_fields, unparse_control_fields
from deb_pkg_tools.package import build_package
from humanfriendly import format_path
from pip_accel.bdist import get_binary_dist, install_binary_dist

# Modules included in our package.
from py2deb.util import (find_python_version, get_tagged_description,
                         patch_control_file)

# Initialize a logger for this module.
logger = logging.getLogger(__name__)

def build(context):
    package = context['package']
    # Create a temporary directory to put the generated package in.
    build_directory = tempfile.mkdtemp()
    # Make sure we clean up the temporary directory afterwards...
    try:
        # Download the package, build the package, create a binary distribution
        # archive, sanitize the contents of the archive and install the
        # sanitized binary distribution inside the build directory (all using
        # pip-accel).
        install_binary_dist(rewrite_filenames(package),
                            prefix=os.path.join(build_directory, 'usr'),
                            python='/usr/bin/%s' % find_python_version())
        # Get the Python requirements converted to Debian dependencies.
        dependencies = [find_python_version()] + package.debian_dependencies
        # If the package installs shared object files, find their dependencies
        # on other system packages. Also determine the package's architecture
        # based on the architecture of the shared object files (if any).
        shared_objects = find_shared_object_files(build_directory)
        architecture = determine_package_architecture(shared_objects)
        if shared_objects:
            dependencies += find_library_dependencies(shared_objects)
        # Generate the control fields.
        control_fields = unparse_control_fields(dict(Package=package.debian_name,
                                                     Version=package.release,
                                                     Description=get_tagged_description(),
                                                     Architecture=architecture,
                                                     Depends=dependencies,
                                                     Priority='optional',
                                                     Section='python',
                                                     Maintainer='py2deb'))
        # Merge the fields defined in stdeb.cfg into the control fields?
        stdeb_cfg = os.path.join(package.directory, 'stdeb.cfg')
        try:
            parser = ConfigParser.RawConfigParser()
            parser.read(stdeb_cfg)
            sections = parser.sections()
            if len(sections) == 1:
                overrides = dict(parser.items(sections[0]))
                logger.debug("Loaded overrides from %s: %s.", format_path(stdeb_cfg), overrides)
                try:
                    del overrides['XS-Python-Version']
                except Exception:
                    pass
                control_fields = merge_control_fields(control_fields, overrides)
                logger.debug("Merged overrides: %s.", control_fields)
        except Exception, e:
            if os.path.isfile(stdeb_cfg):
                logger.warn("Failed to load overrides from %s!", format_path(stdeb_cfg))
                logger.exception(e)
        # Patch any fields for which overrides are present in the configuration
        # file bundled with py2deb or provided by the user.
        control_fields = patch_control_file(package, control_fields)
        # Generate the DEBIAN/control file.
        os.mkdir(os.path.join(build_directory, 'DEBIAN'))
        # TODO Find a way to preserve author/maintainer fields.
        with open(os.path.join(build_directory, 'DEBIAN', 'control'), 'w') as handle:
            control_fields.dump(handle)
        # TODO Post installation script to generate byte code files?!
        return build_package(build_directory)
    finally:
        shutil.rmtree(build_directory)

def rewrite_filenames(package):
    # Download the package, build the package, create a binary distribution
    # archive and sanitize the contents of the archive (all using pip-accel).
    for member, handle in get_binary_dist(package.name, package.version, package.directory):
        # Rewrite /site-packages/ to /dist-packages/. For details see
        # https://wiki.debian.org/Python#Deviations_from_upstream.
        member.name = member.name.replace('/site-packages/', '/dist-packages/')
        yield member, handle

def find_shared_object_files(directory):
    shared_objects = []
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.so'):
                pathname = os.path.join(root, filename)
                os.system('strip --strip-unneeded %s' % pipes.quote(pathname))
                shared_objects.append(pathname)
    if shared_objects:
        logger.debug("Found one or more shared object files: %s", shared_objects)
    return shared_objects

def determine_package_architecture(shared_objects):
    logger.debug("Checking package architecture ..")
    if shared_objects:
        # We found one or more shared object files, i.e. we're dealing with a
        # compiled Python module. To determine the applicable architecture, we
        # simply take the architecture of the current system and (for now)
        # ignore the existence of cross-compilation.
        if sys.maxsize > 2**32:
            logger.debug("We're running on a 64 bit system; assuming package is also 64 bit.")
            return 'amd64'
        else:
            logger.debug("We're running on a 32 bit system; assuming package is also 32 bit.")
            return 'i386'
    else:
        logger.debug("The package's binary distribution doesn't contain any shared object files; assuming we're dealing with a portable package.")
        return 'all'

def find_library_dependencies(shared_objects):
    logger.debug("Abusing `dpkg-shlibdeps' to find dependencies on shared libraries ..")
    # Create a fake source package, because `dpkg-shlibdeps' expects this.
    fake_source_directory = tempfile.mkdtemp()
    try:
        # Create the debian/ directory expected in the source package directory.
        os.mkdir(os.path.join(fake_source_directory, 'debian'))
        # Create an empty debian/control file because `dpkg-shlibdeps' requires
        # this (even though it is apparently fine for the file to be empty ;-).
        open(os.path.join(fake_source_directory, 'debian', 'control'), 'w').close()
        # Run `dpkg-shlibdeps' inside the fake source package directory, but
        # let it analyze the *.so files from the actual build directory.
        command = ['dpkg-shlibdeps', '-O', '--warnings=0'] + shared_objects
        logger.debug("Executing external command: %s", command)
        dpkg_shlibdeps = subprocess.Popen(command, stdout=subprocess.PIPE, cwd=fake_source_directory)
        stdout, stderr = dpkg_shlibdeps.communicate()
        expected_prefix = 'shlibs:Depends='
        if not stdout.startswith(expected_prefix):
            logger.warn("The output of dpkg-shlibdeps doesn't match the expected format! (expected prefix: %r, output: %r)", expected_prefix, stdout)
            return []
        stdout = stdout[len(expected_prefix):]
        dependencies = sorted(d.strip() for d in stdout.split(','))
        logger.debug("Dependencies reported by dpkg-shlibdeps: %s", dependencies)
        return dependencies
    finally:
        shutil.rmtree(fake_source_directory)
