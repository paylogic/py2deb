# Tests for py2deb.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: November 1, 2013

# Standard library modules.
import logging
import os
import shutil
import tempfile
import unittest

# External dependencies.
import coloredlogs
from deb_pkg_tools.package import inspect_package

# Internal modules.
from py2deb.converter import convert
from py2deb.util import transform_package_name

# Initialize logging to the terminal.
coloredlogs.install()
coloredlogs.set_level(logging.DEBUG)

class Py2DebTestCase(unittest.TestCase):

    """
    A simple test case that converts coloredlogs==0.4.8 (a simple package
    without any dependencies) to a Debian package.
    """

    def test_package_conversion(self):
        package_name = 'coloredlogs'
        package_version = '0.4.8'
        expected_package_maintainer = 'Peter Odding <peter@peterodding.com>'
        expected_debian_version = '%s-1' % package_version
        with TemporaryDirectory() as directory:
            # Use py2deb to convert coloredlogs 0.4.8 to a Debian package.
            debian_dependencies = convert(['%s==%s' % (package_name, package_version)], repository=directory, verbose=True)
            # Make sure the generated "Depends:" string is what we would expect it to be.
            self.assertEqual(debian_dependencies, ['python-%s (=%s)' % (package_name, expected_debian_version)])
            # Find the generated package archive.
            package_archives = [fn for fn in os.listdir(directory) if fn.endswith('.deb')]
            self.assertEqual(len(package_archives), 1)
            # Check the metadata fields of the generated package.
            package_fields = inspect_package(os.path.join(directory, package_archives[0]))
            self.assertEqual(package_fields['Package'], 'python-%s' % package_name)
            self.assertEqual(package_fields['Version'], expected_debian_version)
            self.assertEqual(package_fields['Architecture'], 'all')
            self.assertEqual(package_fields['Maintainer'], expected_package_maintainer)
            # Make sure a dependency on Python was added.
            dependencies = [p.strip() for p in package_fields['Depends'].split(',')]
            self.assertTrue(any(p.split()[0] == 'python' for p in dependencies))

class TemporaryDirectory:

    def __init__(self):
        self.directory = tempfile.mkdtemp()

    def __enter__(self):
        return self.directory

    def __exit__(self, exc_type, exc_value, traceback):
        shutil.rmtree(self.directory)

if __name__ == '__main__':
    unittest.main()

# vim: ts=4 sw=4 et
