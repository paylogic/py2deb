#!/usr/bin/env python

# Setup script for py2deb.
#
# Authors:
#  - Arjan Verwer <arjan.verwer@gmail.com>
#  - Peter Odding <peter@peterodding.com>
# Last Change: November 1, 2013
# URL: https://github.com/paylogic/py2deb
#
# Please note that py2deb bundles two copies of stdeb (see `stdeb.py').

import re
from os.path import abspath, dirname, join
from setuptools import setup, find_packages

# Find the directory containing the source distribution.
source_directory = dirname(abspath(__file__))

# Find the current version.
module = join(source_directory, 'py2deb', '__init__.py')
for line in open(module, 'r'):
    match = re.match(r'^__version__\s*=\s*["\']([^"\']+)["\']$', line)
    if match:
        version_string = match.group(1)
        break
else:
    raise Exception, "Failed to extract version from py2deb/__init__.py!"

# Fill in the long description (for the benefit of PyPi)
# with the contents of README.rst (rendered by GitHub).
readme_text = open(join(source_directory, 'README.rst'), 'r').read()

# Fill in the "install_requires" field based on requirements.txt.
requirements = [l.strip() for l in open(join(source_directory, 'requirements.txt'), 'r') if not l.startswith('#')]

setup(name='py2deb',
      version=version_string,
      description='Converts Python packages to Debian packages (including dependencies)',
      long_description=readme_text,
      author='Arjan Verwer & Peter Odding',
      author_email='arjan.verwer@gmail.com, peter.odding@paylogic.eu',
      url='https://github.com/paylogic/py2deb',
      packages=find_packages(),
      py_modules=['stdeb'],
      package_data={'py2deb': ['config/*.ini']},
      install_requires=requirements,
      entry_points={'console_scripts': ['py2deb = py2deb:main']})
