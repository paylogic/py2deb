py2deb: Python to Debian package converter
==========================================

The Python package `py2deb` converts Python source distributions to Debian
packages. It uses pip-accel_ to download, unpack and compile Python packages.
Because of this `py2deb` is compatible with the command line interface of the
``pip install`` command. For example you can specify packages to convert as
command line arguments but you can also use `requirement files`_ if you want.

During the conversion process dependencies are automatically taken into account
and converted as well so you don't actually have to use requirement files
including transitive dependencies. In fact you might prefer not explicitly
listing your transitive dependencies in requirement files because `py2deb` will
translate the version constraints of Python packages into Debian package
relationships.

The `py2deb` package is currently tested on Python 2.6, 2.7 and 3.4. For usage
instructions please refer to the documentation `hosted on Read The Docs`_.

Installation
------------

The `py2deb` package is available on PyPI_, so installation is very simple:

.. code-block:: sh

   $ pip install py2deb

There are some system dependencies which you have to install as well:

.. code-block:: sh

   $ sudo apt-get install dpkg-dev fakeroot lintian

Usage
-----

**Usage:** `py2deb [OPTIONS] ...`

Convert Python packages to Debian packages according to the given command line
options (see below). The positional arguments are the same arguments accepted
by the ``pip install`` command, that means you can name the package(s) to
convert on the command line but you can also use `requirement files`_ if you
prefer.

Sometimes you will need to disambiguate between the options for `py2deb` and
the options for `pip`, for example the short option ``-r`` means
``--repository`` to `py2deb` and ``--requirement`` to `pip`. In such cases you
can use the following syntax:

.. code-block:: sh

   $ py2deb -r /tmp -- -r requirements.txt

So the ``--`` marker separates the `py2deb` options from the `pip` options.

**Supported options:**

  :option:`-c, --config=FILENAME`

    Load a configuration file. Because the command line arguments are processed
    in the given order, you have the choice and responsibility to decide if
    command line options override configuration file options or vice versa.
    Refer to the documentation for details on the configuration file format.

  :option:`-r, --repository=DIRECTORY`

    Change the directory where ``*.deb`` archives are stored. Defaults to the
    system wide temporary directory (which is usually ``/tmp``). If this
    directory doesn't exist `py2deb` refuses to run.

  :option:`--name-prefix=PREFIX`

    Set the name prefix used during the name conversion from Python to Debian
    packages. Defaults to ``python``. The name prefix and package names are
    always delimited by a dash.

  :option:`--no-name-prefix=PYTHON_PACKAGE_NAME`

    Exclude a Python package from having the name prefix applied during the
    package name conversion. This is useful to avoid awkward repetitions.

  :option:`--rename=PYTHON_PACKAGE_NAME,DEBIAN_PACKAGE_NAME`

    Override the package name conversion algorithm for the given pair of
    package names. Useful if you don't agree with the algorithm :-)

  :option:`--install-prefix=DIRECTORY`

    Override the default system wide installation prefix. By setting this to
    anything other than ``/usr`` or ``/usr/local`` you change the way `py2deb`
    works. It will build packages with a file system layout similar to a Python
    virtual environment, except there will not be a Python executable: The
    packages are meant to be loaded by modifying Python's module search path.
    Refer to the documentation for details.

  :option:`--install-alternative=LINK,PATH`

    Use Debian's ``update-alternatives`` system to add an executable that's
    installed in a custom installation prefix (see above) to the system wide
    executable search path. Refer to the documentation for details.

  :option:`--report-dependencies=FILENAME`

    Add the Debian relationships needed to depend on the converted package(s)
    to the given control file. If the control file already contains
    relationships the additional relationships will be added to the control
    file; they won't overwrite existing relationships.

  :option:`-y, --yes`

    Instruct pip-accel_ to automatically install build time dependencies where
    possible. Refer to the pip-accel documentation for details.

  :option:`-v, --verbose`

    Make more noise :-).

  :option:`-h, --help`

    Show this message and exit.

Contact
-------

If you have questions, bug reports, suggestions, etc. please create an issue on
the `GitHub project page`_. The latest version of `py2deb` will always be
available on GitHub. The internal API documentation is `hosted on Read The
Docs`_.

License
-------

This software is licensed under the `MIT license`_.

© 2014 Peter Odding, Arjan Verwer and Paylogic International.

.. External references:
.. _GitHub project page: https://github.com/paylogic/py2deb
.. _hosted on Read The Docs: https://py2deb.readthedocs.org
.. _MIT license: http://en.wikipedia.org/wiki/MIT_License
.. _pip-accel: https://github.com/paylogic/pip-accel
.. _PyPI: https://pypi.python.org/pypi/py2deb
.. _requirement files: http://www.pip-installer.org/en/latest/cookbook.html#requirements-files
