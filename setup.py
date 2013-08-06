#!/usr/bin/env python

# XXX py2deb bundles two copies of stdeb, please refer to the file `stdeb.py'.

from setuptools import setup, find_packages

setup(name='py2deb',
      version='0.7.2',
      description='Converts Python packages to Debian packages (including dependencies).',
      author='Arjan Verwer',
      author_email='arjan.verwer@paylogic.eu',
      url='https://wiki.paylogic.eu/',
      packages=find_packages(),
      py_modules=['stdeb'],
      package_data={'py2deb': ['config/*.ini']},
      install_requires=[
          # Direct dependencies of py2deb.
          'coloredlogs >= 0.4.6',
          'humanfriendly >= 1.5',
          'pip-accel >= 0.9.13',
          'deb-pkg-tools >= 1.0.3',
          # Provides the debian.deb822 module. A direct dependency of py2deb.
          # Ideally we should be able to use the version provided by the
          # upstream Ubuntu package, but I failed to get this working. The
          # problem seems to be that the Ubuntu package has version "0.1.21ubuntu1"
          # which the constraints "python-debian >= 0.1.21, < 0.1.22" don't match;
          # I keep getting the following runtime error message:
          #
          #   pkg_resources.DistributionNotFound: python-debian>=0.1.21,<0.1.22
          #
          # A logical OR in the constraints would solve this but apparently the
          # Python requirement specifications don't support that. See
          # http://www.python.org/dev/peps/pep-0440/. For now I've removed the
          # version constraints, which solves the problem but is not cool.
          'python-debian',
          # Transitive undocumented dependency of `python-debian'.
          'chardet',
      ],
      entry_points={'console_scripts': ['py2deb = py2deb:main']},
      test_suite='py2deb.tests')
