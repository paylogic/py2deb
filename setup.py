#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='pl-py2deb',
      version='0.6.8',
      description='Converts Python packages to Debian packages (including dependencies).',
      author='Arjan Verwer',
      author_email='arjan.verwer@paylogic.eu',
      url='https://wiki.paylogic.eu/',
      packages=find_packages(),
      package_data={'py2deb': ['config/*.ini']},
      install_requires=[
          'python-debian >= 0.1.21', # proper dependency
          'stdeb', # proper dependency
          'chardet', # transitive dependency of `python-debian'... (no one gets dependencies right :-)
          'pip-accel >= 0.9.6', # proper dependency
          'coloredlogs', # proper dependency
      ],
      entry_points={'console_scripts': ['pl-py2deb = py2deb:main']})
