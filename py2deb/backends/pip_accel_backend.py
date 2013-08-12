# Standard library modules.
import logging
import os
import pipes
import shutil
import subprocess
import sys
import tempfile
import time

# External dependencies.
from deb_pkg_tools.package import build_package
from debian.deb822 import Deb822
from pip_accel.bdist import get_binary_dist, install_binary_dist

# Modules included in our package.
from py2deb.util import find_python_version, patch_control_file

# Initialize a logger for this module.
logger = logging.getLogger(__name__)

def build(context):
    package = context['package']
    # Create a temporary directory to put the generated package in.
    build_directory = tempfile.mkdtemp()
    # Make sure we clean up the temporary directory afterwards...
    try:
        # Download the package, build the package, create a binary distribution
        # archive and sanitize the contents of the archive (all using pip-accel).
        members = get_binary_dist(package.name, package.version, package.directory)
        # Install the sanitized binary distribution inside the build directory.
        install_binary_dist(members,
                            prefix=os.path.join(build_directory, 'usr'),
                            python='/usr/bin/%s' % find_python_version())
        # Get the Python requirements converted to Debian dependencies.
        dependencies = [find_python_version()] + package.debian_dependencies
        # Look for shared object files in the package tree.
        shared_objects = find_shared_object_files(build_directory)
        architecture = determine_package_architecture(shared_objects)
        if shared_objects:
            dependencies += find_library_dependencies(shared_objects)
        # Generate the DEBIAN/control file.
        os.mkdir(os.path.join(build_directory, 'DEBIAN'))
        # TODO Find a way to preserve author/maintainer fields.
        control_fields = Deb822(dict(
          Package=package.debian_name,
          Version=package.release,
          Description=time.strftime('Packaged by py2deb on %B %e, %Y at %H:%M'),
          Depends=', '.join(sorted(dependencies)),
          Priority='optional',
          Section='python',
          Architecture=architecture,
          Maintainer='py2deb'))
        control_fields = patch_control_file(package, control_fields)
        with open(os.path.join(build_directory, 'DEBIAN', 'control'), 'w') as handle:
            control_fields.dump(handle)
        # TODO Post installation script to generate byte code files?!
        return build_package(build_directory)
    finally:
        shutil.rmtree(build_directory)

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
