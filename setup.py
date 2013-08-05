#!/usr/bin/env python

# XXX py2deb bundles two copies of stdeb, please refer to the file `stdeb.py'.

from setuptools import setup, find_packages

setup(name='py2deb',
      version='0.7.1',
      description='Converts Python packages to Debian packages (including dependencies).',
      author='Arjan Verwer',
      author_email='arjan.verwer@paylogic.eu',
      url='https://wiki.paylogic.eu/',
      packages=find_packages(),
      py_modules=['stdeb'],
      package_data={'py2deb': ['config/*.ini']},
      install_requires=[
          # Direct dependencies of py2deb.
          'coloredlogs == 0.4.3',
          'humanfriendly == 1.5',
          'pip-accel == 0.9.12',
          'deb-pkg-tools == 1.0',
          # Provides the debian.deb822 module. A direct dependency of py2deb.
          # These version constraints specifically allow for version 0.1.21
          # (available on PyPI) and version 0.1.21ubuntu1 (available in Ubuntu
          # 12.04).
          'python-debian >= 0.1.21, < 0.1.22',
          # Transitive undocumented dependency of `python-debian'.
          'chardet',
      ],
      entry_points={'console_scripts': ['py2deb = py2deb:main']},
      test_suite='py2deb.tests')
