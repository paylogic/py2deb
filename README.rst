The Python to Debian package converter
======================================

The Python to Debian package converter, also known as Py2Deb, is exactly what the name implies:
A program that converts Python packages to Debian packages.
It is the result of an internship assignment at Paylogic.

Why was it build?
-----------------
Paylogic uses Python and deploying/updating the software infrastructure relied on the availability of third parties.
In order to be able to deploy without relying on the availability of third parties, there was a need to find an alternative.
There were several possibilities, but in the end the choice was made to use the Debian packaging system.

A trivial repository was made for internal use, but packages still needed to be converted.
Doing it manually was too much work, so we looked into tools to do it for us.
The tool we found, `stdeb <https://github.com/astraw/stdeb>`_, did most of the steps for converting a package.
However, for internal use, we found several limitations:

- (Automatic) installation of build-dependencies
- Adding prefixes to the package names (To prevent conflicts with existing packages in the official repositories)
- Building/converting in batches
- Being able to choose dependencies

By combining our own requirements with pip-accel and stdeb, Py2Deb was born.

How to install it?
------------------

Download the source and run (as root or in a virtual environment)::

  python setup.py install

How does it work?
-----------------

The py2deb program is a wrapper for pip / pip-accel. For example, if you would
run ``pip-accel coloredlogs -r other_packages.txt`` to install several
packages, you can do ``py2deb coloredlogs -r other_packages.txt`` to convert
those same packages to Debian packages.

For the steps it takes to generate Debian packages you can read the source code
and/or look at ``workflow/workflow.png``

Nice to know
------------

stdeb
  The PyPI version of stdeb (0.6.0) relies on ``py_support``, which is deprecated. The source from their github (0.6.0+git) relies on ``dh_python2``.
  If you use ``Ubuntu 10.04 LTS`` you will not have access to ``dh_python2`` because ``dh_python2`` is included in ``python-all (2.6.5-1)``, while
  ``Ubuntu 10.04 LTS`` uses ``python-all (2.6.5-0)``. If your system has ``dh_python2``, it is recommended to get the source of `stdeb <https://github.com/astraw/stdeb>`_
  and install that instead.
MySQL-python
  This package depends on ``libmysqlclient-dev``, not only while building, but also when pip extracts the source.
  So if you need to convert this package make sure you have ``libmysqlclient-dev`` installed!
fabric/paramiko
  Fabric bundles paramiko. But paramiko is a package on itself too. Using pip you will not notice any problems if you install both,
  but if you converted both packages to debian packages and try to install those, both packages will try to install paramiko.
  This results in an installation failing, because the files or paramiko are already there. The default config of Py2Deb solves this
  by removing the paramiko folder from fabric and letting it depend on paramiko.
setuptools/distribute
  If a python package depends on setuptools, pip will download distribute. When converting, the dependency stays on setuptools,
  This package might not exist (depending on your prefix) and can result in a broken dependency.
  The default configuration of Py2Deb solves this by replacing the dependencies with the ubuntu package ``python-setuptools``.
