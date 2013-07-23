# Tests for py2deb.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 23, 2013

# Standard library modules.
import unittest

# Internal modules.
from py2deb.util import transform_package_name

class Py2DebTestCase(unittest.TestCase):

    def test_package_name_transformation(self):
        self.assertEqual(transform_package_name('python', 'BeautifulSoup'), 'python-beautifulsoup')
        self.assertEqual(transform_package_name('python', 'python', 'debian'), 'python-debian')

if __name__ == '__main__':
    unittest.main()

# vim: ts=4 sw=4 et
