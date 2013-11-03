# Tests for py2deb.
#
# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: November 3, 2013

# Standard library modules.
import logging
import os

# External dependencies.
import coloredlogs
from deb_pkg_tools.package import inspect_package

# Internal modules.
from py2deb.converter import convert

# Initialize logging to the terminal.
coloredlogs.install()
coloredlogs.set_level(logging.DEBUG)

# TODO Test that packages can actually be installed?! (only when os.getuid() == 0)

def test_conversion_of_simple_package_without_dependencies(tmpdir):
    """
    A simple test case that converts coloredlogs==0.4.8 (a simple Python source
    package without any dependencies) to a Debian package.
    """
    directory = str(tmpdir)
    package_name = 'coloredlogs'
    package_version = '0.4.8'
    expected_package_maintainer = 'Peter Odding <peter@peterodding.com>'
    expected_debian_version = '%s-1' % package_version
    # Use py2deb to convert the Python package to a Debian package.
    debian_dependencies = convert(['%s==%s' % (package_name, package_version)], repository=directory, verbose=True)
    # Make sure the generated "Depends:" string is what we would expect it to be.
    assert debian_dependencies == ['python-%s (=%s)' % (package_name, expected_debian_version)]
    # Check the metadata fields of the generated package.
    package_fields = inspect_package(find_package_archive(directory))
    assert package_fields['Package'] == 'python-%s' % package_name
    assert package_fields['Version'] == expected_debian_version
    assert package_fields['Architecture'] == 'all'
    assert package_fields['Maintainer'] == expected_package_maintainer
    # Make sure a dependency on Python was added.
    assert has_dependency(package_fields['Depends'], 'python')

def test_conversion_of_package_with_dependencies(tmpdir):
    """
    Test case that converts pip-accel 0.10.4 and its dependencies (coloredlogs,
    humanfriendly and pip) to Debian packages.
    """
    directory = str(tmpdir)
    package_name = 'pip-accel'
    package_version = '0.10.4'
    expected_package_maintainer = 'Peter Odding <peter.odding@paylogic.eu>'
    expected_debian_version = '%s-1' % package_version
    # Use py2deb to convert the Python package to a Debian package.
    debian_dependencies = convert(['%s==%s' % (package_name, package_version)], repository=directory, verbose=True)
    # Make sure the generated "Depends:" string is what we would expect it to be.
    assert debian_dependencies == ['python-%s (=%s)' % (package_name, expected_debian_version)]
    # Check the metadata fields of the generated package.
    package_fields = inspect_package(find_package_archive(directory, package_name))
    assert package_fields['Package'] == 'python-%s' % package_name
    assert package_fields['Version'] == expected_debian_version
    assert package_fields['Architecture'] == 'all'
    assert package_fields['Maintainer'] == expected_package_maintainer
    # Make sure the proper dependencies were added.
    assert has_dependency(package_fields['Depends'], 'python')
    assert has_dependency(package_fields['Depends'], 'python-coloredlogs')
    assert has_dependency(package_fields['Depends'], 'python-humanfriendly')
    assert has_dependency(package_fields['Depends'], 'python-pip')

def test_conversion_of_replacements(tmpdir):
    """
    Test case that converts pail 0.2 (some random package that has PIL/Pillow
    as a dependency and few other dependencies) and its dependencies
    (coloredlogs, humanfriendly and pip) to Debian packages.
    """
    directory = str(tmpdir)
    package_name = 'pail'
    package_version = '0.2'
    convert(['%s==%s' % (package_name, package_version)], repository=directory, verbose=True)
    package_fields = inspect_package(find_package_archive(directory, package_name))
    assert has_dependency(package_fields['Depends'], 'python')
    assert has_dependency(package_fields['Depends'], 'python-imaging')
    assert has_dependency(package_fields['Depends'], 'python-setuptools')
    assert has_dependency(package_fields['Depends'], 'python-webob')

def find_package_archive(directory, package_name=None):
    archives = []
    for entry in os.listdir(directory):
        pathname = os.path.join(directory, entry)
        if (os.path.isfile(pathname) and entry.endswith('.deb') and
                ((not package_name) or package_name in entry)):
            archives.append(pathname)
    assert len(archives) == 1
    return archives[0]

def has_dependency(depends_line, package_name):
    for dependency in depends_line.split(','):
        tokens = dependency.split()
        if tokens and tokens[0] == package_name:
            return True

# vim: ts=4 sw=4 et
