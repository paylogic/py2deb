Where does py2deb fit in?
=========================

There are several projects out there that share similarities with py2deb, for
example I know of stdeb_, dh-virtualenv_ and fpm_. For those who know these
other projects already and are curious about where py2deb fits in, I would
classify py2deb as a sort of pragmatic compromise between dh-virtualenv_ and
stdeb_ (without the disadvantages that I see in both of these projects).

Below I will attempt to provide a fair comparison between these projects.
Please note that it is not my intention to discourage the use of any of these
projects or to list just the down sides: They all have their place! Of course I
do think `py2deb` has something to add to the mix, otherwise I wouldn't have
created it :-).

If you feel that another project should be discussed here or that an existing
comparison is inaccurate then feel free to mention this on the `py2deb issue
tracker`_.

.. contents::
   :local:

The short comparison
--------------------

In my research into `py2deb`, `stdeb` and `dh-virtualenv` I've come to a sort
of realization about all of these projects that makes it fairly easy to
differentiate them for those who have a passing familiarity with one or more of
these projects: The projects can be placed on a spectrum ranging from very
pragmatic (and dumb, to a certain extent :-) to very perfectionistic (and
idealistic and fragile, to a certain extent). Based on my observations:

- `dh-virtualenv` is a pragmatic solution to a concrete problem. It solves this
  single problem and seems to do so quite well.

- `stdeb` is somewhat pragmatic in the sense that it tries to make the contents
  of the `Python Package Index`_ available to Debian based systems, but it is
  quite perfectionistic (idealistic) in how it goes about accomplishing this.
  When it works it results in fairly high quality conversions.

- `py2deb` sits somewhere between `dh-virtualenv` and `stdeb`:

  - It allows complete requirement sets to be converted (similar to
    `dh-virtualenv`).

  - It converts requirement sets by generating individual binary packages
    (similar to `stdeb`).

  - It can convert requirement sets using a custom name and installation prefix
    to allow the same kind of isolation that `dh-virtualenv` provides.

  - It uses `dpkg-shlibdeps` to automatically track dependencies on system
    packages (inspired by `stdeb`).

Comparison to stdeb
-------------------

The stdeb_ program converts Python source distributions to Debian source
packages which can then be compiled to Debian binary packages (optionally in a
single call).

Shared goals with stdeb
~~~~~~~~~~~~~~~~~~~~~~~

The `stdeb` and `py2deb` projects share very similar goals, in fact `py2deb`
started out being based on `stdeb` but eventually reimplemented the required
functionality on top of pip-accel_ and deb-pkg-tools_. The following goals are
still shared between `stdeb` and `py2deb`:

- Combine the power and ease of deployment of Debian packaging with the rich
  ecosystem of Python packages available on the `Python Package Index`_.

- Provide users with a very easy way to take a Python package and convert it
  into a Debian binary package that is ready to install, without having to know
  the intricate details of the Debian packaging ecosystem.

Notable differences with stdeb
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Although `py2deb` started out being a wrapper for `stdeb` the goals of the two
projects have diverged quite a bit since then. Some notable differences:

- `stdeb` starts by generating Debian source packages while `py2deb` generates
  Debian binary packages without intermediate Debian source packages:

  - `stdeb` works by converting a Python package to a Debian source package
    that uses the existing Debian Python packaging mechanisms. The Debian
    source package can then be compiled into a Debian binary package. These two
    actions can optionally be combined into a single invocation. `stdeb` is
    intended to generate Python Debian packages that comply to the Debian
    packaging policies as much as possible (this is my interpretation).

    - For example Python modules are installed in the pyshared_ directory so
      that multiple Python versions can use the modules. The advantages of this
      are clear, but the main disadvantage is that `stdeb` is sensitive to
      changes in Debian packaging infrastructure. For example it doesn't run on
      older versions of Ubuntu Linux (at one point this was a requirement for
      me). `py2deb` on the other hand is kind of dumb but works almost
      everywhere.

  - `py2deb` never generates Debian source packages, instead it generates
    Debian binary packages directly. This means `py2deb` doesn't use or
    integrate with the Debian Python packaging mechanisms. This was a conscious
    choice that I'll elaborate on further in the following point.

- The main use case of `stdeb` is to convert individual Python packages to
  Debian packages that are installed system wide under the `python-*` name
  prefix. On the other hand `py2deb` always converts complete dependency sets
  (in fact `py2deb` started out as a wrapper for `stdeb` that just added the
  "please convert a complete dependency set for me" aspect). Some consequences
  of this:

  - `stdeb` works fine when converting a couple of Python packages individually
    but if you want to convert a large dependency set it quickly becomes hairy
    and fragile due to scripting of `stdeb`, conflicts with existing system
    packages and other reasons. If you want this process to run automatically
    and reliably without supervision then I personally wouldn't recommend
    `stdeb` - it has given me quite a few headaches because I was pushing
    `stdeb` way beyond its intended use case (my fault entirely, I'm not
    blaming the tool).

  - The larger the dependency set given to `py2deb`, the larger the risk that
    conflicts will occur between Python packages from the official repositories
    versus the packages converted by `py2deb`. This is why `py2deb` eventually
    stopped being based on `stdeb`: In order to add the ability to install
    converted packages under a custom name prefix and installation prefix.
    When used in this mode `py2deb` is something of a pragmatic compromise
    between `stdeb` and `dh-virtualenv`.

Comparison to dh-virtualenv
---------------------------

The dh-virtualenv_ tool provides helpers to easily create a Debian source
package that takes a `pip requirements file`_ and builds a Python virtual
environment that is then packaged as a Debian binary package.

Shared goals with dh-virtualenv
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following goals are shared between `dh-virtualenv` and `py2deb`:

- Combine the power and ease of deployment of Debian packaging with the rich
  ecosystem of Python packages available on the `Python Package Index`_.

- Easily deploy Python based applications with complex dependency sets which
  may conflict with system wide Python packages (`dh-virtualenv` always
  provides this isolation while `py2deb` provides the option but doesn't
  enforce it).

Notable differences with dh-virtualenv
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following notable differences can be observed:

- `dh-virtualenv` requires creating a Debian source package in order to
  generate a Debian binary package while `py2deb` focuses exclusively on
  generating Debian binary packages. Both approaches are valid and have
  advantages and disadvantages:

  - The use of `dh-virtualenv` requires a certain amount of knowledge about how
    to create, manage and build Debian source packages.

  - The use of `py2deb` requires fairly little knowledge about Debian packaging
    and it specifically doesn't require any knowledge about Debian source
    packages.

- `dh-virtualenv` includes a complete requirement set in a single binary
  package while `py2deb` converts each requirement individually (whether
  configured to use an isolated name space or not):

  - An advantage of `dh-virtualenv` here is that the generated ``*.deb`` is
    completely self contained. The disadvantage of this is that when you update
    only a few requirements in a large requirement set you get to rebuild,
    redownload and reinstall the complete requirement set anyway.

  - For `py2deb` the situation is the inverse: Generated binary packages are
    not self contained (each requirement gets a separate ``*.deb`` archive).
    This means that when only a few requirements in a large requirement set are
    updated only those requirements are rebuilt, redownloaded and reinstalled.

Comparison to fpm
-----------------

The fpm_ program is a generic package converter that supports multiple input
formats (Python packages, Ruby packages, etc.) and multiple output formats
(Debian binary packages, Red Hat binary packages, etc.).

Shared goals with fpm
~~~~~~~~~~~~~~~~~~~~~

The `fpm` and `py2deb` projects in the end have very different goals but there
is at least one shared goal:

- Provide users with a very easy way to take a Python package and convert it
  into a Debian binary package that is ready to install, without having to know
  the intricate details of the Debian packaging ecosystem.

Notable differences with fpm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here are some notable differences between `fpm` and `py2deb`:

- `fpm` is a generic package converter while `py2deb` specializes in conversion
  of Python to Debian packages. This makes `fpm` more like a Swiss Army knife
  while `py2deb` has a very specialized use case for which it is actually
  specialized (`py2deb` is smarter about Python to Debian package conversion).

- With `py2deb` it is very easy to convert packages using a custom name and
  installation prefix, allowing conversion of large/complex requirement sets
  that would inevitably conflict with Debian packages from official
  repositories (e.g. because of older or newer versions).

- `py2deb` recognizes dependencies on system packages (libraries) and embeds
  them in the dependencies of the generated Debian packages. This is not so
  important when `py2deb` is used on the system where the converted packages
  will be installed (the dependencies will already have been installed,
  otherwise the package couldn't have been built and converted) but it's
  essential when the converted packages will be deployed to other systems.

.. _deb-pkg-tools: https://pypi.org/project/deb-pkg-tools
.. _dh-virtualenv: https://github.com/spotify/dh-virtualenv
.. _fpm: https://github.com/jordansissel/fpm
.. _pip requirements file: https://pip.pypa.io/en/latest/user_guide.html#requirements-files
.. _pip-accel: https://github.com/paylogic/pip-accel
.. _py2deb issue tracker: https://github.com/paylogic/py2deb/issues
.. _pyshared: https://www.debian.org/doc/packaging-manuals/python-policy/ch-python.html#s-paths
.. _Python Package Index: http://pypi.python.org/
.. _stdeb: https://github.com/astraw/stdeb
