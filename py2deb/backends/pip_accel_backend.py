"""
pip-accel backend for py2deb
============================
"""

# Standard library modules.
import ConfigParser
import glob
import logging
import os
import pipes
import re
import shutil
import StringIO
import subprocess
import sys
import tempfile

# External dependencies.
from deb_pkg_tools.control import merge_control_fields, unparse_control_fields
from deb_pkg_tools.package import build_package, clean_package_tree
from humanfriendly import format_path
from pip_accel.bdist import get_binary_dist, install_binary_dist

# Modules included in our package.
from py2deb.util import (apply_script, find_python_version,
                         get_tagged_description, patch_control_file)

# Initialize a logger for this module.
logger = logging.getLogger(__name__)

def build(context):
    """
    Entry point for the :py:mod:`pip_accel` backend of :py:mod:`py2deb`.
    """
    package = context['package']
    # Create a temporary directory to put the generated package in.
    build_directory = tempfile.mkdtemp()
    # Make sure we clean up the temporary directory afterwards...
    try:
        # Download the package, build the package, create a binary distribution
        # archive, sanitize the contents of the archive and install the
        # sanitized binary distribution inside the build directory (all using
        # pip-accel).
        if package.is_isolated_package:
            install_prefix = context['install_prefix']
        else:
            install_prefix = '/usr'
        absolute_install_prefix = os.path.join(build_directory, install_prefix.lstrip('/'))
        install_binary_dist(rewrite_filenames(package, package.is_isolated_package, install_prefix),
                            prefix=absolute_install_prefix,
                            python='/usr/bin/%s' % find_python_version())
        # Find the package install directory within the temporary install prefix.
        if package.is_isolated_package:
            package_install_directory = os.path.join(absolute_install_prefix, 'lib')
        else:
            dist_packages = glob.glob(os.path.join(absolute_install_prefix, 'lib/python*/dist-packages'))
            assert len(dist_packages) == 1
            package_install_directory = dist_packages[0]
        apply_script(context['config'], package.name, package_install_directory)
        clean_package_tree(package_install_directory)
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
                                                     Maintainer=find_package_maintainer(package),
                                                     Description=get_tagged_description(),
                                                     Architecture=architecture,
                                                     Depends=dependencies,
                                                     Priority='optional',
                                                     Section='python'))
        logger.debug("Control field defaults: %s.", control_fields)
        # Merge the fields defined in stdeb.cfg into the control fields?
        stdeb_cfg = os.path.join(package.directory, 'stdeb.cfg')
        try:
            parser = ConfigParser.RawConfigParser()
            parser.read(stdeb_cfg)
            sections = parser.sections()
            if len(sections) == 1:
                overrides = dict(parser.items(sections[0]))
                logger.debug("Loaded overrides from %s: %s.", format_path(stdeb_cfg), overrides)
                control_fields = merge_control_fields(control_fields, overrides)
                logger.debug("Merged overrides: %s.", control_fields)
        except Exception, e:
            if os.path.isfile(stdeb_cfg):
                logger.warn("Failed to load overrides from %s!", format_path(stdeb_cfg))
                logger.exception(e)
        # Patch any fields for which overrides are present in the configuration
        # file bundled with py2deb or provided by the user? (only for system
        # wide packages)
        if not package.is_isolated_package:
            control_fields = patch_control_file(package, control_fields)
        # Remove the XS-Python-Version field that may have been included from
        # the stdeb.cfg file.
        try:
            del overrides['Xs-Python-Version']
        except Exception:
            pass
        # Create the DEBIAN directory.
        os.mkdir(os.path.join(build_directory, 'DEBIAN'))
        # Generate the DEBIAN/control file.
        control_file = os.path.join(build_directory, 'DEBIAN', 'control')
        logger.debug("Saving control fields to %s ..", format_path(control_file))
        with open(control_file, 'w') as handle:
            control_fields.dump(handle)
        # Install post-installation and pre-removal scripts.
        backends_directory = os.path.dirname(os.path.abspath(__file__))
        for script_name in ('postinst', 'prerm'):
            source = os.path.join(backends_directory, '%s.sh' % script_name)
            target = os.path.join(build_directory, 'DEBIAN', script_name)
            # Read the shell script bundled with py2deb.
            with open(source) as handle:
                contents = list(handle)
            if script_name == 'postinst':
                # Install a program available inside the custom installation
                # prefix in the system wide executable search path using the
                # Debian alternatives system.
                command_template = "update-alternatives --install {link} {name} {path} 0\n"
                for link, path in context['alternatives']:
                    if os.path.isfile(os.path.join(build_directory, path.lstrip('/'))):
                        contents.append(command_template.format(link=pipes.quote(link),
                                                                name=pipes.quote(os.path.basename(link)),
                                                                path=pipes.quote(path)))
            elif script_name == 'prerm':
                # Cleanup the previously created alternative.
                command_template = "update-alternatives --remove {name} {path}\n"
                for link, path in context['alternatives']:
                    if os.path.isfile(os.path.join(build_directory, path.lstrip('/'))):
                        contents.append(command_template.format(name=pipes.quote(os.path.basename(link)),
                                                                path=pipes.quote(path)))
            # Save the shell script in the build directory.
            with open(target, 'w') as handle:
                for line in contents:
                  handle.write(line)
            # Make sure the shell script is executable.
            os.chmod(target, 0755)
        return build_package(build_directory)
    finally:
        shutil.rmtree(build_directory)

def rewrite_filenames(package, is_isolated_package, install_prefix):
    """
    Download the package, build the package, create a binary distribution
    archive and sanitize the contents of the archive (all using
    :py:mod:`pip_accel`).
    """
    for member, handle in get_binary_dist(package.name, package.version, package.directory):
        if is_isolated_package:
            # Strip the complete /usr/lib/pythonX.Y/site-packages/ prefix so we
            # can replace it with the custom installation prefix (at this point
            # /usr/ has already been stripped by get_binary_dist()).
            member.name = re.sub(r'lib/python\d+(\.\d+)*/(dist|site)-packages/', 'lib/', member.name)
            # Rewrite executable Python scripts so they know about the custom
            # installation prefix.
            if member.name.startswith('bin/'):
                lines = handle.readlines()
                if lines and re.match(r'^#!.*\bpython', lines[0]):
                    i = 0
                    while i < len(lines) and lines[i].startswith('#'):
                        i += 1
                    directory = os.path.join(install_prefix, 'lib')
                    lines.insert(i, 'import sys; sys.path.insert(0, %r)\n' % directory)
                handle = StringIO.StringIO(''.join(lines))
        else:
            # Rewrite /site-packages/ to /dist-packages/. For details see
            # https://wiki.debian.org/Python#Deviations_from_upstream.
            member.name = member.name.replace('/site-packages/', '/dist-packages/')
        yield member, handle

def find_shared_object_files(directory):
    """
    Searches a directory tree for shared object files. Runs
    ``strip --strip-unneeded`` on every ``*.so`` file it finds.

    :param directory: The directory to search (a string).
    :returns: A :py:class:`list` with pathnames of ``*.so`` files.
    """
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

def determine_package_architecture(has_shared_objects):
    """
    Determine the architecture that a package should be tagged with: If a
    package contains ``*.so`` files we're dealing with a compiled Python
    module. To determine the applicable architecture, we simply take the
    architecture of the current system and (for now) ignore the existence of
    cross-compilation.

    :param has_shared_objects: ``True`` if the package contains ``*.so`` files.
    :returns: The architecture string, one of 'all', 'i386' or 'amd64'.
    """
    logger.debug("Checking package architecture ..")
    if has_shared_objects:
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
    """
    (Ab)uses the ``dpkg-shlibdeps`` program to find dependencies on system
    libraries.

    :param shared_objects: The pathnames of the ``*.so`` file(s) contained in
                           the package.
    :returns: A list of strings in the format of the entries on the
              ``Depends:`` line of a binary package control file.
    """
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

def find_package_maintainer(package):
    """
    Get the package maintainer name and e-mail address of a Python package and
    combine them into a single string that can be embedded in a Debian
    package.

    :param package: A :py:class:`py2deb.package.Package` object.
    :returns: A string describing the maintainer (defaults to 'Unknown').
    """
    metadata = package.metadata
    maintainer = metadata.get('maintainer')
    maintainer_email = metadata.get('maintainer-email')
    if not maintainer:
        maintainer = metadata.get('author')
        maintainer_email = metadata.get('author-email')
    if maintainer and maintainer_email:
        maintainer = '%s <%s>' % (maintainer, maintainer_email)
    elif not maintainer:
        maintainer = 'Unknown'
    return maintainer
