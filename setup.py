#!/usr/bin/env python

"""
Setup script for the `py2deb` package.
"""

# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: June 18, 2014
# URL: https://py2deb.readthedocs.org

# Standard library modules.
import os
import sys

# We use setuptools to support entry points, `python setup.py test', etc.
import setuptools

# Find the directory where the source distribution was unpacked.
source_directory = os.path.dirname(os.path.abspath(__file__))

# Add the source distribution directory to Python's module search path.
sys.path.append(source_directory)

# Find the current version.
from py2deb import __version__ as version_string

# Fill in the long description (for the benefit of PyPi)
# with the contents of README.rst (rendered by GitHub).
with open(os.path.join(source_directory, 'README.rst')) as handle:
    readme_text = handle.read()

# Fill in the "install_requires" field based on requirements.txt.
with open(os.path.join(source_directory, 'requirements.txt')) as handle:
    requirements = [line.strip() for line in handle if not line.startswith('#')]

setuptools.setup(
    name='py2deb',
    version=version_string,
    description='Python to Debian package converter',
    long_description=readme_text,
    url='https://py2deb.readthedocs.org',
    author='Peter Odding & Arjan Verwer (Paylogic International)',
    author_email='peter.odding@paylogic.com',
    packages=setuptools.find_packages(),
    test_suite='py2deb.tests',
    entry_points={'console_scripts': ['py2deb = py2deb.cli:main']},
    install_requires=requirements,
    include_package_data=True)
