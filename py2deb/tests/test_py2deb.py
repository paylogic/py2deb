# Tests for py2deb.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: November 1, 2013

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
# TODO Test packages with dependencies.

def test_conversion_of_simple_package_without_dependencies(tmpdir):
    """
    A simple test case that converts coloredlogs==0.4.8 (a simple package
    without any dependencies) to a Debian package.
    """
    directory = str(tmpdir)
    package_name = 'coloredlogs'
    package_version = '0.4.8'
    expected_package_maintainer = 'Peter Odding <peter@peterodding.com>'
    expected_debian_version = '%s-1' % package_version
    # Use py2deb to convert coloredlogs 0.4.8 to a Debian package.
    debian_dependencies = convert(['%s==%s' % (package_name, package_version)], repository=directory, verbose=True)
    # Make sure the generated "Depends:" string is what we would expect it to be.
    assert debian_dependencies == ['python-%s (=%s)' % (package_name, expected_debian_version)]
    # Find the generated package archive.
    package_archives = [fn for fn in os.listdir(directory) if fn.endswith('.deb')]
    assert len(package_archives) == 1
    # Check the metadata fields of the generated package.
    package_fields = inspect_package(os.path.join(directory, package_archives[0]))
    assert package_fields['Package'] == 'python-%s' % package_name
    assert package_fields['Version'] == expected_debian_version
    assert package_fields['Architecture'] == 'all'
    assert package_fields['Maintainer'] == expected_package_maintainer
    # Make sure a dependency on Python was added.
    dependencies = [p.strip() for p in package_fields['Depends'].split(',')]
    assert any(p.split()[0] == 'python' for p in dependencies)

# vim: ts=4 sw=4 et
