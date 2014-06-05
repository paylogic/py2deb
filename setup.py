#!/usr/bin/env python

# Setup script for the `py2deb' package.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 5, 2014
# URL: https://py2deb.readthedocs.org

import os, re
from setuptools import setup, find_packages

# Find the directory where the source distribution was unpacked.
source_directory = os.path.dirname(os.path.abspath(__file__))

# Find the current version.
module = os.path.join(source_directory, 'py2deb', '__init__.py')
for line in open(module, 'r'):
    match = re.match(r'^__version__\s*=\s*["\']([^"\']+)["\']$', line)
    if match:
        version_string = match.group(1)
        break
else:
    raise Exception("Failed to extract version from py2deb/__init__.py!")

# Fill in the long description (for the benefit of PyPi)
# with the contents of README.rst (rendered by GitHub).
readme_file = os.path.join(source_directory, 'README.rst')
readme_text = open(readme_file, 'r').read()

# Fill in the "install_requires" field based on requirements.txt.
requirements = [l.strip() for l in open(os.path.join(source_directory, 'requirements.txt'), 'r') if not l.startswith('#')]

setup(name='py2deb',
      version=version_string,
      description='Python to Debian package converter',
      long_description=readme_text,
      url='https://py2deb.readthedocs.org',
      author='Peter Odding',
      author_email='peter@peterodding.com',
      packages=find_packages(),
      test_suite='py2deb.tests',
      entry_points={'console_scripts': ['py2deb = py2deb.cli:main']},
      install_requires=requirements)

# vim: ts=4 sw=4
