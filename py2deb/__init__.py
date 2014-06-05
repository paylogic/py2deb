# py2deb: Python to Debian package converter.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: June 5, 2014
# URL: https://py2deb.readthedocs.org

"""
The main module of py2deb, the Python to Debian package converter.
"""

# Standard library modules.
import glob
import logging
import os
import pipes
import re
import shutil
import sys
import tempfile
import time

# External dependencies.
from cached_property import cached_property
from deb_pkg_tools.control import merge_control_fields, unparse_control_fields
from deb_pkg_tools.package import build_package, find_package_archives
from docutils.core import publish_string
from docutils.writers.html4css1 import Writer
from executor import execute
from html2text import HTML2Text
from humanfriendly import concatenate, pluralize
from pip.exceptions import DistributionNotFound
from pip_accel import download_source_dists, initialize_directories, install_binary_dist, unpack_source_dists
from pip_accel.bdist import get_binary_dist
from pip_accel.deps import sanity_check_dependencies
from pkg_resources import Requirement
from pkginfo import UnpackedSDist
from six.moves import configparser, StringIO

# Semi-standard module versioning.
__version__ = '0.16'

# Initialize a logger.
logger = logging.getLogger(__name__)

# The following installation prefixes are known to contain a `bin' directory
# that's available on the default executable search path (the environment
# variable $PATH).
KNOWN_INSTALL_PREFIXES = ('/usr', '/usr/local')


class PackageConverter(object):

    """
    The external interface of `py2deb`, the Python to Debian package converter.
    """

    def __init__(self):
        """
        Initialize a Python to Debian package converter.
        """
        self.alternatives = set()
        self.auto_install = False
        self.install_prefix = '/usr'
        self.max_download_attempts = 10
        self.name_mapping = {}
        self.name_prefix = 'python'
        self.repository = PackageRepository(tempfile.gettempdir())
        self.scripts = {}

    def set_repository(self, directory):
        """
        Set pathname of directory where `py2deb` stores converted packages.

        :param directory: The pathname of a directory (a string).
        :raises: :py:exc:`exceptions.ValueError` when the directory doesn't
                 exist.
        """
        directory = os.path.abspath(directory)
        if not os.path.isdir(directory):
            msg = "Repository directory doesn't exist! (%s)"
            raise ValueError(msg % directory)
        self.repository = PackageRepository(directory)

    def set_name_prefix(self, prefix):
        """
        Set package name prefix to use during package conversion.

        :param prefix: The name prefix to use (a string).
        :raises: :py:exc:`exceptions.ValueError` when no name prefix is
                 provided (e.g. an empty string).
        """
        if not prefix:
            raise ValueError("Please provide a nonempty name prefix!")
        self.name_prefix = prefix

    def rename_package(self, python_package_name, debian_package_name):
        """
        Override package name conversion algorithm for given pair of names.

        :param python_package_name: The name of a Python package
                                    as found on PyPI (a string).
        :param debian_package_name: The name of the converted
                                    Debian package (a string).
        :raises: :py:exc:`exceptions.ValueError` when a package name is not
                 provided (e.g. an empty string).
        """
        if not python_package_name:
            raise ValueError("Please provide a nonempty Python package name!")
        if not debian_package_name:
            raise ValueError("Please provide a nonempty Debian package name!")
        self.name_mapping[python_package_name.lower()] = debian_package_name.lower()

    def set_install_prefix(self, directory):
        """
        Set installation prefix to use during package conversion.

        The installation directory doesn't have to exist on the system where
        the package is converted.

        :param directory: The pathname of the directory where the converted
                          packages should be installed (a string).
        :raises: :py:exc:`exceptions.ValueError` when no installation prefix is
                 provided (e.g. an empty string).
        """
        if not directory:
            raise ValueError("Please provide a nonempty installation prefix!")
        self.install_prefix = directory

    def set_auto_install(self, enabled):
        """
        Enable or disable automatic installation of build time dependencies.

        :param enabled: If this evaluates to ``True`` automatic installation is
                        enabled, otherwise it's disabled.
        """
        self.auto_install = bool(enabled)

    def install_alternative(self, link, path):
        r"""
        Install system wide link for program installed in custom installation prefix.

        Use Debian's update-alternatives_ system to add an executable that's
        installed in a custom installation prefix to the system wide executable
        search path using a symbolic link.

        :param link: The generic name for the master link (a string). This is
                     the first argument passed to ``update-alternatives
                     --install``.
        :param path: The alternative being introduced for the master link (a
                     string). This is the third argument passed to
                     ``update-alternatives --install``.
        :raises: :py:exc:`exceptions.ValueError` when one of the paths is not
                 provided (e.g. an empty string).

        If this is a bit vague, consider the following example:

        .. code-block:: sh

           $ py2deb --name-prefix=py2deb \
                    --no-name-prefix=py2deb \
                    --install-prefix=/usr/lib/py2deb \
                    --install-alternative=/usr/bin/py2deb,/usr/lib/py2deb/bin/py2deb \
                    py2deb==0.1

        This example will convert `py2deb` and its dependencies using a custom
        name prefix and a custom installation prefix which means the ``py2deb``
        program is not available on the default executable search path. This is
        why ``update-alternatives`` is used to create a symbolic link
        ``/usr/bin/py2deb`` which points to the program inside the custom
        installation prefix.

        .. _update-alternatives: http://manpages.debian.org/cgi-bin/man.cgi?query=update-alternatives
        """
        if not link:
            raise ValueError("Please provide a nonempty name for the master link!")
        if not path:
            raise ValueError("Please provide a nonempty name for the alternative being introduced!")
        self.alternatives.add((link, path))

    def set_conversion_command(self, python_package_name, command):
        """
        Set shell command to be executed during conversion process.

        The shell command is executed in the directory containing the Python
        module(s) that are to be installed by the converted package.

        :param python_package_name: The name of a Python package
                                    as found on PyPI (a string).
        :param command: The shell command to execute (a string).
        :raises: :py:exc:`exceptions.ValueError` when the package name or
                 command is not provided (e.g. an empty string).

        .. warning:: This functionality allows arbitrary manipulation of the
                     Python modules to be installed by the converted package.
                     It should clearly be considered a last resort, only for
                     for fixing things like packaging issues with Python
                     packages that you can't otherwise change.

        For example old versions of Fabric_ bundle a copy of Paramiko_. Most
        people will never notice this because Python package managers don't
        complain about this, they just blindly overwrite the files... Debian's
        packaging system is much more strict and will consider the converted
        Fabric and Paramiko packages as conflicting and thus broken. In this
        case you have two options:

        1. Switch to a newer version of Fabric that no longer bundles Paramiko;
        2. Use the conversion command ``rm -rf paramiko`` to convert Fabric
           (yes this is somewhat brute force :-).

        .. _Fabric: https://pypi.python.org/pypi/Fabric
        .. _Paramiko: https://pypi.python.org/pypi/paramiko
        """
        if not python_package_name:
            raise ValueError("Please provide a nonempty Python package name!")
        if not command:
            raise ValueError("Please provide a nonempty shell command!")
        self.scripts[python_package_name.lower()] = command

    def load_configuration(self, configuration_file):
        """
        Load configuration defaults from a configuration file.

        :param configuration_file: The pathname of a configuration file (a
                                   string).

        Below is an example of the available options, I assume that the mapping
        between the configuration options and the setters of
        :py:class:`PackageConverter` is fairly obvious (it should be :-).

        .. code-block:: ini

           # The `py2deb' section contains global options.
           [py2deb]
           repository = /tmp
           name-prefix = py2deb
           install-prefix = /usr/lib/py2deb
           auto-install = on

           # The `alternatives' section contains instructions
           # for Debian's `update-alternatives' system.
           [alternatives]
           /usr/bin/py2deb = /usr/lib/py2deb/bin/py2deb

           # Sections starting with `package:' contain conversion options
           # specific to a package.
           [package:py2deb]
           no-name-prefix = true

        Note that the configuration options shown here are just examples, they
        are not the configuration defaults (they are what I use to convert
        `py2deb` itself). Package specific sections support the following
        options:

        **no-name-prefix**:
          A boolean indicating whether the configured name prefix should be
          applied or not. Understands ``true`` and ``false`` (``false`` is the
          default and you only need this option to change the default).

        **rename**:
          Gives an override for the package name conversion algorithm (refer to
          :py:func:`rename_package()` for details).

        **script**:
          Set a shell command to be executed during the conversion process
          (refer to :py:func:`set_conversion_command()` for
          details).
        """
        # Load the configuration file.
        parser = configparser.RawConfigParser()
        files_loaded = parser.read(configuration_file)
        try:
            assert len(files_loaded) == 1
            assert os.path.samefile(configuration_file, files_loaded[0])
        except Exception:
            msg = "Failed to load configuration file! (%s)"
            raise Exception(msg % configuration_file)
        # Apply the global settings in the configuration file.
        if parser.has_option('py2deb', 'repository'):
            self.set_repository(parser.get('py2deb', 'repository'))
        if parser.has_option('py2deb', 'name-prefix'):
            self.set_name_prefix(parser.get('py2deb', 'name-prefix'))
        if parser.has_option('py2deb', 'install-prefix'):
            self.set_install_prefix(parser.get('py2deb', 'install-prefix'))
        if parser.has_option('py2deb', 'auto-install'):
            self.set_auto_install(parser.getboolean('py2deb', 'auto-install'))
        # Apply the defined alternatives.
        if parser.has_section('alternatives'):
            for link, path in parser.items('alternatives'):
                self.install_alternative(link, path)
        # Apply any package specific settings.
        for section in parser.sections():
            tag, _, package = section.partition(':')
            if tag == 'package':
                if parser.has_option(section, 'no-name-prefix'):
                    if parser.getboolean(section, 'no-name-prefix'):
                        self.rename_package(package, package)
                if parser.has_option(section, 'rename'):
                    rename_to = parser.get(section, 'rename')
                    self.rename_package(package, rename_to)
                if parser.has_option(section, 'script'):
                    script = parser.get(section, 'script')
                    self.set_conversion_command(package, script)

    def convert(self, pip_install_arguments):
        """
        Convert one or more Python packages to Debian packages.

        :param pip_install_arguments: The command line arguments to the ``pip
                                      install`` command.
        :returns: A list of strings containing the Debian package relationships
                  required to depend on the converted package(s).

        Here's an example of what's returned:

        >>> from py2deb import PackageConverter
        >>> converter = PackageConverter()
        >>> converter.convert(['py2deb'])
        ['python-py2deb (=0.1)']

        """
        with TemporaryDirectory(prefix='py2deb-sdists-') as sources_directory:
            primary_packages = []
            # Download, unpack and convert no-yet-converted packages.
            for package in self.get_source_distributions(pip_install_arguments, sources_directory):
                if package.requirement.is_direct:
                    primary_packages.append(package)
                if package.existing_archive:
                    logger.info("Package %s (%s) already converted: %s",
                                package.python_name, package.python_version,
                                package.existing_archive.filename)
                else:
                    package.convert()
            # Tell the caller how to depend on the converted packages.
            dependencies_to_report = []
            for package in primary_packages:
                dependency = '%s (=%s)' % (package.debian_name, package.debian_version)
                dependencies_to_report.append(dependency)
            return sorted(dependencies_to_report)

    def get_source_distributions(self, pip_install_arguments, build_directory):
        """
        Use :py:mod:`pip_accel` to download and unpack Python source distributions.

        Retries several times if a download fails (so it doesn't fail
        immediately when a package index server returns a transient error).

        :param pip_install_arguments: The command line arguments to the ``pip
                                      install`` command.
        :param build_directory: The pathname of a build directory (a string).
        :returns: A generator of :py:class:`PackageToConvert` objects.
        :raises: When downloading fails even after several retries this
                 function raises :py:exc:`pip.exceptions.DistributionNotFound`.
                 This function can also raise other exceptions raised by pip
                 because it uses :py:mod:`pip_accel` to call pip (as a Python
                 API).
        """
        # Compose the `pip install' command line:
        #  - The command line arguments to `py2deb' are the command line
        #    arguments to `pip install'. Since it doesn't make any sense for
        #    users of `py2deb' to type out commands like `py2deb install ...'
        #    we'll have to fill in the `install' command ourselves.
        #  - We depend on `pip install --ignore-installed ...' so we can
        #    guarantee that all of the packages specified by the caller are
        #    converted, instead of only those not currently installed somewhere
        #    where pip can see them (a poorly defined concept to begin with).
        pip_install_arguments = ['install', '--ignore-installed'] + list(pip_install_arguments)
        # Make sure pip-accel has been properly initialized.
        initialize_directories()
        # Loop to retry downloading source packages a couple of times (so
        # we don't fail immediately when a package index server returns a
        # transient error).
        for i in range(1, self.max_download_attempts):
            try:
                for requirement in unpack_source_dists(pip_install_arguments, build_directory):
                    yield PackageToConvert(self, requirement)
                return
            except DistributionNotFound:
                logger.warning("We don't have all source distributions yet!")
                download_source_dists(pip_install_arguments, build_directory)
        msg = "Failed to download source distribution archive(s)! (tried %i times)"
        raise DistributionNotFound(msg % self.max_download_attempts)

    def transform_name(self, python_package_name):
        """
        Transform Python package name to Debian package name.

        :param python_package_name: The name of a Python package
                                    as found on PyPI (a string).
        :returns: The transformed name (a string).

        Examples:

        >>> from py2deb import PackageConverter
        >>> converter = PackageConverter()
        >>> converter.transform_name('example')
        'python-example'
        >>> converter.set_name_prefix('my-custom-prefix')
        >>> converter.transform_name('example')
        'my-custom-prefix-example'
        """
        # Check for an override by the caller.
        debian_package_name = self.name_mapping.get(python_package_name.lower())
        if not debian_package_name:
            # No override. Make something up :-).
            debian_package_name = '%s-%s' % (self.name_prefix, python_package_name)
            debian_package_name = normalize_package_name(debian_package_name)
            debian_package_name = '-'.join(compact_repeating_words(debian_package_name.split('-')))
        # Always normalize the package name (even if it was given to us by the caller).
        return normalize_package_name(debian_package_name)

    @cached_property
    def debian_architecture(self):
        """
        Find Debian architecture of current environment.

        Uses the external command ``uname --machine``.

        :raises: If the output of the command is not recognized
                 :py:exc:`Exception` is raised.
        :returns: The Debian architecture (a string like ``i386`` or ``amd64``).
        """
        architecture = execute('uname', '--machine', capture=True, logger=logger)
        if architecture == 'i686':
            return 'i386'
        elif architecture == 'x86_64':
            return 'amd64'
        else:
            msg = "The current architecture is not supported by py2deb! (architecture reported by uname -m: %s)"
            raise Exception(msg % architecture)


class PackageToConvert(object):

    """
    Abstraction for Python packages to be converted to Debian packages.

    Contains a :py:class:`pip_accel.req.Requirement` object, has a back
    reference to the :py:class:`PackageConverter` and provides all of the
    Debian package metadata implied by the Python package metadata.
    """

    def __init__(self, converter, requirement):
        """
        Initialize a package to convert.

        :param converter: The :py:class:`PackageConverter` that holds the user
                          options and knows how to transform package names.
        :param requirement: A :py:class:`pip_accel.req.Requirement` object
                            (created by :py:func:`PackageConverter.get_source_distributions()`).
        """
        self.converter = converter
        self.requirement = requirement

    @property
    def python_name(self):
        """
        The name of the Python package (a string).
        """
        return self.requirement.name

    @cached_property
    def debian_name(self):
        """
        The name of the converted Debian package (a string).
        """
        return self.converter.transform_name(self.python_name)

    @property
    def python_version(self):
        """
        The version of the Python package (a string).
        """
        return self.requirement.version

    @property
    def debian_version(self):
        """
        The version of the Debian package (a string).
        """
        return self.requirement.version

    @cached_property
    def debian_maintainer(self):
        """
        Get the package maintainer's name and e-mail address.

        The name and e-mail address are combined into a single string that can
        be embedded in a Debian package.
        """
        maintainer = self.metadata.maintainer
        maintainer_email = self.metadata.maintainer_email
        if not maintainer:
            maintainer = self.metadata.author
            maintainer_email = self.metadata.author_email
        if maintainer and maintainer_email:
            return '%s <%s>' % (maintainer, maintainer_email.strip('<>'))
        else:
            return maintainer or 'Unknown'

    @cached_property
    def debian_description(self):
        """
        Python package description converted to Debian package description.

        Converts and reformats the Python package's description so that it can
        be used as the description of a Debian binary package. The conversion
        process works as follows:

        1. The Python package's description is run through Docutils_ to convert
           reStructuredText_ to HTML, because reStructuredText is the de facto
           standard in the Python community and because it's a fairly sensible
           superset of plain text.

        2. The html2text_ package is used to convert the HTML back to plain
           text without all of the line noise inherent in reStructuredText.
           Actually html2text doesn't convert to plain text, it converts to
           Markdown_, but Markdown is a lot closer to plain text than
           reStructuredText is :-)

        3. The output of html2text is massaged slightly to improve its
           appearance.

        4. The resulting text is converted to the format expected to be used in
           Debian control files (all lines are indented and empty lines are
           replaced with a dot).

        5. Finally a tag like `Packaged by py2deb on June 5, 2014 at 18:42` is
           appended to the end of the description.

        .. _Docutils: https://pypi.python.org/pypi/docutils
        .. _html2text: https://pypi.python.org/pypi/html2text
        .. _Markdown: http://daringfireball.net/projects/markdown/
        .. _reStructuredText: http://docutils.sourceforge.net/rst.html
        """
        description = self.metadata.description or ''
        # Use docutils to convert the (assumed to be) reStructuredText input
        # text to UTF-8 encoded HTML and decode that to a Unicode string.
        # UTF-8 is the documented default output encoding of docutils:
        # http://docutils.sourceforge.net/docs/api/publisher.html#encodings
        html_text = publish_string(description, writer=Writer()).decode('UTF-8')
        # Convert the HTML to human friendly plain text. This is a very lossy
        # conversion but that's not all that relevant given our context...
        converter = HTML2Text()
        converter.ignore_links = True
        converter.ignore_images = True
        plain_text = converter.handle(html_text)
        # I have almost nothing to complain about html2text except that it
        # sometimes emits repeating empty lines (ignoring whitespace).
        lines = []
        for line in plain_text.splitlines():
            if line and not line.isspace():
                lines.append(line.rstrip())
            elif not (lines and lines[-1] == ''):
                lines.append('')
        # Join the lines back together and strip any leading and/or trailing
        # whitespace (this will also remove a possible empty trailing line).
        description = '\n'.join(lines).strip()
        # Most descriptions will start with a level one Markdown heading which
        # looks a bit weird given that the first line of a Debian package's
        # description is the synopsis, so let's remove the `#' marker.
        description = description.lstrip('#').lstrip()
        # Tag the description with a reference to py2deb and the date/time when
        # the package was converted.
        tag = ' '.join(time.strftime('Packaged by py2deb on %B %e, %Y at %H:%M.').split())
        if description:
            description += '\n\n' + tag
        else:
            description = tag
        # Replace empty lines in the description with a dot and indent all
        # lines to make the description compatible with the control file
        # format. It's a shame that the deb822 package won't do this...
        lines = description.splitlines()
        for i, line in enumerate(lines):
            if line and not line.isspace():
                lines[i] = ' ' + line
            else:
                lines[i] = ' .'
        # Join the lines back together.
        return '\n'.join(lines)

    @cached_property
    def metadata(self):
        """
        Get the Python package metadata.

        The metadata is loaded from the ``PKG-INFO`` file generated by ``pip``
        when it unpacked the source distribution archive. Results in a
        pkginfo.UnpackedSDist_ object.

        .. _pkginfo.UnpackedSDist: http://pythonhosted.org//pkginfo/distributions.html#introspecting-unpacked-source-distributions
        """
        return UnpackedSDist(self.find_egg_info_file())

    @cached_property
    def has_custom_install_prefix(self):
        """
        Check whether package is being installed under custom installation prefix.

        :returns: ``True`` if the package is being installed under a custom
                  installation prefix, ``False`` otherwise.

        A custom installation prefix is an installation prefix whose ``bin``
        directory is (likely) not available on the default executable search
        path (the environment variable ``$PATH``)
        """
        return self.converter.install_prefix not in KNOWN_INSTALL_PREFIXES

    @cached_property
    def python_requirements(self):
        """
        Find requirements of Python package.

        :returns: A list of :py:class:`pkg_resources.Requirement` objects, read
                  from the ``requires.txt`` file generated by pip when it
                  unpacks a source distribution archive.
        """
        requirements = []
        filename = self.find_egg_info_file('requires.txt')
        if filename:
            with open(filename) as handle:
                for line in handle:
                    line = line.strip()
                    # Stop at extra requirements (optional dependencies).
                    # TODO Is it actually correct to just skip these?
                    if line.startswith('['):
                        break
                    elif line:
                        requirements.append(Requirement.parse(line))
        logger.debug("Python requirements of %s (%s): %r", self.python_name, self.python_version, requirements)
        return requirements

    @cached_property
    def debian_dependencies(self):
        """
        Find Debian dependencies of Python package.

        :returns: A list with Debian package relationships (strings) in the
                  format of the ``Depends:`` line of a Debian package
                  ``control`` file. Based on :py:data:`python_requirements`.
        """
        # Useful link:
        # http://www.python.org/dev/peps/pep-0440/#version-specifiers
        dependencies = []
        for requirement in self.python_requirements:
            debian_package_name = self.converter.transform_name(requirement.project_name)
            if requirement.specs:
                for constraint, version in requirement.specs:
                    if constraint == '==':
                        dependencies.append('%s (= %s)' % (debian_package_name, version))
                    elif constraint == '!=':
                        values = (debian_package_name, version, debian_package_name, version)
                        dependencies.append('%s (<< %s) | %s (>> %s)' % values)
                    elif constraint == '<':
                        dependencies.append('%s (<< %s)' % (debian_package_name, version))
                    elif constraint == '>':
                        dependencies.append('%s (>> %s)' % (debian_package_name, version))
                    elif constraint in ('<=', '>='):
                        dependencies.append('%s (%s %s)' % (debian_package_name, constraint, version))
                    else:
                        msg = "Conversion specifier not supported! (%r used by Python package %s)"
                        raise Exception(msg % (constraint, self.python_name))
        dependencies = sorted(dependencies)
        logger.debug("Debian dependencies of %s (%s): %r", self.debian_name, self.debian_version, dependencies)
        return dependencies

    @cached_property
    def existing_archive(self):
        """
        Find ``*.deb`` archive for current package name and version.

        :returns: The pathname of the found archive (a string) or ``None`` if
                  no existing archive is found.
        """
        return (self.converter.repository.find_package(self.debian_name, self.debian_version, 'all') or
                self.converter.repository.find_package(self.debian_name, self.debian_version,
                                                       self.converter.debian_architecture))

    def convert(self):
        """
        Convert current package from Python package to Debian package.

        :returns: The pathname of the generated ``*.deb`` archive.
        """
        sanity_check_dependencies(self.python_name, self.converter.auto_install)
        with TemporaryDirectory(prefix='py2deb-build-') as build_directory:

            # Unpack the binary distribution archive provided by pip-accel inside our build directory.
            build_install_prefix = os.path.join(build_directory, self.converter.install_prefix.lstrip('/'))
            install_binary_dist(members=self.transform_binary_dist(),
                                prefix=build_install_prefix,
                                python='/usr/bin/%s' % find_python_version(),
                                enable_workarounds=False)

            # Execute a user defined command inside the directory where the Python modules are installed.
            command = self.converter.scripts.get(self.python_name.lower())
            if command:
                if self.has_custom_install_prefix:
                    lib_directory = os.path.join(build_install_prefix, 'lib')
                else:
                    dist_packages = glob.glob(os.path.join(build_install_prefix, 'lib/python*/dist-packages'))
                    if len(dist_packages) != 1:
                        msg = "Expected to find a single 'dist-packages' directory inside converted package!"
                        raise Exception(msg)
                    lib_directory = dist_packages[0]
                execute(command, directory=lib_directory, logger=logger)

            # Determine the package's dependencies, starting with the currently
            # running version of Python and the Python requirements converted
            # to Debian packages.
            dependencies = [find_python_version()] + self.debian_dependencies

            # Check if the converted package contains any compiled *.so files.
            shared_object_files = self.find_shared_object_files(build_directory)
            if shared_object_files:
                # Determine system dependencies by analyzing the linkage of the
                # *.so file(s) found in the converted package.
                dependencies += self.find_system_dependencies(shared_object_files)

            # Make up some control file fields ... :-)
            architecture = self.determine_package_architecture(shared_object_files)
            control_fields = unparse_control_fields(dict(package=self.debian_name,
                                                         version=self.debian_version,
                                                         maintainer=self.debian_maintainer,
                                                         description=self.debian_description,
                                                         architecture=architecture,
                                                         depends=dependencies,
                                                         priority='optional',
                                                         section='python'))

            # Merge any control file fields defined in py2deb.cfg (inside the
            # Python package's source distribution) into the Debian package's
            # control file fields?
            py2deb_cfg = os.path.join(self.requirement.source_directory, 'py2deb.cfg')
            parser = configparser.RawConfigParser()
            parser.read(py2deb_cfg)
            if 'py2deb' in parser.sections():
                overrides = dict(parser.items('py2deb'))
                logger.debug("Found %i control file field override(s) in %s: %r", len(overrides), py2deb_cfg, overrides)
                control_fields = merge_control_fields(control_fields, overrides)

            # Create the DEBIAN directory.
            debian_directory = os.path.join(build_directory, 'DEBIAN')
            os.mkdir(debian_directory)

            # Generate the DEBIAN/control file.
            control_file = os.path.join(debian_directory, 'control')
            logger.debug("Saving control file fields to %s: %s", control_file, control_fields)
            with open(control_file, 'w') as handle:
                control_fields.dump(handle)

            # Install post-installation and pre-removal scripts.
            installation_directory = os.path.dirname(os.path.abspath(__file__))
            scripts_pattern = os.path.join(installation_directory, 'scripts', '*.sh')
            for source in glob.glob(scripts_pattern):
                script, extension = os.path.splitext(os.path.basename(source))
                target = os.path.join(debian_directory, script)
                # Read the shell script bundled with py2deb.
                with open(source) as handle:
                    contents = list(handle)
                if script == 'postinst':
                    # Install a program available inside the custom installation
                    # prefix in the system wide executable search path using the
                    # Debian alternatives system.
                    command_template = "update-alternatives --install {link} {name} {path} 0\n"
                    for link, path in self.converter.alternatives:
                        if os.path.isfile(os.path.join(build_directory, path.lstrip('/'))):
                            contents.append(command_template.format(link=pipes.quote(link),
                                                                    name=pipes.quote(os.path.basename(link)),
                                                                    path=pipes.quote(path)))
                elif script == 'prerm':
                    # Cleanup the previously created alternative.
                    command_template = "update-alternatives --remove {name} {path}\n"
                    for link, path in self.converter.alternatives:
                        if os.path.isfile(os.path.join(build_directory, path.lstrip('/'))):
                            contents.append(command_template.format(name=pipes.quote(os.path.basename(link)),
                                                                    path=pipes.quote(path)))
                # Save the shell script in the build directory.
                with open(target, 'w') as handle:
                    for line in contents:
                        handle.write(line)
                # Make sure the shell script is executable.
                os.chmod(target, 0755)

            return build_package(build_directory)

    def transform_binary_dist(self):
        """
        Build Python package and transform directory layout.

        Builds the Python package (using :py:mod:`pip_accel`) and changes the
        names of the files included in the package to match the layout
        corresponding to the given conversion options.

        :returns: An iterable of tuples with two values each:

                  1. A :py:class:`tarfile.TarInfo` object;
                  2. A file-like object.
        """
        for member, handle in get_binary_dist(self.requirement.name,
                                              self.requirement.version,
                                              self.requirement.source_directory):
            if self.has_custom_install_prefix:
                # Strip the complete /usr/lib/pythonX.Y/site-packages/ prefix
                # so we can replace it with the custom installation prefix
                # (at this point /usr/ has been stripped by get_binary_dist()).
                member.name = re.sub(r'lib/python\d+(\.\d+)*/(dist|site)-packages/', 'lib/', member.name)
                # Rewrite executable Python scripts so they know about the
                # custom installation prefix.
                if member.name.startswith('bin/'):
                    lines = handle.readlines()
                    if lines and re.match(r'^#!.*\bpython', lines[0]):
                        i = 0
                        while i < len(lines) and lines[i].startswith('#'):
                            i += 1
                        directory = os.path.join(self.converter.install_prefix, 'lib')
                        lines.insert(i, 'import sys; sys.path.insert(0, %r)\n' % directory)
                        handle = StringIO(''.join(lines))
            else:
                # Rewrite /site-packages/ to /dist-packages/. For details see
                # https://wiki.debian.org/Python#Deviations_from_upstream.
                member.name = member.name.replace('/site-packages/', '/dist-packages/')
            yield member, handle

    def find_shared_object_files(self, directory):
        """
        Search directory tree of converted package for shared object files.

        Runs ``strip --strip-unneeded`` on all ``*.so`` files found.

        :param directory: The directory to search (a string).
        :returns: A :py:class:`list` with pathnames of ``*.so`` files.
        """
        shared_object_files = []
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if filename.endswith('.so'):
                    pathname = os.path.join(root, filename)
                    shared_object_files.append(pathname)
                    execute('strip', '--strip-unneeded', pathname, logger=logger)
        if shared_object_files:
            logger.debug("Found one or more shared object files: %s", shared_object_files)
        return shared_object_files

    def find_system_dependencies(self, shared_object_files):
        """
        (Ab)use dpkg-shlibdeps_ to find dependencies on system libraries.

        :param shared_object_files: The pathnames of the ``*.so`` file(s) contained
                                    in the package (a list of strings).
        :returns: A list of strings in the format of the entries on the
                  ``Depends:`` line of a binary package control file.

        .. _dpkg-shlibdeps: https://www.debian.org/doc/debian-policy/ch-sharedlibs.html#s-dpkg-shlibdeps
        """
        logger.debug("Abusing `dpkg-shlibdeps' to find dependencies on shared libraries ..")
        # Create a fake source package, because `dpkg-shlibdeps' expects this...
        with TemporaryDirectory(prefix='py2deb-dpkg-shlibdeps-') as fake_source_directory:
            # Create the debian/ directory expected in the source package directory.
            os.mkdir(os.path.join(fake_source_directory, 'debian'))
            # Create an empty debian/control file because `dpkg-shlibdeps' requires
            # this (even though it is apparently fine for the file to be empty ;-).
            open(os.path.join(fake_source_directory, 'debian', 'control'), 'w').close()
            # Run `dpkg-shlibdeps' inside the fake source package directory, but
            # let it analyze the *.so files from the actual build directory.
            command = ['dpkg-shlibdeps', '-O', '--warnings=0'] + shared_object_files
            output = execute(*command, directory=fake_source_directory, capture=True, logger=logger)
            expected_prefix = 'shlibs:Depends='
            if not output.startswith(expected_prefix):
                msg = ("The output of dpkg-shlibdeps doesn't match the"
                       " expected format! (expected prefix: %r, output: %r)")
                logger.warning(msg, expected_prefix, output)
                return []
            output = output[len(expected_prefix):]
            dependencies = sorted(d.strip() for d in output.split(','))
            logger.debug("Dependencies reported by dpkg-shlibdeps: %s", dependencies)
            return dependencies

    def determine_package_architecture(self, has_shared_object_files):
        """
        Determine binary architecture that Debian package should be tagged with.

        If a package contains ``*.so`` files we're dealing with a compiled
        Python module. To determine the applicable architecture, we simply take
        the architecture of the current system and (for now) ignore the
        existence of cross-compilation.

        :param has_shared_objects: ``True`` if the package contains ``*.so`` files.
        :returns: The architecture string, one of 'all', 'i386' or 'amd64'.
        """
        logger.debug("Checking package architecture ..")
        if has_shared_object_files:
            if sys.maxsize > 2**32:
                logger.debug("We're running on a 64 bit host -> assuming package is also 64 bit.")
                return 'amd64'
            else:
                logger.debug("We're running on a 32 bit host -> assuming package is also 32 bit.")
                return 'i386'
        else:
            logger.debug("The package's binary distribution doesn't contain any shared"
                         " object files -> we must be dealing with a portable package.")
            return 'all'

    def find_egg_info_file(self, pattern=''):
        """
        Find pip metadata files in unpacked source distributions.

        When pip unpacks a source distribution archive it creates a directory
        ``pip-egg-info`` which contains the package metadata in a declarative
        and easy to parse format. This method finds such metadata files.

        :param pattern: The :py:mod:`glob` pattern to search for (a string).
        :returns: A list of matched filenames (strings).
        """
        full_pattern = os.path.join(self.requirement.source_directory, 'pip-egg-info', '*.egg-info', pattern)
        logger.debug("Looking for %r file(s) using pattern %r ..", pattern, full_pattern)
        matches = glob.glob(full_pattern)
        if len(matches) > 1:
            msg = "Source distribution directory of %s (%s) contains multiple *.egg-info directories: %s"
            raise Exception(msg % (self.requirement.project_name, self.requirement.version, concatenate(matches)))
        elif matches:
            logger.debug("Matched %s: %s.", pluralize(len(matches), "file", "files"), concatenate(matches))
            return matches[0]
        else:
            logger.debug("No matching %r files found.", pattern)


class PackageRepository(object):

    """
    Very simply abstraction for a directory containing ``*.deb`` archives.
    """

    def __init__(self, directory):
        """
        Initialize a :py:class:`PackageRepository` object.

        :param directory: The pathname of the directory containing ``*.deb``
                          archives (a string).
        """
        self.directory = directory

    @cached_property
    def archives(self):
        """
        Find archive(s) in package repository / directory.

        :returns: A sorted list of package archives, same as the return value
                  of :py:func:`deb_pkg_tools.package.find_package_archives()`.

        An example:

        >>> from py2deb import PackageRepository
        >>> repo = PackageRepository('/tmp')
        >>> repo.archives
        [PackageFile(name='py2deb', version='0.1', architecture='all',
                     filename='/tmp/py2deb_0.1_all.deb'),
         PackageFile(name='py2deb-cached-property', version='0.1.5', architecture='all',
                     filename='/tmp/py2deb-cached-property_0.1.5_all.deb'),
         PackageFile(name='py2deb-chardet', version='2.2.1', architecture='all',
                     filename='/tmp/py2deb-chardet_2.2.1_all.deb'),
         PackageFile(name='py2deb-coloredlogs', version='0.5', architecture='all',
                     filename='/tmp/py2deb-coloredlogs_0.5_all.deb'),
         PackageFile(name='py2deb-deb-pkg-tools', version='1.20.4', architecture='all',
                     filename='/tmp/py2deb-deb-pkg-tools_1.20.4_all.deb'),
         PackageFile(name='py2deb-docutils', version='0.11', architecture='all',
                     filename='/tmp/py2deb-docutils_0.11_all.deb'),
         PackageFile(name='py2deb-executor', version='1.2', architecture='all',
                     filename='/tmp/py2deb-executor_1.2_all.deb'),
         PackageFile(name='py2deb-html2text', version='2014.4.5', architecture='all',
                     filename='/tmp/py2deb-html2text_2014.4.5_all.deb'),
         PackageFile(name='py2deb-humanfriendly', version='1.8.2', architecture='all',
                     filename='/tmp/py2deb-humanfriendly_1.8.2_all.deb'),
         PackageFile(name='py2deb-pkginfo', version='1.1', architecture='all',
                     filename='/tmp/py2deb-pkginfo_1.1_all.deb'),
         PackageFile(name='py2deb-python-debian', version='0.1.21-nmu2', architecture='all',
                     filename='/tmp/py2deb-python-debian_0.1.21-nmu2_all.deb'),
         PackageFile(name='py2deb-six', version='1.6.1', architecture='all',
                     filename='/tmp/py2deb-six_1.6.1_all.deb')]

        """
        return find_package_archives(self.directory)

    def find_package(self, package, version, architecture):
        """
        Find a package in the repository.

        Here's an example:

        >>> from py2deb import PackageRepository
        >>> repo = PackageRepository('/tmp')
        >>> repo.find_package('py2deb', '0.1', 'all')
        PackageFile(name='py2deb', version='0.1', architecture='all', filename='/tmp/py2deb_0.1_all.deb')

        :param package: The name of the package (a string).
        :param version: The version of the package (a string).
        :param architecture: The architecture of the package (a string).
        :returns: A :py:class:`deb_pkg_tools.package.PackageFile` object
                  or ``None``.
        """
        for a in self.archives:
            if a.name == package and a.version == version and a.architecture == architecture:
                return a


class TemporaryDirectory(object):

    """
    Easy temporary directory creation & cleanup using the :keyword:`with` statement.

    Here's an example of how to use this:

    .. code-block:: python

       with TemporaryDirectory() as directory:
           # Do something useful here.
           assert os.path.isdir(directory)
    """

    def __init__(self, **options):
        """
        Initialize context manager that manages creation & cleanup of temporary directory.

        :param options: Any keyword arguments are passed on to
                        :py:func:`tempfile.mkdtemp()`.
        """
        self.options = options

    def __enter__(self):
        """
        Create the temporary directory.
        """
        self.temporary_directory = tempfile.mkdtemp(**self.options)
        logger.debug("Created temporary directory: %s", self.temporary_directory)
        return self.temporary_directory

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Destroy the temporary directory.
        """
        logger.debug("Cleaning up temporary directory: %s", self.temporary_directory)
        shutil.rmtree(self.temporary_directory)
        del self.temporary_directory


def find_python_version():
    """
    Find the version of Python we're running.

    This specifically returns a name matching the format of the names of the
    Debian packages providing the various available Python versions.

    :returns: A string like ``python2.6`` or ``python2.7``.
    """
    python_version = 'python%d.%d' % (sys.version_info[0], sys.version_info[1])
    logger.debug("Detected Python version: %s", python_version)
    return python_version


def normalize_package_name(python_package_name):
    """
    Normalize Python package name to be used as Debian package name.

    >>> from py2deb import normalize_package_name
    >>> normalize_package_name('MySQL-python')
    'mysql-python'

    :param python_package_name: The name of a Python package
                                as found on PyPI (a string).
    :returns: The normalized name (a string).
    """
    return re.sub('[^a-z0-9]+', '-', python_package_name.lower()).strip('-')


def compact_repeating_words(words):
    """
    Remove adjacent repeating words.

    This is used to avoid awkward word repetitions in the package name
    conversion algorithm. Here's an example of what I mean:

    >>> from py2deb import compact_repeating_words
    >>> name_prefix = 'python'
    >>> package_name = 'python-mcrypt'
    >>> combined_words = [name_prefix] + package_name.split('-')
    >>> print combined_words
    ['python', 'python', 'mcrypt']
    >>> compacted_words = compact_repeating_words(combined_words)
    >>> print compacted_words
    ['python', 'mcrypt']

    :param words: A list of words (strings), assumed to already be normalized
                  (lowercased).
    :returns: The list of words with adjacent repeating words replaced by a
              single word.
    """
    i = 0
    while i < len(words):
        if i + 1 < len(words) and words[i] == words[i + 1]:
            words.pop(i)
        else:
            i += 1
    return words

# vim: ts=4 sw=4
