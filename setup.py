#!/usr/bin/env python

"""Setup script for the `py2deb` package."""

# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: April 15, 2016
# URL: https://py2deb.readthedocs.org

# Standard library modules.
import codecs
import os
import re
import sys

# De-facto standard solution for Python packaging.
from setuptools import find_packages, setup


def get_absolute_path(*args):
    """Transform relative pathnames into absolute pathnames."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *args)


def get_contents(filename):
    """Get the contents of a file relative to the source distribution directory."""
    with codecs.open(get_absolute_path(filename), 'r', 'utf-8') as handle:
        return handle.read()


def get_version(filename):
    """Extract the version number from a Python module."""
    contents = get_contents(filename)
    metadata = dict(re.findall('__([a-z]+)__ = [\'"]([^\'"]+)', contents))
    return metadata['version']


def get_requirements(*args):
    """Get requirements from pip requirement files."""
    requirements = set()
    with open(get_absolute_path(*args)) as handle:
        for line in handle:
            # Strip comments.
            line = re.sub(r'^#.*|\s#.*', '', line)
            # Ignore empty lines
            if line and not line.isspace():
                requirements.add(re.sub(r'\s+', '', line))
    return sorted(requirements)


def have_environment_marker_support():
    """
    Check whether setuptools has support for PEP-426 environment markers.

    Based on the ``setup.py`` script of the ``pytest`` package:
    https://bitbucket.org/pytest-dev/pytest/src/default/setup.py
    """
    try:
        from pkg_resources import parse_version
        from setuptools import __version__
        return parse_version(__version__) >= parse_version('0.7.2')
    except Exception:
        return False


# Conditional importlib dependency for Python 2.6 and 3.0 when creating a source distribution.
install_requires = get_requirements('requirements.txt')
if 'bdist_wheel' not in sys.argv:
    if sys.version_info[:2] <= (2, 6) or sys.version_info[:2] == (3, 0):
        install_requires.append('importlib')

# Conditional importlib dependency for Python 2.6 and 3.0 when creating a wheel distribution.
extras_require = {}
if have_environment_marker_support():
    extras_require[':python_version == "2.6" or python_version == "3.0"'] = ['importlib']


setup(
    name='py2deb',
    version=get_version('py2deb/__init__.py'),
    description='Python to Debian package converter',
    long_description=get_contents('README.rst'),
    url='https://py2deb.readthedocs.org',
    author='Peter Odding & Arjan Verwer (Paylogic International)',
    author_email='peter.odding@paylogic.com',
    packages=find_packages(),
    test_suite='py2deb.tests',
    entry_points={'console_scripts': ['py2deb = py2deb.cli:main']},
    install_requires=install_requires,
    extras_require=extras_require,
    include_package_data=True)
