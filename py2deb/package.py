# py2deb: Python to Debian package converter.
#
# Authors:
#  - Arjan Verwer
#  - Peter Odding <peter.odding@paylogic.com>
# Last Change: August 5, 2020
# URL: https://py2deb.readthedocs.io

"""
The :mod:`py2deb.package` module contains the low level conversion logic.

This module defines the :class:`PackageToConvert` class which implements the
low level logic of converting a single Python package to a Debian package. The
separation between the :class:`.PackageConverter` and :class:`PackageToConvert`
classes is somewhat crude (because neither class can work without the other)
but the idea is to separate the high level conversion logic from the low level
conversion logic.
"""

# Standard library modules.
import glob
import logging
import os
import platform
import re
import sys
import time

# External dependencies.
from deb_pkg_tools.control import merge_control_fields, unparse_control_fields
from deb_pkg_tools.package import build_package, find_object_files, find_system_dependencies, strip_object_files
from executor import execute
from humanfriendly.text import concatenate, pluralize
from pkg_resources import Requirement
from pkginfo import UnpackedSDist
from property_manager import PropertyManager, cached_property
from six import BytesIO
from six.moves import configparser

# Modules included in our package.
from py2deb.namespaces import find_pkgutil_namespaces
from py2deb.utils import (
    TemporaryDirectory,
    detect_python_script,
    embed_install_prefix,
    normalize_package_version,
    package_names_match,
    python_version,
)

# Initialize a logger.
logger = logging.getLogger(__name__)

# The following installation prefixes are known to contain a `bin' directory
# that's available on the default executable search path (the environment
# variable $PATH).
KNOWN_INSTALL_PREFIXES = ('/usr', '/usr/local')


class PackageToConvert(PropertyManager):

    """
    Abstraction for Python packages to be converted to Debian packages.

    Contains a :class:`pip_accel.req.Requirement` object, has a back
    reference to the :class:`.PackageConverter` and provides all of the
    Debian package metadata implied by the Python package metadata.
    """

    def __init__(self, converter, requirement):
        """
        Initialize a package to convert.

        :param converter: The :class:`.PackageConverter` that holds the user
                          options and knows how to transform package names.
        :param requirement: A :class:`pip_accel.req.Requirement` object
                            (created by :func:`~py2deb.converter.PackageConverter.get_source_distributions()`).
        """
        self.converter = converter
        self.requirement = requirement

    @cached_property
    def debian_dependencies(self):
        """
        Find Debian dependencies of Python package.

        Converts `Python version specifiers`_ to `Debian package
        relationships`_.

        :returns: A list with Debian package relationships (strings) in the
                  format of the ``Depends:`` line of a Debian package
                  ``control`` file. Based on :data:`python_requirements`.

        .. _Python version specifiers: http://www.python.org/dev/peps/pep-0440/#version-specifiers
        .. _Debian package relationships: https://www.debian.org/doc/debian-policy/ch-relationships.html
        """
        dependencies = set()
        for requirement in self.python_requirements:
            debian_package_name = self.converter.transform_name(requirement.project_name, *requirement.extras)
            if requirement.specs:
                for constraint, version in requirement.specs:
                    version = self.converter.transform_version(self, requirement.project_name, version)
                    if version == 'dev':
                        # Requirements like 'pytz > dev' (celery==3.1.16) don't
                        # seem to really mean anything to pip (based on my
                        # reading of the 1.4.x source code) but Debian will
                        # definitely complain because version strings should
                        # start with a digit. In this case we'll just fall
                        # back to a dependency without a version specification
                        # so we don't drop the dependency.
                        dependencies.add(debian_package_name)
                    elif constraint == '==':
                        dependencies.add('%s (= %s)' % (debian_package_name, version))
                    elif constraint == '!=':
                        values = (debian_package_name, version, debian_package_name, version)
                        dependencies.add('%s (<< %s) | %s (>> %s)' % values)
                    elif constraint == '<':
                        dependencies.add('%s (<< %s)' % (debian_package_name, version))
                    elif constraint == '>':
                        dependencies.add('%s (>> %s)' % (debian_package_name, version))
                    elif constraint in ('<=', '>='):
                        dependencies.add('%s (%s %s)' % (debian_package_name, constraint, version))
                    else:
                        msg = "Conversion specifier not supported! (%r used by Python package %s)"
                        raise Exception(msg % (constraint, self.python_name))
            else:
                dependencies.add(debian_package_name)
        dependencies = sorted(dependencies)
        logger.debug("Debian dependencies of %s: %r", self, dependencies)
        return dependencies

    @cached_property
    def debian_description(self):
        """
        Get a minimal description for the converted Debian package.

        Includes the name of the Python package and the date at which the
        package was converted.
        """
        text = ["Python package", self.python_name, "converted by py2deb on"]
        # The %e directive (not documented in the Python standard library but
        # definitely available on Linux which is the only platform that py2deb
        # targets, for obvious reasons :-) includes a leading space for single
        # digit day-of-month numbers. I don't like that, fixed width fields are
        # an artefact of 30 years ago and have no place in my software
        # (generally speaking :-). This explains the split/compact duo.
        text.extend(time.strftime('%B %e, %Y at %H:%M').split())
        return ' '.join(text)

    @cached_property
    def debian_maintainer(self):
        """
        Get the package maintainer name and e-mail address.

        The name and e-mail address are combined into a single string that can
        be embedded in a Debian package (in the format ``name <email>``). The
        metadata is retrieved as follows:

        1. If the environment variable ``$DEBFULLNAME`` is defined then its
           value is taken to be the name of the maintainer (this logic was
           added in `#25`_). If ``$DEBEMAIL`` is set as well that will be
           incorporated into the result.

        2. The Python package maintainer name and email address are looked up
           in the package metadata and if found these are used.

        3. The Python package author name and email address are looked up in
           the package metadata and if found these are used.

        4. Finally if all else fails the text "Unknown" is returned.

        .. _#25: https://github.com/paylogic/py2deb/pull/25
        """
        if "DEBFULLNAME" in os.environ:
            maintainer = os.environ["DEBFULLNAME"]
            maintainer_email = os.environ.get("DEBEMAIL")
        elif self.metadata.maintainer:
            maintainer = self.metadata.maintainer
            maintainer_email = self.metadata.maintainer_email
        elif self.metadata.author:
            maintainer = self.metadata.author
            maintainer_email = self.metadata.author_email
        else:
            maintainer = None
            maintainer_email = None
        if maintainer and maintainer_email:
            return '%s <%s>' % (maintainer, maintainer_email.strip('<>'))
        else:
            return maintainer or 'Unknown'

    @cached_property
    def debian_name(self):
        """The name of the converted Debian package (a string)."""
        return self.converter.transform_name(self.python_name, *self.requirement.pip_requirement.extras)

    @cached_property
    def debian_provides(self):
        """
        A symbolic name for the role the package provides (a string).

        When a Python package provides "extras" those extras are encoded into
        the name of the generated Debian package, to represent the additional
        dependencies versus the package without extras.

        However the package including extras definitely also satisfies a
        dependency on the package without extras, so a ``Provides: ...``
        control field is added to the Debian package that contains the
        converted package name *without extras*.
        """
        if self.requirement.pip_requirement.extras:
            return self.converter.transform_name(self.python_name)
        else:
            return ''

    @cached_property
    def debian_version(self):
        """
        The version of the Debian package (a string).

        Reformats :attr:`python_version` using
        :func:`.normalize_package_version()`.
        """
        return normalize_package_version(
            self.python_version, prerelease_workaround=self.converter.prerelease_workaround
        )

    @cached_property
    def existing_archive(self):
        """
        Find ``*.deb`` archive for current package name and version.

        :returns: The pathname of the found archive (a string) or ``None`` if
                  no existing archive is found.
        """
        return self.converter.repository.get_package(
            self.debian_name, self.debian_version, "all"
        ) or self.converter.repository.get_package(
            self.debian_name, self.debian_version, self.converter.debian_architecture
        )

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
    def metadata(self):
        """
        Get the Python package metadata.

        The metadata is loaded from the ``PKG-INFO`` file generated by ``pip``
        when it unpacked the source distribution archive. Results in a
        pkginfo.UnpackedSDist_ object.

        .. _pkginfo.UnpackedSDist: http://pythonhosted.org/pkginfo/distributions.html
        """
        return UnpackedSDist(self.find_egg_info_file())

    @cached_property
    def namespace_packages(self):
        """
        Get the Python `namespace packages`_ defined by the Python package.

        :returns: A list of dotted names (strings).

        When :attr:`setuptools_namespaces` is available that will be used,
        otherwise we fall back to :attr:`pkgutil_namespaces`. This order of
        preference may be switched in the future, but not until
        :attr:`pkgutil_namespaces` has seen more thorough testing:

        - Support for :attr:`setuptools_namespaces` was added to py2deb in
          release 0.22 (2015) so this is fairly mature code that has seen
          thousands of executions between 2015-2020.

        - Support for :attr:`pkgutil_namespaces` was added in August 2020 so
          this is new (and complicated) code that hasn't seen a lot of use yet.
          Out of conservativeness on my part this is nested in the 'else'
          branch (to reduce the scope of potential regressions).

        Additionally computing :attr:`setuptools_namespaces` is very cheap
        (all it has to do is search for and read one text file) compared
        to :attr:`pkgutil_namespaces` (which needs to recursively search
        a directory tree for ``__init__.py`` files and parse each file
        it finds to determine whether it's relevant).

        .. _namespace packages: https://packaging.python.org/guides/packaging-namespace-packages/
        """
        if self.setuptools_namespaces:
            return self.setuptools_namespaces
        else:
            return sorted(set(ns['name'] for ns in self.pkgutil_namespaces))

    @cached_property
    def namespace_style(self):
        """
        Get the style of Python `namespace packages`_ in use by this package.

        :returns: One of the strings ``pkgutil``, ``setuptools`` or ``none``.
        """
        # We check setuptools_namespaces first because it's cheaper and the
        # code has been battle tested (in contrast to pkgutil_namespaces).
        if self.setuptools_namespaces:
            return "setuptools"
        elif self.pkgutil_namespaces:
            return "pkgutil"
        else:
            return "none"

    @cached_property
    def namespaces(self):
        """
        Get the Python `namespace packages`_ defined by the Python package.

        :returns: A list of unique tuples of strings. The tuples are sorted by
                  increasing length (the number of strings in each tuple) so
                  that e.g. ``zope`` is guaranteed to sort before
                  ``zope.app``.

        This property processes the result of :attr:`namespace_packages`
        into a more easily usable format. Here's an example of the difference
        between :attr:`namespace_packages` and :attr:`namespaces`:

        >>> from py2deb.converter import PackageConverter
        >>> converter = PackageConverter()
        >>> package = next(converter.get_source_distributions(['zope.app.cache']))
        >>> package.namespace_packages
        ['zope', 'zope.app']
        >>> package.namespaces
        [('zope',), ('zope', 'app')]

        The value of this property is used by
        :func:`~py2deb.hooks.initialize_namespaces()` and
        :func:`~py2deb.hooks.cleanup_namespaces()` during installation and
        removal of the generated package.
        """
        namespaces = set()
        for namespace_package in self.namespace_packages:
            dotted_name = []
            for component in namespace_package.split('.'):
                dotted_name.append(component)
                namespaces.add(tuple(dotted_name))
        return sorted(namespaces, key=lambda n: len(n))

    @cached_property
    def pkgutil_namespaces(self):
        """
        Namespace packages declared through :mod:`pkgutil`.

        :returns:

          A list of dictionaries similar to those returned by
          :func:`.find_pkgutil_namespaces()`.

        For details about this type of namespace packages please refer to
        <https://packaging.python.org/guides/packaging-namespace-packages/#pkgutil-style-namespace-packages>.

        The implementation of this property lives in a separate module (refer
        to :func:`.find_pkgutil_namespaces()`) in order to compartmentalize the
        complexity of reliably identifying namespace packages defined using
        :mod:`pkgutil`.
        """
        return list(find_pkgutil_namespaces(self.requirement.source_directory))

    @property
    def python_name(self):
        """The name of the Python package (a string)."""
        return self.requirement.name

    @cached_property
    def python_requirements(self):
        """
        Find the installation requirements of the Python package.

        :returns: A list of :class:`pkg_resources.Requirement` objects.

        This property used to be implemented by manually parsing the
        ``requires.txt`` file generated by pip when it unpacks a source
        distribution archive.

        While this implementation was eventually enhanced to supported named
        extras, it never supported environment markers.

        Since then this property has been reimplemented to use
        ``pkg_resources.Distribution.requires()`` so that
        environment markers are supported.

        If the new implementation fails the property falls back to the old
        implementation (as a precautionary measure to avoid unexpected side
        effects of the new implementation).
        """
        try:
            dist = self.requirement.pip_requirement.get_dist()
            extras = self.requirement.pip_requirement.extras
            requirements = list(dist.requires(extras))
        except Exception:
            logger.warning("Failed to determine installation requirements of %s "
                           "using pkg-resources, falling back to old implementation.",
                           self, exc_info=True)
            requirements = self.python_requirements_fallback
        logger.debug("Python requirements of %s: %r", self, requirements)
        return requirements

    @cached_property
    def python_requirements_fallback(self):
        """Fall-back implementation of :attr:`python_requirements`."""
        requirements = []
        filename = self.find_egg_info_file('requires.txt')
        if filename:
            selected_extras = set(extra.lower() for extra in self.requirement.pip_requirement.extras)
            current_extra = None
            with open(filename) as handle:
                for line in handle:
                    line = line.strip()
                    if line.startswith('['):
                        current_extra = line.strip('[]').lower()
                    elif line and (current_extra is None or current_extra in selected_extras):
                        requirements.append(Requirement.parse(line))
        return requirements

    @property
    def python_version(self):
        """The version of the Python package (a string)."""
        return self.requirement.version

    @cached_property
    def setuptools_namespaces(self):
        """
        Namespace packages declared through :pypi:`setuptools`.

        :returns: A list of dotted names (strings).

        For details about this type of namespace packages please refer to
        <https://packaging.python.org/guides/packaging-namespace-packages/#pkg-resources-style-namespace-packages>.
        """
        logger.debug("Searching for pkg_resources-style namespace packages of '%s' ..", self.python_name)
        dotted_names = []
        namespace_packages_file = self.find_egg_info_file('namespace_packages.txt')
        if namespace_packages_file:
            with open(namespace_packages_file) as handle:
                for line in handle:
                    line = line.strip()
                    if line:
                        dotted_names.append(line)
        return dotted_names

    @cached_property
    def vcs_revision(self):
        """
        The VCS revision of the Python package.

        This works by parsing the ``.hg_archival.txt`` file generated by the
        ``hg archive`` command so for now this only supports Python source
        distributions exported from Mercurial repositories.
        """
        filename = os.path.join(self.requirement.source_directory, '.hg_archival.txt')
        if os.path.isfile(filename):
            with open(filename) as handle:
                for line in handle:
                    name, _, value = line.partition(':')
                    if name.strip() == 'node':
                        return value.strip()

    def convert(self):
        """
        Convert current package from Python package to Debian package.

        :returns: The pathname of the generated ``*.deb`` archive.
        """
        with TemporaryDirectory(prefix='py2deb-build-') as build_directory:

            # Prepare the absolute pathname of the Python interpreter on the
            # target system. This pathname will be embedded in the first line
            # of executable scripts (including the post-installation and
            # pre-removal scripts).
            python_executable = '/usr/bin/%s' % python_version()

            # Unpack the binary distribution archive provided by pip-accel inside our build directory.
            build_install_prefix = os.path.join(build_directory, self.converter.install_prefix.lstrip('/'))
            self.converter.pip_accel.bdists.install_binary_dist(
                members=self.transform_binary_dist(python_executable),
                prefix=build_install_prefix,
                python=python_executable,
                virtualenv_compatible=False,
            )

            # Determine the directory (at build time) where the *.py files for
            # Python modules are located (the site-packages equivalent).
            if self.has_custom_install_prefix:
                build_modules_directory = os.path.join(build_install_prefix, 'lib')
            else:
                # The /py*/ pattern below is intended to match both /pythonX.Y/ and /pypyX.Y/.
                dist_packages_directories = glob.glob(os.path.join(build_install_prefix, 'lib/py*/dist-packages'))
                if len(dist_packages_directories) != 1:
                    msg = "Expected to find a single 'dist-packages' directory inside converted package!"
                    raise Exception(msg)
                build_modules_directory = dist_packages_directories[0]

            # Determine the directory (at installation time) where the *.py
            # files for Python modules are located.
            install_modules_directory = os.path.join('/', os.path.relpath(build_modules_directory, build_directory))

            # Execute a user defined command inside the directory where the Python modules are installed.
            command = self.converter.scripts.get(self.python_name.lower())
            if command:
                execute(command, directory=build_modules_directory, logger=logger)

            # Determine the package's dependencies, starting with the currently
            # running version of Python and the Python requirements converted
            # to Debian packages.
            dependencies = [python_version()] + self.debian_dependencies

            # Check if the converted package contains any compiled *.so files.
            object_files = find_object_files(build_directory)
            if object_files:
                # Strip debugging symbols from the object files.
                strip_object_files(object_files)
                # Determine system dependencies by analyzing the linkage of the
                # *.so file(s) found in the converted package.
                dependencies += find_system_dependencies(object_files)

            # Make up some control file fields ... :-)
            architecture = self.determine_package_architecture(object_files)
            control_fields = unparse_control_fields(dict(package=self.debian_name,
                                                         version=self.debian_version,
                                                         maintainer=self.debian_maintainer,
                                                         description=self.debian_description,
                                                         architecture=architecture,
                                                         depends=dependencies,
                                                         provides=self.debian_provides,
                                                         priority='optional',
                                                         section='python'))

            # Automatically add the Mercurial global revision id when available.
            if self.vcs_revision:
                control_fields['Vcs-Hg'] = self.vcs_revision

            # Apply user defined control field overrides from `stdeb.cfg'.
            control_fields = self.load_control_field_overrides(control_fields)

            # Create the DEBIAN directory.
            debian_directory = os.path.join(build_directory, 'DEBIAN')
            os.mkdir(debian_directory)

            # Generate the DEBIAN/control file.
            control_file = os.path.join(debian_directory, 'control')
            logger.debug("Saving control file fields to %s: %s", control_file, control_fields)
            with open(control_file, 'wb') as handle:
                control_fields.dump(handle)

            # Lintian is a useful tool to find mistakes in Debian binary
            # packages however Lintian checks from the perspective of a package
            # included in the official Debian repositories. Because py2deb
            # doesn't and probably never will generate such packages some
            # messages emitted by Lintian are useless (they merely point out
            # how the internals of py2deb work). Because of this we silence
            # `known to be irrelevant' messages from Lintian using overrides.
            if self.converter.lintian_ignore:
                overrides_directory = os.path.join(
                    build_directory, 'usr', 'share', 'lintian', 'overrides',
                )
                overrides_file = os.path.join(overrides_directory, self.debian_name)
                os.makedirs(overrides_directory)
                with open(overrides_file, 'w') as handle:
                    for tag in self.converter.lintian_ignore:
                        handle.write('%s: %s\n' % (self.debian_name, tag))

            # Find the alternatives relevant to the package we're building.
            alternatives = set((link, path) for link, path in self.converter.alternatives
                               if os.path.isfile(os.path.join(build_directory, path.lstrip('/'))))

            # Remove __init__.py files that define "pkgutil-style namespace
            # packages" and let the maintainer scripts generate these files
            # instead. If we don't do this these __init__.py files will cause
            # dpkg file conflicts.
            if self.namespace_style == 'pkgutil':
                for ns in self.pkgutil_namespaces:
                    module_in_build_directory = os.path.join(build_modules_directory, ns['relpath'])
                    logger.debug("Removing pkgutil-style namespace package file: %s", module_in_build_directory)
                    os.remove(module_in_build_directory)

            # Generate post-installation and pre-removal maintainer scripts.
            self.generate_maintainer_script(filename=os.path.join(debian_directory, 'postinst'),
                                            python_executable=python_executable,
                                            function='post_installation_hook',
                                            package_name=self.debian_name,
                                            alternatives=alternatives,
                                            modules_directory=install_modules_directory,
                                            namespaces=self.namespaces,
                                            namespace_style=self.namespace_style)
            self.generate_maintainer_script(filename=os.path.join(debian_directory, 'prerm'),
                                            python_executable=python_executable,
                                            function='pre_removal_hook',
                                            package_name=self.debian_name,
                                            alternatives=alternatives,
                                            modules_directory=install_modules_directory,
                                            namespaces=self.namespaces)

            # Enable a user defined Python callback to manipulate the resulting
            # binary package before it's turned into a *.deb archive (e.g.
            # manipulate the contents or change the package metadata).
            if self.converter.python_callback:
                logger.debug("Invoking user defined Python callback ..")
                self.converter.python_callback(self.converter, self, build_directory)
                logger.debug("User defined Python callback finished!")

            return build_package(directory=build_directory,
                                 check_package=self.converter.lintian_enabled,
                                 copy_files=False)

    def determine_package_architecture(self, has_shared_object_files):
        """
        Determine binary architecture that Debian package should be tagged with.

        If a package contains ``*.so`` files we're dealing with a compiled
        Python module. To determine the applicable architecture, we take the
        Debian architecture reported by
        :attr:`~py2deb.converter.PackageConverter.debian_architecture`.

        :param has_shared_objects: ``True`` if the package contains ``*.so``
                                   files, ``False`` otherwise.
        :returns: The architecture string, 'all' or one of the values of
                  :attr:`~py2deb.converter.PackageConverter.debian_architecture`.
        """
        logger.debug("Checking package architecture ..")
        if has_shared_object_files:
            logger.debug("Package contains shared object files, tagging with %s architecture.",
                         self.converter.debian_architecture)
            return self.converter.debian_architecture
        else:
            logger.debug("Package doesn't contain shared object files, dealing with a portable package.")
            return 'all'

    def find_egg_info_file(self, pattern=''):
        """
        Find pip metadata files in unpacked source distributions.

        When pip unpacks a source distribution archive it creates a directory
        ``pip-egg-info`` which contains the package metadata in a declarative
        and easy to parse format. This method finds such metadata files.

        :param pattern: The :mod:`glob` pattern to search for (a string).
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

    def generate_maintainer_script(self, filename, python_executable, function, **arguments):
        """
        Generate a post-installation or pre-removal maintainer script.

        :param filename: The pathname of the maintainer script (a string).
        :param python_executable: The absolute pathname of the Python
                                  interpreter on the target system (a string).
        :param function: The name of the function in the :mod:`py2deb.hooks`
                         module to be called when the maintainer script is run
                         (a string).
        :param arguments: Any keyword arguments to the function in the
                          :mod:`py2deb.hooks` are serialized and embedded
                          inside the generated maintainer script.
        """
        # Read the py2deb/hooks.py script.
        py2deb_directory = os.path.dirname(os.path.abspath(__file__))
        hooks_script = os.path.join(py2deb_directory, 'hooks.py')
        with open(hooks_script) as handle:
            contents = handle.read()
        blocks = contents.split('\n\n')
        # Generate the shebang / hashbang line.
        blocks.insert(0, '#!%s' % python_executable)
        # Generate the call to the top level function.
        encoded_arguments = ', '.join('%s=%r' % (k, v) for k, v in arguments.items())
        blocks.append('%s(%s)' % (function, encoded_arguments))
        # Write the maintainer script.
        with open(filename, 'w') as handle:
            handle.write('\n\n'.join(blocks))
            handle.write('\n')
        # Make sure the maintainer script is executable.
        os.chmod(filename, 0o755)

    def load_control_field_overrides(self, control_fields):
        """
        Apply user defined control field overrides.

        Looks for an ``stdeb.cfg`` file inside the Python package's source
        distribution and if found it merges the overrides into the control
        fields that will be embedded in the generated Debian binary package.

        This method first applies any overrides defined in the ``DEFAULT``
        section and then it applies any overrides defined in the section whose
        normalized name (see :func:`~py2deb.utils.package_names_match()`)
        matches that of the Python package.

        :param control_fields: The control field defaults constructed by py2deb
                               (a :class:`debian.deb822.Deb822` object).
        :returns: The merged defaults and overrides (a
                  :class:`debian.deb822.Deb822` object).
        """
        py2deb_cfg = os.path.join(self.requirement.source_directory, 'stdeb.cfg')
        if not os.path.isfile(py2deb_cfg):
            logger.debug("Control field overrides file not found (%s).", py2deb_cfg)
        else:
            logger.debug("Loading control field overrides from %s ..", py2deb_cfg)
            parser = configparser.RawConfigParser()
            parser.read(py2deb_cfg)
            # Prepare to load the overrides from the DEFAULT section and
            # the section whose name matches that of the Python package.
            # DEFAULT is processed first on purpose.
            section_names = ['DEFAULT']
            # Match the normalized package name instead of the raw package
            # name because `python setup.py egg_info' normalizes
            # underscores in package names to dashes which can bite
            # unsuspecting users. For what it's worth, PEP-8 discourages
            # underscores in package names but doesn't forbid them:
            # https://www.python.org/dev/peps/pep-0008/#package-and-module-names
            section_names.extend(section_name for section_name in parser.sections()
                                 if package_names_match(section_name, self.python_name))
            for section_name in section_names:
                if parser.has_section(section_name):
                    overrides = dict(parser.items(section_name))
                    logger.debug("Found %i control file field override(s) in section %s of %s: %r",
                                 len(overrides), section_name, py2deb_cfg, overrides)
                    control_fields = merge_control_fields(control_fields, overrides)
        return control_fields

    def transform_binary_dist(self, interpreter):
        """
        Build Python package and transform directory layout.

        :param interpreter: The absolute pathname of the Python interpreter
                            that should be referenced by executable scripts in
                            the binary distribution (a string).
        :returns: An iterable of tuples with two values each:

                  1. A :class:`tarfile.TarInfo` object;
                  2. A file-like object.

        Builds the Python package (using :mod:`pip_accel`) and changes the
        names of the files included in the package to match the layout
        corresponding to the given conversion options.
        """
        # Detect whether we're running on PyPy (it needs special handling).
        if platform.python_implementation() == 'PyPy':
            on_pypy = True
            normalized_pypy_path = 'lib/pypy%i.%i/site-packages/' % sys.version_info[:2]
            if sys.version_info[0] == 3:
                # The file /usr/lib/pypy3/dist-packages/README points to
                # /usr/lib/pypy3/lib-python/3/site.py which states that in
                # PyPy 3 /usr/lib/python3/dist-packages is shared between
                # cPython and PyPy.
                normalized_pypy_segment = '/python3/'
            else:
                # The file /usr/lib/pypy/dist-packages/README points to
                # /usr/lib/pypy/lib-python/2.7/site.py which states that in
                # PyPy 2 /usr/lib/pypy<version>/dist-packages is used for
                # "Debian addons" however when you run the interpreter and
                # inspect sys.path you'll find that /usr/lib/pypy/dist-packages
                # is being used instead of the <version> directory. This might
                # be a documentation bug?
                normalized_pypy_segment = '/pypy/'
        else:
            on_pypy = False
        for member, handle in self.converter.pip_accel.bdists.get_binary_dist(self.requirement):
            is_executable = member.name.startswith('bin/')
            # Note that at this point the installation prefix has already been
            # stripped from `member.name' by the get_binary_dist() method.
            if on_pypy:
                # Normalize PyPy virtual environment layout:
                #
                # 1. cPython uses /lib/pythonX.Y/(dist|site)-packages/
                # 2. PyPy uses /site-packages/ (a top level directory)
                #
                # In this if branch we change 2 to look like 1 so that the
                # following if/else branches don't need to care about the
                # difference.
                member.name = re.sub('^(dist|site)-packages/', normalized_pypy_path, member.name)
            if self.has_custom_install_prefix:
                # Strip the complete /usr/lib/pythonX.Y/site-packages/ prefix
                # so we can replace it with the custom installation prefix.
                member.name = re.sub(r'lib/(python|pypy)\d+(\.\d+)*/(dist|site)-packages/', 'lib/', member.name)
                # Rewrite executable Python scripts so they know about the
                # custom installation prefix.
                if is_executable:
                    handle = embed_install_prefix(handle, os.path.join(self.converter.install_prefix, 'lib'))
            else:
                if on_pypy:
                    # Normalize the PyPy "versioned directory segment" (it differs
                    # between virtual environments versus system wide installations).
                    member.name = re.sub(r'/pypy\d(\.\d)?/', normalized_pypy_segment, member.name)
                # Rewrite /site-packages/ to /dist-packages/. For details see
                # https://wiki.debian.org/Python#Deviations_from_upstream.
                member.name = member.name.replace('/site-packages/', '/dist-packages/')
            # Update the interpreter reference in the first line of executable scripts.
            if is_executable:
                handle = self.update_shebang(handle, interpreter)
            yield member, handle

    def update_shebang(self, handle, interpreter):
        """
        Update the shebang_ of executable scripts.

        :param handle: A file-like object containing an executable.
        :param interpreter: The absolute pathname of the Python interpreter
                            that should be referenced by the script.
        :returns: A file-like object.

        Normally pip-accel is responsible for updating interpreter references
        in executable scripts, however there's a bug in pip-accel where it
        assumes that the string 'python' will appear literally in the shebang
        (which isn't true when running on PyPy).

        .. note:: Of course this bug should be fixed in pip-accel however that
                  project is in limbo while I decide whether to reinvigorate or
                  kill it (the second of which implies needing to make a whole
                  lot of changes to py2deb).

        .. _shebang: https://en.wikipedia.org/wiki/Shebang_(Unix)
        """
        if detect_python_script(handle):
            lines = handle.readlines()
            lines[0] = b'#!' + interpreter.encode('ascii') + b'\n'
            handle = BytesIO(b''.join(lines))
            handle.seek(0)
        return handle

    def __str__(self):
        """The name, version and extras of the package encoded in a human readable string."""
        version = [self.python_version]
        extras = self.requirement.pip_requirement.extras
        if extras:
            version.append("extras: %s" % concatenate(sorted(extras)))
        return "%s (%s)" % (self.python_name, ', '.join(version))
