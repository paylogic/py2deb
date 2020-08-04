#!/usr/bin/env python

# Setup script for the `py2deb' package.

# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: August 4, 2020
# URL: https://py2deb.readthedocs.io

"""
Setup script for the `py2deb` package.

**python setup.py install**
  Install from the working directory into the current Python environment.

**python setup.py sdist**
  Build a source distribution archive.

**python setup.py bdist_wheel**
  Build a wheel distribution archive.
"""

# Standard library modules.
import codecs
import os
import re
import sys

# De-facto standard solution for Python packaging.
from setuptools import find_packages, setup


def get_contents(*args):
    """Get the contents of a file relative to the source distribution directory."""
    with codecs.open(get_absolute_path(*args), 'r', 'UTF-8') as handle:
        return handle.read()


def get_version(*args):
    """Extract the version number from a Python module."""
    contents = get_contents(*args)
    metadata = dict(re.findall('__([a-z]+)__ = [\'"]([^\'"]+)', contents))
    return metadata['version']


def get_install_requires():
    """Get the conditional dependencies for source distributions."""
    install_requires = get_requirements('requirements.txt')
    if 'bdist_wheel' not in sys.argv:
        if sys.version_info[:2] <= (2, 6) or sys.version_info[:2] == (3, 0):
            install_requires.append('importlib')
    return sorted(install_requires)


def get_extras_require():
    """Get the conditional dependencies for wheel distributions."""
    extras_require = {}
    if have_environment_marker_support():
        expression = ':python_version == "2.6" or python_version == "3.0"'
        extras_require[expression] = ['importlib']
    return extras_require


def get_absolute_path(*args):
    """Transform relative pathnames into absolute pathnames."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), *args)


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


setup(
    name='py2deb',
    version=get_version('py2deb', '__init__.py'),
    description="Python to Debian package converter",
    long_description=get_contents('README.rst'),
    url='https://py2deb.readthedocs.io',
    author="Peter Odding & Arjan Verwer (Paylogic International)",
    author_email='peter.odding@paylogic.com',
    license='MIT',
    packages=find_packages(),
    entry_points=dict(console_scripts=[
        'py2deb = py2deb.cli:main',
    ]),
    install_requires=get_install_requires(),
    extras_require=get_extras_require(),
    test_suite='py2deb.tests',
    include_package_data=True,
    python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Archiving :: Packaging',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ])
