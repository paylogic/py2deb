py2deb: Python to Debian package converter
==========================================

.. image:: https://travis-ci.org/paylogic/py2deb.svg?branch=master
   :target: https://travis-ci.org/paylogic/py2deb

.. image:: https://coveralls.io/repos/paylogic/py2deb/badge.svg?branch=master
   :target: https://coveralls.io/r/paylogic/py2deb?branch=master

The Python package `py2deb` converts Python source distributions to Debian
binary packages (the ones used for installation). It uses pip-accel_ to
download, unpack and compile Python packages. Because of this `py2deb` is
compatible with the command line interface of the ``pip install`` command. For
example you can specify packages to convert as command line arguments but you
can also use `requirement files`_ if you want.

During the conversion process dependencies are automatically taken into account
and converted as well so you don't actually have to use requirement files
including transitive dependencies. In fact you might prefer not explicitly
listing your transitive dependencies in requirement files because `py2deb` will
translate the version constraints of Python packages into Debian package
relationships.

The `py2deb` package is currently tested on Python 2.6, 2.7, 3.4, 3.5 and 3.6
(although Python 3.x support isn't being used extensively yet, so you may run
into some sharp edges). For usage instructions please refer to the
documentation `hosted on Read The Docs`_.

.. contents:: :local:

Installation
------------

The `py2deb` package is available on PyPI_, so installation is very simple:

.. code-block:: sh

   $ pip install py2deb

There are some system dependencies which you have to install as well:

.. code-block:: sh

   $ sudo apt-get install dpkg-dev fakeroot

Optionally you can also install Lintian_ (which is not a hard dependency but
more of a "nice to have"):

.. code-block:: sh

   $ sudo apt-get install lintian

When Lintian is installed it will be run automatically to sanity check
converted packages. This slows down the conversion process somewhat but can be
very useful, especially when working on py2deb itself. Currently py2deb doesn't
fail when Lintian reports errors, this is due to the unorthodox ways in which
py2deb can be used. This may change in the future as py2deb becomes more
mature.

Usage
-----

There are two ways to use the `py2deb` package: As the command line program
``py2deb`` and as a Python API. For details about the Python API please refer
to the API documentation `hosted on Read the Docs`_. The command line interface
is described below.

Command line
~~~~~~~~~~~~

.. A DRY solution to avoid duplication of the `py2deb --help' text:
..
.. [[[cog
.. from humanfriendly.usage import inject_usage
.. inject_usage('py2deb.cli')
.. ]]]

**Usage:** `py2deb [OPTIONS] ...`

Convert Python packages to Debian packages according to the given command line options (see below). The command line arguments are the same as accepted by the "pip install" command because py2deb invokes pip during the conversion process. This means you can name the package(s) to convert on the command line but you can also use "requirement files" if you prefer.

If you want to pass command line options to pip (e.g. because you want to use a custom index URL or a requirements file) then you will need to tell py2deb where the options for py2deb stop and the options for pip begin. In such cases you can use the following syntax:

.. code-block:: sh

  $ py2deb -r /tmp -- -r requirements.txt

So the "--" marker separates the py2deb options from the pip options.

**Supported options:**

.. csv-table::
   :header: Option, Description
   :widths: 30, 70


   "``-c``, ``--config=FILENAME``","Load a configuration file. Because the command line arguments are processed
   in the given order, you have the choice and responsibility to decide if
   command line options override configuration file options or vice versa.
   Refer to the documentation for details on the configuration file format.
   
   The default configuration files /etc/py2deb.ini and ~/.py2deb.ini are
   automatically loaded if they exist. This happens before environment
   variables and command line options are processed.
   
   Can also be set using the environment variable ``$PY2DEB_CONFIG``."
   "``-r``, ``--repository=DIRECTORY``","Change the directory where \*.deb archives are stored. Defaults to
   the system wide temporary directory (which is usually /tmp). If
   this directory doesn't exist py2deb refuses to run.
   
   Can also be set using the environment variable ``$PY2DEB_REPOSITORY``."
   "``--use-system-package=PYTHON_PACKAGE_NAME,DEBIAN_PACKAGE_NAME``","Exclude a Python package (the name before the comma) from conversion and
   replace references to the Python package with a specific Debian package
   name. This allows you to use system packages for specific Python
   requirements."
   ``--name-prefix=PREFIX``,"Set the name prefix used during the name conversion from Python to
   Debian packages. Defaults to ""python"". The name prefix and package
   names are always delimited by a dash.
   
   Can also be set using the environment variable ``$PY2DEB_NAME_PREFIX``."
   ``--no-name-prefix=PYTHON_PACKAGE_NAME``,"Exclude a Python package from having the name prefix applied
   during the package name conversion. This is useful to avoid
   awkward repetitions."
   "``--rename=PYTHON_PACKAGE_NAME,DEBIAN_PACKAGE_NAME``","Override the package name conversion algorithm for the given pair
   of package names. Useful if you don't agree with the algorithm :-)"
   ``--install-prefix=DIRECTORY``,"Override the default system wide installation prefix. By setting
   this to anything other than ""/usr"" or ""/usr/local"" you change the
   way py2deb works. It will build packages with a file system layout
   similar to a Python virtual environment, except there will not be
   a Python executable: The packages are meant to be loaded by
   modifying Python's module search path. Refer to the documentation
   for details.
   
   Can also be set using the environment variable ``$PY2DEB_INSTALL_PREFIX``."
   "``--install-alternative=LINK,PATH``","Use Debian's ""update-alternatives"" system to add an executable
   that's installed in a custom installation prefix (see above) to
   the system wide executable search path. Refer to the documentation
   for details."
   ``--python-callback=EXPRESSION``,"Set a Python callback to be called during the conversion process. Refer to
   the documentation for details about the use of this feature and the syntax
   of ``EXPRESSION``.
   
   Can also be set using the environment variable ``$PY2DEB_CALLBACK``."
   ``--report-dependencies=FILENAME``,"Add the Debian relationships needed to depend on the converted
   package(s) to the given control file. If the control file already
   contains relationships the additional relationships will be added
   to the control file; they won't overwrite existing relationships."
   "``-y``, ``--yes``","Instruct pip-accel to automatically install build time dependencies
   where possible. Refer to the pip-accel documentation for details.
   
   Can also be set using the environment variable ``$PY2DEB_AUTO_INSTALL``."
   "``-v``, ``--verbose``",Make more noise :-).
   "``-h``, ``--help``","Show this message and exit.
   "

.. [[[end]]]

Future improvements
-------------------

Some random ideas for possible improvements to py2deb (in no specific order):

- Find a way to facilitate (explicit / opt-in) installation of system wide
  files (not related to Python per se) based on a Python distribution? This
  could significantly reduce the need for "wrapper packages" that basically
  just pull in packages converted by py2deb and drop a few configuration files
  into place.

- Investigate the feasability of supporting conversion of binary wheels. Slowly
  but surely the Python community seems to be gravitating towards (binary)
  wheels and once gravity has shifted we don't want to be left in the dust! ;-)

- Make it possible to "replace" Python requirements in a requirement set with a
  Debian package that's included in the official repositories (e.g. Pillow_
  becomes python-imaging_ or python-pil_). There are some hairy details
  involved here.

- Dive into PEP-440_ and see if there is a way to fully support it? Then `this
  question on Reddit`_ can finally get a satisfying answer :-).

Similar projects
----------------

There are several projects out there that share similarities with py2deb, for
example I know of stdeb_, dh-virtualenv_ and fpm_. The documentation includes a
fairly `detailed comparison`_ with each of these projects.

Contact
-------

If you have questions, bug reports, suggestions, etc. please create an issue on
the `GitHub project page`_. The latest version of `py2deb` will always be
available on GitHub. The internal API documentation is `hosted on Read The
Docs`_.

License
-------

This software is licensed under the `MIT license`_.

© 2017 Peter Odding, Arjan Verwer and Paylogic International.

.. External references:
.. _deb-pkg-tools: https://pypi.python.org/pypi/deb-pkg-tools
.. _detailed comparison: https://py2deb.readthedocs.io/en/latest/comparisons.html
.. _dh-virtualenv: https://github.com/spotify/dh-virtualenv
.. _fpm: https://github.com/jordansissel/fpm
.. _GitHub project page: https://github.com/paylogic/py2deb
.. _hosted on Read The Docs: https://py2deb.readthedocs.io
.. _Lintian: http://en.wikipedia.org/wiki/Lintian
.. _MIT license: http://en.wikipedia.org/wiki/MIT_License
.. _PEP-440: https://www.python.org/dev/peps/pep-0440/
.. _Pillow: https://python-pillow.github.io/
.. _pip-accel: https://github.com/paylogic/pip-accel
.. _PyPI: https://pypi.python.org/pypi/py2deb
.. _python-imaging: https://packages.debian.org/search?keywords=python-imaging
.. _python-pil: https://packages.debian.org/search?keywords=python-pil
.. _requirement files: http://www.pip-installer.org/en/latest/cookbook.html#requirements-files
.. _stdeb: https://pypi.python.org/pypi/stdeb
.. _this question on Reddit: https://www.reddit.com/r/Python/comments/2x7s17/py2deb_python_to_debian_package_converter/coxyyzu
