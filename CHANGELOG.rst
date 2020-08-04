Changelog
=========

The purpose of this document is to list all of the notable changes to this
project. The format was inspired by `Keep a Changelog`_. This project adheres
to `semantic versioning`_.

.. contents::
   :local:

.. _Keep a Changelog: http://keepachangelog.com/
.. _semantic versioning: http://semver.org/

`Release 5.0`_ (2020-08-05)
---------------------------

- Added support for :mod:`pkgutil` style namespace packages. This should be
  considered experimental because it hasn't seen any real world use yet.

- Explicitly documented Python compatibility in the readme (see also `#17`_,
  `#18`_, `#27`_ and `#31`_) to avoid more issues being reported about Python
  3.8+ not being supported.

.. _Release 5.0: https://github.com/paylogic/py2deb/compare/4.0...5.0
.. _#17: https://github.com/paylogic/py2deb/issues/17
.. _#18: https://github.com/paylogic/py2deb/issues/18
.. _#27: https://github.com/paylogic/py2deb/issues/27
.. _#31: https://github.com/paylogic/py2deb/issues/31

`Release 4.0`_ (2020-08-04)
---------------------------

.. note:: While I don't consider this a major release feature wise, the
          major version number was bumped because this change is backwards
          incompatible (although clearly an improvement).

Merged pull request `#22`_ to stop :pypi:`py2deb` from normalizing "local
version labels" as defined by `PEP 440`_. One important thing to note is that
the "Debian revision" safe guard is applied after the "local version label" is
restored, which means the "local version label" may not be the final part of
the generated Debian version string.

.. _Release 4.0: https://github.com/paylogic/py2deb/compare/3.2...4.0
.. _#22: https://github.com/paylogic/py2deb/pull/22
.. _PEP 440: https://www.python.org/dev/peps/pep-0440/

`Release 3.2`_ (2020-08-04)
---------------------------

Merged pull request `#25`_ which adds support for the ``$DEBFULLNAME`` and
``$DEBEMAIL`` environment variables to override package maintainer metadata.

.. _Release 3.2: https://github.com/paylogic/py2deb/compare/3.1...3.2
.. _#25: https://github.com/paylogic/py2deb/pull/25

`Release 3.1`_ (2020-08-04)
---------------------------

Merged pull request `#20`_ which adds a ``Provides`` Debian control field for
converted packages that have "extras" encoded in their name.

One caveat to point out: ``Provides`` is a second-class citizen in the Debian
packaging ecosystem in the sense that it satisfies only *unversioned*
relationships.

Nevertheless this may prove useful, so it was merged 🙂.

.. _Release 3.1: https://github.com/paylogic/py2deb/compare/3.0.1...3.1
.. _#20: https://github.com/paylogic/py2deb/pull/20

`Release 3.0.1`_ (2020-08-04)
-----------------------------

`Release 3.0`_ was yanked from PyPI just minutes after uploading, because I
forgot to include a ``python_requires`` definition in the ``setup.py`` script,
which means Python 2.6 and 3.4 installations could end up downloading
incompatible :pypi:`py2deb` releases. This has since been added.

.. _Release 3.0.1: https://github.com/paylogic/py2deb/compare/3.0...3.0.1

`Release 3.0`_ (2020-08-04)
---------------------------

.. note:: While I don't consider this a major release feature wise, the major
          version number was bumped because of the compatibility changes
          (dropping 2.6 and 3.4).

**Updated compatibility:**

- PyPy 3 is now officially supported (and tested on Travis CI). This was
  triggered by pull requests `#29`_ and `#30`_.

- Python 2.6 and 3.4 are no longer supported (nor tested on Travis CI)
  following the same change in my other 20+ open source Python projects
  (some of which are requirements of :pypi:`py2deb`).

**Project maintenance:**

- Spent several days stabilizing the test suite on Travis CI, to avoid finding
  myself in a situation where I'm releasing new features without the safety net
  provided by a test suite that runs automatically and shouts loudly when
  breakage is found 😇.

- Spent several days getting PyPy 3 testing to work on Travis CI, due to fatal
  incompatibilities between the most recent release of :pypi:`pip` and PyPy 3.
  For more then you ever wanted to know consult `these commits`_ and the
  related Travis CI build failures (some of which are linked in commit
  messages).

- Updated some imports to be compatible with :pypi:`humanfriendly` 8.0.

**Miscellaneous changes:**

- Merged pull request `#21`_ which fixes a typo in the hooks module.

.. _Release 3.0: https://github.com/paylogic/py2deb/compare/2.3...3.0
.. _#29: https://github.com/paylogic/py2deb/pull/29
.. _#30: https://github.com/paylogic/py2deb/pull/30
.. _#21: https://github.com/paylogic/py2deb/pull/21
.. _these commits: https://github.com/paylogic/py2deb/compare/4ab626b6582...affa7158560

`Release 2.3`_ (2020-07-28)
---------------------------

Merged pull request `#30`_:

- Added support ``pypy3`` in replacement hashbangs.
- Added support for ``pypy3`` package name prefix.

.. _Release 2.3: https://github.com/paylogic/py2deb/compare/2.2...2.3
.. _#30: https://github.com/paylogic/py2deb/pull/30

`Release 2.2`_ (2020-07-28)
---------------------------

Addded support for ``pypy3`` hashbangs via pull request `#29`_.

.. _Release 2.2: https://github.com/paylogic/py2deb/compare/2.1.1...2.2
.. _#29: https://github.com/paylogic/py2deb/pull/29

`Release 2.1.1`_ (2020-05-26)
-----------------------------

**Defensively pin pip-accel requirement.**

I intend to revive pip-accel_ based on the latest pip_ release, offering a
minimal conceptual subset of previous functionality of pip-accel_, just enough
for py2deb to use for downloading and unpacking distribution archives.

However this will surely take some time to flesh out - possibly multiple
releases of both projects. I'm not even sure yet what will be involved in
getting pip-accel and py2deb running on the latest version of pip (I can
however already tell that large architectural changes will be required in
pip-accel and consequently also py2deb).

In the mean time I don't want any users (including my employer) run into
breakage caused by this endeavor. Alpha / beta releases on PyPI should be able
to avoid this problem, however I've never published those myself, so I'm opting
for "defense in depth" 😇.

.. _Release 2.1.1: https://github.com/paylogic/py2deb/compare/2.1...2.1.1

`Release 2.1`_ (2018-12-16)
---------------------------

Enable optional backwards compatibility with the old version number conversion
up to `release 0.25`_ in which pre-release identifiers didn't receive any
special treatment.

My reason for adding this backwards compatibility now is that it will allow me
to upgrade py2deb on the build server of my employer to the latest version
without being forced to switch to the new version number format at the same
time. This simplifies the transition significantly.

.. _Release 2.1: https://github.com/paylogic/py2deb/compare/2.0...2.1

`Release 2.0`_ (2018-11-18)
---------------------------

**New features:**

- Added support for Python 3.7 🎉 (configured `Travis CI`_ to run the test
  suite on Python 3.7 and updated the project metadata and documentation).

- Added support for PyPy_ 🎉 (configured `Travis CI`_ to run the test suite on
  PyPy, changed the test suite to accommodate PyPy, fixed several
  incompatibilities in the code base, updated the project metadata and
  documentation).

- Make it possible for callers to change Lintian_ overrides embedded in
  the generated binary packages. Also, update the default overrides.

**Bug fixes:**

- Make the default name prefix conditional on the Python version that's running
  py2deb (this is **backwards incompatible** although clearly the correct
  behavior):

  - On PyPy_ the default name prefix is now ``pypy``.
  - On Python 2 the default name prefix is still ``python``.
  - On Python 3 the default name prefix is now ``python3``.

  The old behavior of using the ``python`` name prefix on Python 3 and PyPy_
  was definitely wrong and quite likely could lead to serious breakage, but
  even so this change is of course backwards incompatible.

- Don't raise an exception from ``transform_version()`` when a partial
  requirement set is converted using pip's ``--no-deps`` command line option
  (this is a valid use case that should be supported).

**Documentation changes:**

- Added this changelog 🎉. The contents were generated by a Python script that
  collects tags and commit messages from the git repository. I manually
  summarized and converted the output to reStructuredText format (which was a
  whole lot work 😛).

- Changed the theme of the documentation from ``classic`` to ``nature``. The
  classic theme is heavily customized by Read the Docs whereas the nature theme
  more closely matches what is rendered locally by Sphinx versus what is
  rendered 'remotely' on Read the Docs.

- Changed the location of the intersphinx mapping for setuptools (it now uses
  Read the Docs).

**Internal improvements:**

- Move the finding of shared object files and the dpkg-shlibdeps_ integration
  to deb-pkg-tools_ (strictly speaking this is backwards incompatible). This
  functionality originated in py2deb but since then I'd wanted to reuse it
  outside of py2deb several times and so I eventually reimplemented it in
  deb-pkg-tools_. Switching to that implementation now made sense (in order to
  reduce code duplication and simplify the py2deb code base). Strictly speaking
  this is backwards incompatible because methods have been removed but this
  only affects those who extend ``PackageToConvert`` which I don't expect
  anyone to have actually done 🙂.

- Switched from cached-property_ to property-manager_. The py2deb project comes
  from a time (2013) when Python descriptors were still magic to me and so I
  chose to use cached-property_. However since then I created the
  property-manager_ project (2015). At this point in time (2018) several of the
  dependencies of py2deb (other projects of mine) already use property-manager_
  and the integration of property-manager_ in py2deb can help to improve the
  project, so this seemed like the logical choice 😇.

.. _Release 2.0: https://github.com/paylogic/py2deb/compare/1.1...2.0
.. _dpkg-shlibdeps: https://manpages.debian.org/dpkg-shlibdeps
.. _cached-property: https://pypi.org/project/cached-property
.. _property-manager: https://pypi.org/project/property-manager
.. _PyPy: https://en.wikipedia.org/wiki/PyPy
.. _Lintian: https://en.wikipedia.org/wiki/Lintian

`Release 1.1`_ (2018-02-24)
---------------------------

- Add support for conditional dependencies via environment markers.
- Include the documentation in source distributions (the ``*.tar.gz`` files).

.. _Release 1.1: https://github.com/paylogic/py2deb/compare/1.0...1.1

`Release 1.0`_ (2017-08-08)
---------------------------

- Fixed issue `#8`_: Support PEP 440 pre-release versions.

- Document Python 3.6 support, configure `Travis CI`_ to test Python 3.6.

- Merged pull request `#11`_: Update comparison with fpm_ to remove invalid
  statement about the lack of support for converting multiple packages at once.

Since `release 0.25`_ I've only made bug fixes (i.e. no features were added)
however the change related to `#8`_ is backwards incompatible, which is why
I've decided to bump the major version number.

.. _Release 1.0: https://github.com/paylogic/py2deb/compare/0.25...1.0
.. _#8: https://github.com/paylogic/py2deb/issues/8
.. _#11: https://github.com/paylogic/py2deb/pull/11

`Release 0.25`_ (2017-05-23)
----------------------------

Make it possible to "replace" specific Python packages (installation
requirements) with a user defined system package using the new command line
option ``--use-system-package=PYTHON_PACKAGE_NAME,DEBIAN_PACKAGE_NAME``.

The package ``PYTHON_PACKAGE_NAME`` will be excluded from the convertion
process. Converted packages that depended on ``PYTHON_PACKAGE_NAME`` will have
their dependencies updated to refer to ``DEBIAN_PACKAGE_NAME`` instead.

.. _Release 0.25: https://github.com/paylogic/py2deb/compare/0.24.4...0.25

`Release 0.24.4`_ (2017-01-17)
------------------------------

- Fixed a bug in ``py2deb.utils.embed_install_prefix()`` (reported in issue
  `#9`_ and fixed in pull request `#10`_) that accidentally truncated binary
  executables when using a custom installation prefix.

- Fixed a broken import in the documentation (reported in issue `#6`_).

- Added Python 3.5 to versions tested on `Travis CI`_ (but don't look
  at the build logs just yet, for example Lintian complains with
  ``python-module-in-wrong-location``, to be investigated if and
  how this can be 'improved').

- Improved ``docs/conf.py`` and added ``humanfriendly.sphinx`` usage.

- Refactored setup script (added docstring and classifiers) and ``Makefile``
  and related files.

.. _Release 0.24.4: https://github.com/paylogic/py2deb/compare/0.24.3...0.24.4
.. _#6: https://github.com/paylogic/py2deb/issues/6
.. _#9: https://github.com/paylogic/py2deb/issues/9
.. _#10: https://github.com/paylogic/py2deb/pull/10

`Release 0.24.3`_ (2016-04-15)
------------------------------

Refactor ``setup.py`` script, improving Python 3 support:

- Counteract a possible ``UnicodeDecodeError`` when ``setup.py`` loads
  ``README.rst`` to populate the ``long_description`` field.

- Could have fixed this with a two line diff, but noticed some other things I
  wanted to improve, so here we are 🙂.

.. _Release 0.24.3: https://github.com/paylogic/py2deb/compare/0.24.2...0.24.3

`Release 0.24.2`_ (2016-01-19)
------------------------------

Bug fix: Restore compatibility with latest coloredlogs (fixes `#4`_).

.. _Release 0.24.2: https://github.com/paylogic/py2deb/compare/0.24.1...0.24.2
.. _#4: https://github.com/paylogic/py2deb/issues/4

`Release 0.24.1`_ (2015-09-24)
------------------------------

Bug fix to restore Python 3 compatibility (``execfile()`` versus ``exec``).

.. _Release 0.24.1: https://github.com/paylogic/py2deb/compare/0.24...0.24.1

`Release 0.24`_ (2015-09-24)
----------------------------

Added support for Python callbacks that enable arbitrary manipulation during
packaging.

.. _Release 0.24: https://github.com/paylogic/py2deb/compare/0.23.2...0.24

`Release 0.23.2`_ (2015-09-04)
------------------------------

- Strip trailing zeros in required versions when necessary (improves compatibility with pip_).
- Document ideas for future improvements.

.. _Release 0.23.2: https://github.com/paylogic/py2deb/compare/0.23.1...0.23.2

`Release 0.23.1`_ (2015-06-28)
------------------------------

Moved usage message munging to humanfriendly_ package.

.. _Release 0.23.1: https://github.com/paylogic/py2deb/compare/0.23...0.23.1

`Release 0.23`_ (2015-04-22)
----------------------------

Make it possible to disable automatic Lintian checks.

.. _Release 0.23: https://github.com/paylogic/py2deb/compare/0.22...0.23

`Release 0.22`_ (2015-04-12)
----------------------------

- Refactor maintainer scripts into a proper Python module:

  The post-installation and pre-removal scripts that py2deb bundled with
  generated Debian packages were lacking functionality and were not easy to
  extend. I've now refactored these scripts into a Python module with proper
  coding standards (documentation, tests, readable and maintainable code) and
  some additional features:

  - Robust support for `pkg_resources-style namespace packages`_.
  - Smart enough to clean up properly after PEP 3147 (>= Python 3.2).

- Use :func:`executor.quote()` instead of :func:`pipes.quote()`.
- Always clean up temporary directories created by pip_ and pip-accel_.
- Remove redundant temporary directory creation.

.. _Release 0.22: https://github.com/paylogic/py2deb/compare/0.21.1...0.22
.. _pkg_resources-style namespace packages: https://packaging.python.org/guides/packaging-namespace-packages/#pkg-resources-style-namespace-packages

`Release 0.21.1`_ (2015-04-05)
------------------------------

Update usage instructions in readme (and automate the process for the future).

.. _Release 0.21.1: https://github.com/paylogic/py2deb/compare/0.21...0.21.1

`Release 0.21`_ (2015-04-04)
----------------------------

Upgraded dependencies: pip-accel_ 0.25 and pip_ 6.

.. _Release 0.21: https://github.com/paylogic/py2deb/compare/0.20.11...0.21

`Release 0.20.11`_ (2015-03-18)
-------------------------------

Switched to ``deb_pkg_tools.utils.find_debian_architecture()``.

.. _Release 0.20.11: https://github.com/paylogic/py2deb/compare/0.20.10...0.20.11

`Release 0.20.10`_ (2015-03-04)
-------------------------------

Move control field override handling to separate, documented method.

.. _Release 0.20.10: https://github.com/paylogic/py2deb/compare/0.20.9...0.20.10

`Release 0.20.9`_ (2015-03-04)
------------------------------

Normalize package names during stdeb.cfg parsing.

.. _Release 0.20.9: https://github.com/paylogic/py2deb/compare/0.20.8...0.20.9

`Release 0.20.8`_ (2015-03-01)
------------------------------

- Include a detailed comparison to stdeb_, dh-virtualenv_ and fpm_ in the
  documentation (for details see `#1`_).

- Clarify in the readme that py2deb builds *binary* Debian packages and that
  Lintian is an optional dependency.

.. _Release 0.20.8: https://github.com/paylogic/py2deb/compare/0.20.7...0.20.8
.. _dh-virtualenv: https://github.com/spotify/dh-virtualenv
.. _fpm: https://github.com/jordansissel/fpm
.. _#1: https://github.com/paylogic/py2deb/issues/1

`Release 0.20.7`_ (2015-03-01)
------------------------------

This was a "vanity release" that contained no code changes relevant to users:
I'd finally gotten the full test suite to pass on `Travis CI`_ (see issue `#3`_
for details) and I wanted to add badges to the readme 😇.

.. _Release 0.20.7: https://github.com/paylogic/py2deb/compare/0.20.6...0.20.7
.. _#3: https://github.com/paylogic/py2deb/issues/3

`Release 0.20.6`_ (2015-03-01)
------------------------------

Improve ``PackageToConvert.determine_package_architecture()``.

In the previous release I added the ``armv6l`` to ``armhf`` mapping to
``PackageConverter`` and I just noticed that ``PackageToConvert`` didn't
respect this change.

I'm not sure why ``PackageConverter`` and ``PackageToConvert`` both ended up
having separate ways to detect the current Debian architecture (I guess this
was left over from a previous refactoring) but clearly this logic should be
contained in a single place, not spread over multiple places like it was before
this change.

.. _Release 0.20.6: https://github.com/paylogic/py2deb/compare/0.20.5...0.20.6

`Release 0.20.5`_ (2015-02-27)
------------------------------

- Improved Python 3.4 compatibility, also bumped deb-pkg-tools_ requirement to
  improve Python 3 compatibility.

- Replaced the use of ``uname -m`` with ``os.uname()`` and added an ``armv6l``
  to ``armhf`` mapping (to enable support for Raspbian).

- Start running the test suite on `Travis CI`_ against Python 2.6, 2.7 and 3.4
  and collect coverage statistics on Coveralls_.

.. _Release 0.20.5: https://github.com/paylogic/py2deb/compare/0.20.4...0.20.5
.. _Travis CI: https://travis-ci.org/paylogic/py2deb
.. _Coveralls: https://coveralls.io/github/paylogic/py2deb

`Release 0.20.4`_ (2015-02-25)
------------------------------

Give up on conversion of package descriptions using docutils_:

1. It was always just a nice to have.
2. I'm never going to get it working reliably.
3. Right now it adds several "dead weight" dependencies (because the feature
   was disabled in `release 0.18.6`_).
4. This "dead code" was reducing test coverage.

This release was the first release to be published on PyPI.

.. _Release 0.20.4: https://github.com/paylogic/py2deb/compare/0.20.3...0.20.4

`Release 0.20.3`_ (2014-12-09)
------------------------------

Add a log message when the control field overrides file is not found.

.. _Release 0.20.3: https://github.com/paylogic/py2deb/compare/0.20.2...0.20.3

`Release 0.20.2`_ (2014-11-29)
------------------------------

Bug fix: Change initialization order.

.. _Release 0.20.2: https://github.com/paylogic/py2deb/compare/0.20.1...0.20.2

`Release 0.20.1`_ (2014-11-28)
------------------------------

Re-enable auto-install runtime/configuration option.

.. _Release 0.20.1: https://github.com/paylogic/py2deb/compare/0.20...0.20.1

`Release 0.20`_ (2014-11-28)
----------------------------

Upgraded to the newest pip-accel_ (0.19.2).

.. _Release 0.20: https://github.com/paylogic/py2deb/compare/0.19.1...0.20

`Release 0.19.1`_ (2014-11-18)
------------------------------

- Moved ``coerce_to_boolean()`` to humanfriendly_ package.
- Workaround for dependency specifications like ``pytz > dev``.

.. _Release 0.19.1: https://github.com/paylogic/py2deb/compare/0.19...0.19.1
.. _humanfriendly: https://pypi.org/project/humanfriendly

`Release 0.19`_ (2014-11-12)
----------------------------

Load configuration files and environment variables by default (with
an escape hatch should it ever turn out to be problematic 😇).

.. _Release 0.19: https://github.com/paylogic/py2deb/compare/0.18.9...0.19

`Release 0.18.9`_ (2014-11-09)
------------------------------

Upgrade to pip-accel_ 0.14.1.

.. _Release 0.18.9: https://github.com/paylogic/py2deb/compare/0.18.8...0.18.9

`Release 0.18.8`_ (2014-07-23)
------------------------------

Avoid Lintian complaining about ``debian-revision-should-not-be-zero``.

.. _Release 0.18.8: https://github.com/paylogic/py2deb/compare/0.18.7...0.18.8

`Release 0.18.7`_ (2014-07-15)
------------------------------

Bug fix for custom installation prefix embedding in executable scripts.

.. _Release 0.18.7: https://github.com/paylogic/py2deb/compare/0.18.6...0.18.7

`Release 0.18.6`_ (2014-07-15)
------------------------------

Disable package description conversion until I find out what's wrong with it:

- Starting from `release 0.16` pydeb would use docutils_ to convert the
  ``long_description`` of each Python package to HTML which was then translated
  to plain text in order to generate a readme text that was embedded in the
  metadata of the binary package.

- However lots of packages on PyPI (including mine) automatically embed their
  ``README.rst`` as the ``long_description`` in the ``setup.py`` script, making
  for rather complex documents to transform.

- This interaction caused "Unable to parse package file" warnings from
  ``apt-get`` during installation of packages (given input packages with
  complex enough long descriptions).

Given that this was a "nice to have" and I had more important things on my
plate I decided to just disable this feature for now.

.. _Release 0.18.6: https://github.com/paylogic/py2deb/compare/0.18.5...0.18.6
.. _docutils: https://pypi.org/project/docutils

`Release 0.18.5`_ (2014-07-15)
------------------------------

Bug fix: Make sure the "Debian revision" part of converted version numbers
contains a digit.

.. _Release 0.18.5: https://github.com/paylogic/py2deb/compare/0.18.4...0.18.5

`Release 0.18.4`_ (2014-07-15)
------------------------------

Bug fix: Tildes in Debian binary package versions considered harmful!

Because of the special semantics of ``~`` in Debian binary pakcage versions
I've decided to switch from ``~`` to ``-`` as the separator between tokens in
the version string.

About those special semantics::

  $ dpkg --compare-versions '0.21.1~paylogic' '>=' '0.21.1'; echo $?
  1

  $ dpkg --compare-versions '0.21.1~paylogic' '>=' '0.21.1'; echo $?
  1

  $ dpkg --compare-versions '0.21.1-paylogic' '>=' '0.21.1'; echo $?
  0

  $ dpkg --compare-versions '0.21.1-paylogic-0' '>=' '0.21.1'; echo $?
  0

.. _Release 0.18.4: https://github.com/paylogic/py2deb/compare/0.18.3...0.18.4

`Release 0.18.3`_ (2014-07-15)
------------------------------

Bug fix: Cleanup temporary source directories.

These are created when you tell pip_ to install from a directory containing an
unpacked source distribution: pip copies the complete directory to ``/tmp``
before doing anything with it, but because this directory cannot be set using
``--build-directory`` py2deb never cleaned up directories created in this
manner.

.. _Release 0.18.3: https://github.com/paylogic/py2deb/compare/0.18.2...0.18.3

`Release 0.18.2`_ (2014-07-02)
------------------------------

Automatically add the ``Vcs-Hg`` control field when possible.

This works by parsing the ``.hg_archival.txt`` file generated by the ``hg
archive`` command so for now this only supports Python source distributions
exported from Mercurial repositories.

.. _Release 0.18.2: https://github.com/paylogic/py2deb/compare/0.18.1...0.18.2

`Release 0.18.1`_ (2014-06-27)
------------------------------

This release consists of more than 10 commits that were part of an effort to
prepare the py2deb project for open sourcing under the name of Paylogic_.
Here's a short summary:

- Bumped pip-accel_ requirement (to pull in an upstream bug fix) and minor
  changes to be compatible wiht the new version.
- Support for default configuration files (``/etc/py2deb.ini`` and ``~/.py2deb.ini``)
- Don't copy files during builds (performance optimization).
- Add logging in order to debug handling of postinst/prerm scripts.
- Explicitly iterate postinst/prerm scripts (explicit is better than implicit).
- Bug fix: Include postinst/prerm scripts during installation!
- Bug fix: Reformat version strings to comply with Debian policy manual.
- Make ``converter.convert()`` return list of generated package archives.
- Check for duplicate files in converted dependency sets.
- Improved the documentation.

.. _Release 0.18.1: https://github.com/paylogic/py2deb/compare/0.18...0.18.1

`Release 0.18`_ (2014-06-16)
----------------------------

This release consists of about 15 commits that were part of an effort to
prepare the py2deb project for open sourcing under the name of Paylogic_.
Here's a short summary:

- Support for environment variables.
- Make py2deb compatible with Python 3.4.
- Explicitly document that py2deb invokes pip.
- Improve ``PackageToConvert.python_requirements``.
- Improve ``PackageToConvert.debian_dependencies``.
- Rename ``find_package()`` to ``get_package()``.
- Rename ``find_python_version()`` to ``python_version()``.
- Improve ``compact_repeating_words()``.
- Add comparison between py2deb and stdeb_ to readme.
- Bring test coverage up to 92%.

.. _Release 0.18: https://github.com/paylogic/py2deb/compare/0.17...0.18

`Release 0.17`_ (2014-06-07)
----------------------------

This release consists of almost 50 commits that were part of an effort to
prepare the py2deb project for open sourcing under the name of Paylogic_.
Here's a short summary:

- Implemented PEP-8 and PEP-257 compatibility and code style checks.
- Implemented ``--report-dependencies`` option.
- Encode Python requirement 'extras' in Debian package names.
- Document the ``--`` trick in the usage message.
- Document several missing installation requirements.
- Restore compatibility with ``stdeb.cfg`` configuration files (for now there's
  no reason not to use the same file, since the file serves the exact same
  purpose - if and when I need non-compatible behavior I can switch to or add
  ``py2deb.cfg`` support).
- Bug fix: Don't move generated archives if already in target directory.
- Big refactoring: Split main module into several sub modules.
- Significantly improve test coverage.
- Enable Sphinx viewcode extension.

.. _Release 0.17: https://github.com/paylogic/py2deb/compare/0.16...0.17

`Release 0.16`_ (2014-06-05)
----------------------------

Remove the stdeb_ backend and focus fully on the pip-accel_ backend:

- I don't need something that's refined and elegant but only supports a subset
  of packages (stdeb_).
  
  I see stdeb_ as the more idealistic choice.

- What I need instead is something that supports all or most packages, and when
  it does, then it doesn't matter if the way in which it works isn't the most
  elegant way to do things.

  I see the pip-accel backend as the pragmatic choice.

.. _Release 0.16: https://github.com/paylogic/py2deb/compare/0.15...0.16

`Release 0.15`_ (2014-06-01)
----------------------------

Abusing ``update-alternatives`` for fun and profit?

This makes it possible to create a package with an isolated installation prefix
that nevertheless installs global executables in the default executable search
path (``$PATH``).

.. _Release 0.15: https://github.com/paylogic/py2deb/compare/0.14.9...0.15

`Release 0.14.9`_ (2014-05-31)
------------------------------

- Update dependencies.
- Update tests to use new version of deb-pkg-tools_ (including support for
  relationship parsing and matching).
- Bug fix: Exclude other architectures from ``*.deb`` filename matching.

.. _Release 0.14.9: https://github.com/paylogic/py2deb/compare/0.14.8...0.14.9

`Release 0.14.8`_ (2014-05-26)
------------------------------

- Rename ``packages_to_rename`` → ``name_mapping``.
- Update requirements (python-debian 0.1.21-nmu2 for Python 3.x compatibility).
- Replace configuration (global state) with function arguments (local state).

.. _Release 0.14.8: https://github.com/paylogic/py2deb/compare/0.14.7...0.14.8

`Release 0.14.7`_ (2014-05-24)
------------------------------

Bug fix for last commit.

.. _Release 0.14.7: https://github.com/paylogic/py2deb/compare/0.14.6...0.14.7

`Release 0.14.6`_ (2014-05-24)
------------------------------

Don't implicitly forbid automatic installation by pip-accel_.

.. _Release 0.14.6: https://github.com/paylogic/py2deb/compare/0.14.5...0.14.6

`Release 0.14.5`_ (2014-05-22)
------------------------------

- Moved ``package_name_from_filename()`` to ``deb_pkg_tools.package.parse_filename()``.
- Fix non fatal bug in logger format string.

.. _Release 0.14.5: https://github.com/paylogic/py2deb/compare/0.14.4...0.14.5

`Release 0.14.4`_ (2014-05-16)
------------------------------

Implement ``py2deb --inject-deps=CTRL_FILE`` option.

.. _Release 0.14.4: https://github.com/paylogic/py2deb/compare/0.14.3...0.14.4

`Release 0.14.3`_ (2014-05-07)
------------------------------

- Implement ``--no-name-prefix=PKG`` option, use it in the automated tests.
- Test conversion of isolated packages and the ``--rename=FROM,TO`` option.

.. _Release 0.14.3: https://github.com/paylogic/py2deb/compare/0.14.2...0.14.3

`Release 0.14.2`_ (2014-05-07)
------------------------------

- Bug fixes for ``--rename=FROM,TO`` functionality.
- Bug fix for stdeb backend.
- Start writing new tests that cover both backends.
- Start using Sphinx for documentation.
- Add a test involving a package with Python dependencies as well as system
  dependencies (``stdeb.cfg``).

.. _Release 0.14.2: https://github.com/paylogic/py2deb/compare/0.14.1...0.14.2

`Release 0.14.1`_ (2014-05-05)
------------------------------

Bug fix for ``py2deb.util.apply_script()``.

.. _Release 0.14.1: https://github.com/paylogic/py2deb/compare/0.14...0.14.1

`Release 0.14`_ (2014-05-05)
----------------------------

Introduce the ``--rename=FROM,TO`` option to make things more robust.

.. _Release 0.14: https://github.com/paylogic/py2deb/compare/0.13.15...0.14

`Release 0.13.15`_ (2014-05-04)
-------------------------------

Switch from ``deb_pkg_tools.utils.execute()`` to ``executor.execute()`` (today
I decided to extract this functionality into a separate package called
executor_).

.. _Release 0.13.15: https://github.com/paylogic/py2deb/compare/0.13.14...0.13.15
.. _executor: https://pypi.org/project/executor

`Release 0.13.14`_ (2014-05-03)
-------------------------------

Support for default configuration files (``~/.py2deb.ini`` and ``/etc/py2deb.ini``).

.. _Release 0.13.14: https://github.com/paylogic/py2deb/compare/0.13.13...0.13.14

`Release 0.13.13`_ (2014-05-03)
-------------------------------

Support for environment variables (``$PY2DEB_CONFIG``, ``$PY2DEB_REPO`` and
``$PY2DEB_VERBOSE``).

.. _Release 0.13.13: https://github.com/paylogic/py2deb/compare/0.13.12...0.13.13

`Release 0.13.12`_ (2014-04-23)
-------------------------------

Check command line options for non-empty arguments (feedback from Bart_ :-).

.. _Release 0.13.12: https://github.com/paylogic/py2deb/compare/0.13.11...0.13.12
.. _Bart: https://github.com/tarmack

`Release 0.13.11`_ (2014-04-22)
-------------------------------

Ignore overridden Debian package names when building isolated packages.

.. _Release 0.13.11: https://github.com/paylogic/py2deb/compare/0.13.10...0.13.11

`Release 0.13.10`_ (2014-04-11)
-------------------------------

- Don't make the post-installation script error out on syntax errors reported by ``py_compile``.
- Bug fix for apply-script command in pip-accel_ backend.

.. _Release 0.13.10: https://github.com/paylogic/py2deb/compare/0.13.9...0.13.10

`Release 0.13.9`_ (2014-04-11)
------------------------------

Bug fix for order of unpack/apply script/cleanup commands in pip-accel_
backend.

.. _Release 0.13.9: https://github.com/paylogic/py2deb/compare/0.13.8...0.13.9

`Release 0.13.8`_ (2014-04-11)
------------------------------

- Use ``deb_pkg_tools.package.clean_package_tree()`` in pip-accel_ backend.
- Move ``apply_script()`` to common code, call it from both backends
- Move sanity checking from stdeb_ backend to common code.

.. _Release 0.13.8: https://github.com/paylogic/py2deb/compare/0.13.7...0.13.8

`Release 0.13.7`_ (2014-04-09)
------------------------------

Bug fix: Never use the root logger.

.. _Release 0.13.7: https://github.com/paylogic/py2deb/compare/0.13.6...0.13.7

`Release 0.13.6`_ (2014-04-09)
------------------------------

Bug fix: Remove output redirection, change ``--print-deps`` to ``--report-deps=PATH``.

.. _Release 0.13.6: https://github.com/paylogic/py2deb/compare/0.13.5...0.13.6

`Release 0.13.5`_ (2014-04-01)
------------------------------

Bug fix: Don't patch control files of isolated packages.

.. _Release 0.13.5: https://github.com/paylogic/py2deb/compare/0.13.4...0.13.5

`Release 0.13.4`_ (2014-03-31)
------------------------------

Bug fix: Move output redirection to ``main()`` function (where it belongs).

.. _Release 0.13.4: https://github.com/paylogic/py2deb/compare/0.13.3...0.13.4

`Release 0.13.3`_ (2014-03-27)
------------------------------

Reset primary package name when building name/install prefixed packages.

.. _Release 0.13.3: https://github.com/paylogic/py2deb/compare/0.13.2...0.13.3

`Release 0.13.2`_ (2014-03-20)
------------------------------

Cleanup handling & documentation of command line arguments.

.. _Release 0.13.2: https://github.com/paylogic/py2deb/compare/0.13.1...0.13.2

`Release 0.13.1`_ (2014-03-20)
------------------------------

Add a post-installation script to generate ``*.pyc`` files.

.. _Release 0.13.1: https://github.com/paylogic/py2deb/compare/0.13...0.13.1

`Release 0.13`_ (2014-03-20)
----------------------------

Initial support for isolated packages (not in the default ``sys.path``).

.. _Release 0.13: https://github.com/paylogic/py2deb/compare/0.12.3...0.13

`Release 0.12.3`_ (2014-02-01)
------------------------------

Bump pip-accel_ requirement (another upstream bug fixed).

.. _Release 0.12.3: https://github.com/paylogic/py2deb/compare/0.12.2...0.12.3

`Release 0.12.2`_ (2014-01-30)
------------------------------

Bump pip-accel_ requirement (upstream bug fixed).

.. _Release 0.12.2: https://github.com/paylogic/py2deb/compare/0.12.1...0.12.2

`Release 0.12.1`_ (2013-11-03)
------------------------------

Bug fix: Don't fail when a ``PKG-INFO`` file can't be parsed.

.. _Release 0.12.1: https://github.com/paylogic/py2deb/compare/0.12...0.12.1

`Release 0.12`_ (2013-11-03)
----------------------------

Improve the pip-accel_ backend (use a ``prerm`` script to cleanup left over byte code files).

.. _Release 0.12: https://github.com/paylogic/py2deb/compare/0.11.2...0.12

`Release 0.11.2`_ (2013-11-03)
------------------------------

Improve the pip-accel_ backend (the maintainer field is now preserved).

.. _Release 0.11.2: https://github.com/paylogic/py2deb/compare/0.11.1...0.11.2

`Release 0.11.1`_ (2013-11-03)
------------------------------

Improve logging of pip-accel_ backend.

.. _Release 0.11.1: https://github.com/paylogic/py2deb/compare/0.11...0.11.1

`Release 0.11`_ (2013-11-03)
----------------------------

- Improve the pip-accel_ backend (for example it now respects ``stdeb.cfg``).
- Move generation of tagged descriptions to common function.
- Make Python >= 2.6 dependency explicit in ``stdeb.cfg``.

.. _Release 0.11: https://github.com/paylogic/py2deb/compare/0.10.8...0.11

`Release 0.10.8`_ (2013-11-03)
------------------------------

- Add a test case for converting packages with dependencies on replacements.
- Increase the verbosity of the stdeb_ logger.

.. _Release 0.10.8: https://github.com/paylogic/py2deb/compare/0.10.7...0.10.8

`Release 0.10.7`_ (2013-11-02)
------------------------------

Bug fix: Properly convert dependencies on packages with replacements (and add a
test case for converting packages with dependencies).

.. _Release 0.10.7: https://github.com/paylogic/py2deb/compare/0.10.6...0.10.7

`Release 0.10.6`_ (2013-11-02)
------------------------------

- Bug fix: Make ``convert()`` report direct dependencies but not transitive ones.
- Add a first test case to the test suite, use ``py.test`` to run it.

.. _Release 0.10.6: https://github.com/paylogic/py2deb/compare/0.10.5...0.10.6

`Release 0.10.5`_ (2013-11-01)
------------------------------

- Bug fix for logging in ``py2deb.backends.stdeb_backend.patch_control()``.
- Add ``make reset`` target to (re)create virtual environment

.. _Release 0.10.5: https://github.com/paylogic/py2deb/compare/0.10.4...0.10.5

`Release 0.10.4`_ (2013-10-22)
------------------------------

Bug fix for pip-accel_ backend (fallback on e.g. Jaunty and Karmic) by
rewriting ``/site-packages/`` to ``/dist-packages/``.

.. _Release 0.10.4: https://github.com/paylogic/py2deb/compare/0.10.3...0.10.4

`Release 0.10.3`_ (2013-10-22)
------------------------------

Remove automatic dependency installation (way too much magic, a silly idea in retrospect).

.. _Release 0.10.3: https://github.com/paylogic/py2deb/compare/0.10.2...0.10.3

`Release 0.10.2`_ (2013-10-21)
------------------------------

Add a missing Debian dependency: ``python-setuptools``.

.. _Release 0.10.2: https://github.com/paylogic/py2deb/compare/0.10.1...0.10.2

`Release 0.10.1`_ (2013-10-20)
------------------------------

Bug fix for last commit.

.. _Release 0.10.1: https://github.com/paylogic/py2deb/compare/0.10...0.10.1

`Release 0.10`_ (2013-10-20)
----------------------------

Fall back to alternative backend when requested backend fails.

.. _Release 0.10: https://github.com/paylogic/py2deb/compare/0.9.10...0.10

`Release 0.9.10`_ (2013-10-20)
------------------------------

Enable compatiblity with Ubuntu 9.04 (Jaunty) by changing from
``sort --version-sort`` to ``sort --general-numeric-sort``.

.. _Release 0.9.10: https://github.com/paylogic/py2deb/compare/0.9.9...0.9.10

`Release 0.9.9`_ (2013-10-20)
-----------------------------

Bug fix: Don't assume iterable arguments are lists (they might be tuples).

.. _Release 0.9.9: https://github.com/paylogic/py2deb/compare/0.9.8...0.9.9

`Release 0.9.8`_ (2013-10-20)
-----------------------------

Fix recursive import error between ``__init__.py`` and ``bootstrap.py``.

.. _Release 0.9.8: https://github.com/paylogic/py2deb/compare/0.9.7...0.9.8

`Release 0.9.7`_ (2013-10-20)
-----------------------------

Automatic installation of required system packages.

.. _Release 0.9.7: https://github.com/paylogic/py2deb/compare/0.9.6...0.9.7

`Release 0.9.6`_ (2013-10-17)
-----------------------------

Bug fix: Send the output of Lintian to stderr! (otherwise ``--print-deps`` is broken)

.. _Release 0.9.6: https://github.com/paylogic/py2deb/compare/0.9.5...0.9.6

`Release 0.9.5`_ (2013-10-12)
-----------------------------

Bump some requirements.

.. _Release 0.9.5: https://github.com/paylogic/py2deb/compare/0.9.4...0.9.5

`Release 0.9.4`_ (2013-10-12)
-----------------------------

Bug fix for ``py2deb.bootstrap.install()``.

.. _Release 0.9.4: https://github.com/paylogic/py2deb/compare/0.9.3...0.9.4

`Release 0.9.3`_ (2013-10-12)
-----------------------------

Bug fix for ``py2deb.converter.convert()``.

.. _Release 0.9.3: https://github.com/paylogic/py2deb/compare/0.9.2...0.9.3

`Release 0.9.2`_ (2013-10-12)
-----------------------------

Bug fix for ``py2deb --install``.

.. _Release 0.9.2: https://github.com/paylogic/py2deb/compare/0.9.1...0.9.2

`Release 0.9.1`_ (2013-10-12)
-----------------------------

Bug fix for broken import.

.. _Release 0.9.1: https://github.com/paylogic/py2deb/compare/0.9...0.9.1

`Release 0.9`_ (2013-10-12)
---------------------------

- Created a shell script that uses magic in deb-pkg-tools_ to convert py2deb
  using itself and install the resulting ``*.deb`` packages on the local
  system. This shell script was then converted to Python and is available from
  the command line interface using ``py2deb --install``.

- Bug fix: Don't error out when repository directory matches archive directory

.. _Release 0.9: https://github.com/paylogic/py2deb/compare/0.8.6...0.9

`Release 0.8.6`_ (2013-09-29)
-----------------------------

Make it simpler to call py2deb from Python (by moving logic
from ``py2deb.main()`` to ``py2deb.converter.convert()``).

.. _Release 0.8.6: https://github.com/paylogic/py2deb/compare/0.8.5...0.8.6

`Release 0.8.5`_ (2013-09-29)
-----------------------------

Cleanup handling of logging.

.. _Release 0.8.5: https://github.com/paylogic/py2deb/compare/0.8.4...0.8.5

`Release 0.8.4`_ (2013-09-14)
-----------------------------

Be compatible with upstream Debianized packages (e.g. Kazoo).

.. _Release 0.8.4: https://github.com/paylogic/py2deb/compare/0.8.3...0.8.4

`Release 0.8.3`_ (2013-09-14)
-----------------------------

Process required packages in alphabetical sort order.

.. _Release 0.8.3: https://github.com/paylogic/py2deb/compare/0.8.2...0.8.3

`Release 0.8.2`_ (2013-08-13)
-----------------------------

- Improved decision process for choosing stdeb_ version:

  And here's for a very peculiar bug fix... I was trying to convert PyXML 0.8.4
  to a Debian package and the setup.py script kept failing with ``error: invalid
  command 'debianize'``. After much digging:

  - py2deb runs ``python setup.py --command-packages=stdeb.command debianize``
    which implies that ``from stdeb.command import debianize`` is run.

  - ``import stdeb`` actually imports the module bundled with py2deb (which
    automatically pick the right version of stdeb for the current platform) and
    this module imported py2deb -> pip-accel -> pip -> html5lib (bundled with
    pip) which then blows up with::

     >>> import xml.etree.ElementTree as default_etree
     ImportError: No module named etree.ElementTree

  - Turns out PyXML 0.8.4 indeed contains an ``xml`` module... This all happens
    because Python implicitly imports from the current working directory before
    the rest of the entries in ``sys.path`` and PyXML actually depends on this;
    take a look at the ``setup.py`` script.

  Lesson learned: I guess it's wise to restrict our bundled fake stdeb module
  to standard library module imports :-).

- Improved ``py2deb.util.patch_control_file()``.

.. _Release 0.8.2: https://github.com/paylogic/py2deb/compare/0.8.1...0.8.2

`Release 0.8.1`_ (2013-08-13)
-----------------------------

- Implement control overrides for pip-accel_ backend (also: refactor configuration handling).
- Make it possible to override individual Debian package names.
- Backends shouldn't know about "replacements".

.. _Release 0.8.1: https://github.com/paylogic/py2deb/compare/0.8...0.8.1

`Release 0.8`_ (2013-08-13)
---------------------------

Start work on a backend using pip-accel_ instead of stdeb_:

- After working with stdeb_ for over four months it had become painfully clear
  that it would never be able to convert the huge dependency trees I had in
  mind for it because it was simply way too fragile.

- At the same time I knew from working on pip-accel_ that ``python setup.py
  bdist`` was much more reliable / robust and gave usable results, even if
  completely specific to the major and minor version of the running Python
  interpreter.

This is how I decided to start working on an alternative package conversion
backend for py2deb.

.. _Release 0.8: https://github.com/paylogic/py2deb/compare/0.7.7...0.8

`Release 0.7.7`_ (2013-08-11)
-----------------------------

- Remove reference to stdeb_ from py2deb.ini (bundled with py2deb anyway)
- Log external command execution.
- Fix copy/paste error in ``setup.py``.
- Improve stdeb_ version selection.

.. _Release 0.7.7: https://github.com/paylogic/py2deb/compare/0.7.6...0.7.7

`Release 0.7.6`_ (2013-08-11)
-----------------------------

Use ``coloredlogs.increase_verbosity()`` (always keep logger at full verbosity).

.. _Release 0.7.6: https://github.com/paylogic/py2deb/compare/0.7.5...0.7.6

`Release 0.7.5`_ (2013-08-11)
-----------------------------

- Start using ``deb_pkg_tools.package.clean_package_tree()``.
- Add ``README`` and ``LICENSE`` to ``MANIFEST.in``.

.. _Release 0.7.5: https://github.com/paylogic/py2deb/compare/0.7.4...0.7.5

`Release 0.7.4`_ (2013-08-11)
-----------------------------

Compatibility with pip-accel_ 0.9.4.

.. _Release 0.7.4: https://github.com/paylogic/py2deb/compare/0.7.3...0.7.4

`Release 0.7.3`_ (2013-08-11)
-----------------------------

Improve the ``setup.py`` script and move the installation requirements to a
separate ``requirements.txt`` file.

.. _Release 0.7.3: https://github.com/paylogic/py2deb/compare/0.7.2...0.7.3

`Release 0.7.2`_ (2013-08-07)
-----------------------------

Tweak the requirements.

.. _Release 0.7.2: https://github.com/paylogic/py2deb/compare/0.7.1...0.7.2

`Release 0.7.1`_ (2013-08-05)
-----------------------------

- Compatibility with the latest version of pip-accel_ (0.9.12).
- Compatibility with the latest version of deb-pkg-tools_.
- Restore release tag in pinned versions only.
- Abuse "Description" field to advertise py2deb.
- Make ``py2deb -v`` imply ``DH_VERBOSE=1`` (pass verbosity to debian-helper scripts).

.. _Release 0.7.1: https://github.com/paylogic/py2deb/compare/0.7...0.7.1

`Release 0.7`_ (2013-07-23)
---------------------------

This is a snapshot in the middle of a big refactoring...

I'd love to use py2deb in a dozen places but was blocked from doing so because
of a handful of unrelated issues that remained to be solved. After lots of
testing, failed attempts and frustration I now have something that seems to
work (although I have to clean it up and there are still some minor issues that
I'm aware of):

- My original goal with py2deb was to use two name spaces for the names of
  generated packages: The real name space ``pl-python-...`` would be very
  explicit but dependencies would refer to virtual packages named
  ``python-...``. Then the ``pl-python-...`` packages could have ``Provides:``
  fields giving the ``python-...`` names.
   
  It turns out this cannot work the way I want it to; virtual packages are
  second class citizens in Debian :-(. AFAICT the only way to get everything
  working properly is to just use the ``python-...`` name space directly, so
  that's what the new code is slowly working towards.

- Merging of control files was not working properly, however some months ago (I
  think before py2deb was born) I wrote my own control file merger. I've now
  extracted that from the project where it originated and moved it to a package
  called deb-pkg-tools_, which hasn't been released yet but will be soon. py2deb
  now uses deb-pkg-tools to patch/merge control files.

- The Python ``==`` version matching operator was copied verbatim to the
   Debian control files which is invalid. This is now fixed.

- stdeb_ 0.6.0 is required on Ubuntu 10.04, stdeb 0.6.0+git is required on
  Ubuntu 12.04, however stdeb 0.6.0+git hasn't been released yet. Also Python
  nor Debian can simply/elegantly express this *very explicit* distinction
  between stdeb versions and Ubuntu distributions. The only remaining way to
  keep my sanity was to bundle both versions of stdeb inside py2deb.

  TODO: Add READMEs, LICENSEs.

- Lots of changes to logging including the version of coloredlogs and the
  introduction of separate loggers for separate modules.

- Lots of moving around with code and responsibilities while I tried to make
  sense of the way py2deb should and could work.

.. _Release 0.7: https://github.com/paylogic/py2deb/compare/0.6.10...0.7
.. _deb-pkg-tools: https://pypi.org/project/deb-pkg-tools/

`Release 0.6.10`_ (2013-07-05)
------------------------------

- Replace nasty rules file patching with an environment variable
- Improved the README.

.. _Release 0.6.10: https://github.com/paylogic/py2deb/compare/0.6.9...0.6.10

`Release 0.6.9`_ (2013-06-27)
-----------------------------

Minor changes to logging output (changed severity levels + made logger name visible).

.. _Release 0.6.9: https://github.com/paylogic/py2deb/compare/0.6.8...0.6.9

`Release 0.6.8`_ (2013-06-27)
-----------------------------

Make it possible to set the repository directory as a command line option.

.. _Release 0.6.8: https://github.com/paylogic/py2deb/compare/0.6.7...0.6.8

`Release 0.6.7`_ (2013-06-27)
-----------------------------

Sneaking in a minor bug fix.

.. _Release 0.6.7: https://github.com/paylogic/py2deb/compare/0.6.6...0.6.7

`Release 0.6.6`_ (2013-06-27)
-----------------------------

Redirect pip's output to stderr.

.. _Release 0.6.6: https://github.com/paylogic/py2deb/compare/0.6.5...0.6.6

`Release 0.6.5`_ (2013-06-26)
-----------------------------

- Updated README.
- Return of the sanity_check

.. _Release 0.6.5: https://github.com/paylogic/py2deb/compare/0.6.4...0.6.5

`Release 0.6.4`_ (2013-06-25)
-----------------------------

- Will now correctly remove the script field.
- Fixed dependency issues.

.. _Release 0.6.4: https://github.com/paylogic/py2deb/compare/0.6.2...0.6.4

`Release 0.6.2`_ (2013-06-25)
-----------------------------

Temporarily removed sanity checking.

.. _Release 0.6.2: https://github.com/paylogic/py2deb/compare/0.6.1...0.6.2

`Release 0.6.1`_ (2013-06-24)
-----------------------------

Added sanity check on dependencies using pip-accel_.

.. _Release 0.6.1: https://github.com/paylogic/py2deb/compare/0.6.0...0.6.1

`Release 0.6.0`_ (2013-06-24)
-----------------------------

- Moved and rewrote converter, package, util to reflect changes to the cli.
- Fixed check on returncodes from subprocesses.
- Overhauled command line options.
- Changed verbosity option.
- Renamed control.ini.

.. _Release 0.6.0: https://github.com/paylogic/py2deb/compare/0.5.41...0.6.0

`Release 0.5.41`_ (2013-06-04)
------------------------------

Try to deal better with packages that have Debian replacements.

.. _Release 0.5.41: https://github.com/paylogic/py2deb/compare/0.5.40...0.5.41

`Release 0.5.40`_ (2013-06-04)
------------------------------

Deal with the python-imaging vs. pil vs. pillow mess 😞.

.. _Release 0.5.40: https://github.com/paylogic/py2deb/compare/0.5.39...0.5.40

`Release 0.5.39`_ (2013-06-04)
------------------------------

Added ``pil`` to ``control.ini``.

.. _Release 0.5.39: https://github.com/paylogic/py2deb/compare/0.5.38...0.5.39

`Release 0.5.38`_ (2013-06-04)
------------------------------

Lots of changes to deal with the whole setuptools/distribute contraption...

.. _Release 0.5.38: https://github.com/paylogic/py2deb/compare/0.5.37...0.5.38

`Release 0.5.37`_ (2013-06-04)
------------------------------

Added ``Pillow`` conflict with ``python-imaging`` to ``control.ini``.

.. _Release 0.5.37: https://github.com/paylogic/py2deb/compare/0.5.36...0.5.37

`Release 0.5.36`_ (2013-05-30)
------------------------------

- Mark the ``python-support`` package as a requirement of py2deb in the
  configuration file.
- Added the command line option ``-d``, ``--no-deps`` to ignore dependencies.

.. _Release 0.5.36: https://github.com/paylogic/py2deb/compare/0.5.35...0.5.36

`Release 0.5.35`_ (2013-05-17)
------------------------------

Raise an exception if there is no dependency file to recall.

.. _Release 0.5.35: https://github.com/paylogic/py2deb/compare/0.5.34...0.5.35

`Release 0.5.34`_ (2013-05-17)
------------------------------

Properly integrate pip-accel_ 0.8.5 into py2deb and remove the embedded (and
simplified) variant of pip-accel_ from the py2deb code base.

.. _Release 0.5.34: https://github.com/paylogic/py2deb/compare/0.5.33...0.5.34

`Release 0.5.33`_ (2013-05-02)
------------------------------

Workaround Fabric bundling Paramiko.

.. _Release 0.5.33: https://github.com/paylogic/py2deb/compare/0.5.32...0.5.33

`Release 0.5.32`_ (2013-05-02)
------------------------------

Bug fix: Requirement instance has no attribute 'specs'.

.. _Release 0.5.32: https://github.com/paylogic/py2deb/compare/0.5.31...0.5.32

`Release 0.5.31`_ (2013-05-02)
------------------------------

Remove confusion about ``py2deb.package.Requirement`` versus
``pkg_resources.Requirement``.

.. _Release 0.5.31: https://github.com/paylogic/py2deb/compare/0.5.30...0.5.31

`Release 0.5.30`_ (2013-05-02)
------------------------------

- Rename ``[replace_dependencies]`` section to ``[replacements]``.
- Add ``[replacements]`` workarounds for specific packages to the configuration file.
- Don't translate replacement package names.

.. _Release 0.5.30: https://github.com/paylogic/py2deb/compare/0.5.29...0.5.30

`Release 0.5.29`_ (2013-05-02)
------------------------------

Make pinned Debian dependencies explicit.

.. _Release 0.5.29: https://github.com/paylogic/py2deb/compare/0.5.28...0.5.29

`Release 0.5.28`_ (2013-05-02)
------------------------------

Change the location of the default repository when running as ``root``.

.. _Release 0.5.28: https://github.com/paylogic/py2deb/compare/0.5.27...0.5.28

`Release 0.5.27`_ (2013-05-02)
------------------------------

- Pinned version of ``python-debian``.
- Support for "replacing" dependencies (for example ``setuptools`` versus ``distribute``).
- Lots of changes and improvements to dependency/requirement handling.

.. _Release 0.5.27: https://github.com/paylogic/py2deb/compare/0.5.26...0.5.27

`Release 0.5.26`_ (2013-05-01)
------------------------------

Incorporate release numbers in pinned versions (without this, ``pl-py2deb
--recall`` reports invalid versions).

.. _Release 0.5.26: https://github.com/paylogic/py2deb/compare/0.5.25...0.5.26

`Release 0.5.25`_ (2013-05-01)
------------------------------

- Make it possible to persist and recall Debianized dependencies.
- Add a simple command line interface.
- Place built packages in ``/tmp`` if user is not ``root``.
- Make sure ``python setup.py debianize`` runs inside the virtual environment.

.. _Release 0.5.25: https://github.com/paylogic/py2deb/compare/0.5.24...0.5.25

`Release 0.5.24`_ (2013-05-01)
------------------------------

Report dependencies as well as required versions.

.. _Release 0.5.24: https://github.com/paylogic/py2deb/compare/0.5.23...0.5.24

`Release 0.5.23`_ (2013-04-29)
------------------------------

Another bug fix.

.. _Release 0.5.23: https://github.com/paylogic/py2deb/compare/0.5.22...0.5.23

`Release 0.5.22`_ (2013-04-29)
------------------------------

Another bug fix.

.. _Release 0.5.22: https://github.com/paylogic/py2deb/compare/0.5.21...0.5.22

`Release 0.5.21`_ (2013-04-29)
------------------------------

Another bug fix.

.. _Release 0.5.21: https://github.com/paylogic/py2deb/compare/0.5.20...0.5.21

`Release 0.5.20`_ (2013-04-29)
------------------------------

Sorry, forgot to call the function...

.. _Release 0.5.20: https://github.com/paylogic/py2deb/compare/0.5.19...0.5.20

`Release 0.5.19`_ (2013-04-29)
------------------------------

Bug fix for previous release.

.. _Release 0.5.19: https://github.com/paylogic/py2deb/compare/0.5.18...0.5.19

`Release 0.5.18`_ (2013-04-29)
------------------------------

Bug fix for dependency introspection.

.. _Release 0.5.18: https://github.com/paylogic/py2deb/compare/0.5.17...0.5.18

`Release 0.5.17`_ (2013-04-29)
------------------------------

Remove ``merge_dicts`` usage.

.. _Release 0.5.17: https://github.com/paylogic/py2deb/compare/0.5.16...0.5.17

`Release 0.5.16`_ (2013-04-29)
------------------------------

Don't print empty ``Depends:`` fields.

.. _Release 0.5.16: https://github.com/paylogic/py2deb/compare/0.5.15...0.5.16

`Release 0.5.15`_ (2013-04-29)
------------------------------

Bug fix for deb822 usage (``merge_fields`` doesn't work if you start with an
empty field).

.. _Release 0.5.15: https://github.com/paylogic/py2deb/compare/0.5.14...0.5.15

`Release 0.5.14`_ (2013-04-29)
------------------------------

Bug fix for release 0.5.13.

.. _Release 0.5.14: https://github.com/paylogic/py2deb/compare/0.5.13...0.5.14

`Release 0.5.13`_ (2013-04-29)
------------------------------

Print the ``Depends:`` fields of built packages.

.. _Release 0.5.13: https://github.com/paylogic/py2deb/compare/0.5.12...0.5.13

`Release 0.5.12`_ (2013-04-25)
------------------------------

Code style noise.

.. _Release 0.5.12: https://github.com/paylogic/py2deb/compare/0.5.11...0.5.12

`Release 0.5.11`_ (2013-04-25)
------------------------------

Bug fix: Use ``pkg_resources.Requirement.parse()`` to properly parse
requirement expressions.

.. _Release 0.5.11: https://github.com/paylogic/py2deb/compare/0.5.10...0.5.11

`Release 0.5.10`_ (2013-04-25)
------------------------------

Don't silence the output of ``dpkg-buildpackage``.

.. _Release 0.5.10: https://github.com/paylogic/py2deb/compare/0.5.9...0.5.10

`Release 0.5.9`_ (2013-04-25)
-----------------------------

- Ignore GPG signing when building packages.
- Don't cleanup build directory on exceptions (allows post-mortem debugging).
- Added a readme and todo list.

.. _Release 0.5.9: https://github.com/paylogic/py2deb/compare/0.5.8...0.5.9

`Release 0.5.8`_ (2013-04-25)
-----------------------------

Yet another bug fix for release 0.5.5...

.. _Release 0.5.8: https://github.com/paylogic/py2deb/compare/0.5.7...0.5.8

`Release 0.5.7`_ (2013-04-25)
-----------------------------

Another bug fix for release 0.5.5.

.. _Release 0.5.7: https://github.com/paylogic/py2deb/compare/0.5.6...0.5.7

`Release 0.5.6`_ (2013-04-25)
-----------------------------

Bug fix for release 0.5.5.

.. _Release 0.5.6: https://github.com/paylogic/py2deb/compare/0.5.5...0.5.6

`Release 0.5.5`_ (2013-04-25)
-----------------------------

Fixes for installation of global build dependencies.

.. _Release 0.5.5: https://github.com/paylogic/py2deb/compare/0.5.4...0.5.5

`Release 0.5.4`_ (2013-04-25)
-----------------------------

Don't silence the output of ``apt-get`` when installing build dependencies.

.. _Release 0.5.4: https://github.com/paylogic/py2deb/compare/0.5.3...0.5.4

`Release 0.5.3`_ (2013-04-25)
-----------------------------

Use system wide pip-accel_ cache directories when running as ``root``.

.. _Release 0.5.3: https://github.com/paylogic/py2deb/compare/0.5.2...0.5.3
.. _pip-accel: https://github.com/paylogic/pip-accel

`Release 0.5.2`_ (2013-04-25)
-----------------------------

Add dependency on ``chardet`` which is imported by ``python-debian`` but not
included in its installation requirements.

.. _Release 0.5.2: https://github.com/paylogic/py2deb/compare/0.5.1...0.5.2

`Release 0.5.1`_ (2013-04-25)
-----------------------------

- Properly nest all Python modules under ``pydeb.*`` namespace.
- Renamed command line entry point from ``py2deb`` to ``pl-py2deb``.

  Context: py2deb is developed at Paylogic_ where a lot of our internal command
  line tools use the ``pl-*`` namespace inspired by the ``mk-*`` / ``pt-*``
  namespace that `Percona Toolkit`_ uses.

.. _Release 0.5.1: https://github.com/paylogic/py2deb/compare/0.5.0...0.5.1
.. _Paylogic: https://www.paylogic.com/
.. _Percona Toolkit: https://www.percona.com/software/database-tools/percona-toolkit

`Release 0.5.0`_ (2013-04-24)
-----------------------------

The initial release, very much a rough work in progress 😇.

The py2deb project was kicked off by Arjan, an intern at Paylogic at the time,
in collaboration with Peter (who guided Arjan's internship). The abstract idea
that we set out to create was as follows:

- Use pip_ to download a Python package from PyPI and recursively gather
  installation requirements until we can satisfy all dependencies.

- Use stdeb_ to batch convert all of the downloaded Python packages to Debian
  packages.

.. _Release 0.5.0: https://github.com/paylogic/py2deb/tree/0.5.0
.. _pip: https://pip.pypa.io/en/stable/
.. _stdeb: https://pypi.org/project/stdeb
