# py2deb: Python to Debian package converter.
#
# Authors:
#  - Arjan Verwer
#  - Peter Odding <peter.odding@paylogic.com>
# Last Change: June 7, 2014
# URL: https://py2deb.readthedocs.org

"""
The :py:mod:`py2deb.package` module contains the low level conversion logic.

This module defines the :py:class:`PackageToConvert` class which implements the
low level logic of converting a single Python package to a Debian package. The
separation between the :py:class:`py2deb.converter.PackageConverter` and
:py:class:`py2deb.package.PackageToConvert` classes is somewhat crude (because
neither class can work without the other) but the idea is to separate the high
level conversion logic from the low level conversion logic.
"""

# Standard library modules.
import glob
import logging
import os
import pipes
import re
import sys
import time

# External dependencies.
from cached_property import cached_property
from deb_pkg_tools.control import merge_control_fields, unparse_control_fields
from deb_pkg_tools.package import build_package
from docutils.core import publish_string
from docutils.writers.html4css1 import Writer
from executor import execute
from html2text import HTML2Text
from humanfriendly import concatenate, pluralize
from pip_accel import install_binary_dist
from pip_accel.bdist import get_binary_dist
from pip_accel.deps import sanity_check_dependencies
from pkg_resources import Requirement
from pkginfo import UnpackedSDist
from six.moves import configparser, StringIO

# Modules included in our package.
from py2deb.utils import find_python_version, TemporaryDirectory

# Initialize a logger.
logger = logging.getLogger(__name__)

# The following installation prefixes are known to contain a `bin' directory
# that's available on the default executable search path (the environment
# variable $PATH).
KNOWN_INSTALL_PREFIXES = ('/usr', '/usr/local')


class PackageToConvert(object):

    """
    Abstraction for Python packages to be converted to Debian packages.

    Contains a :py:class:`pip_accel.req.Requirement` object, has a back
    reference to the :py:class:`py2deb.converter.PackageConverter` and provides
    all of the Debian package metadata implied by the Python package metadata.
    """

    def __init__(self, converter, requirement):
        """
        Initialize a package to convert.

        :param converter: The :py:class:`py2deb.converter.PackageConverter`
                          that holds the user options and knows how to
                          transform package names.
        :param requirement: A :py:class:`pip_accel.req.Requirement` object
                            (created by :py:func:`py2deb.converter.PackageConverter.get_source_distributions()`).
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

        3. The output of html2text is modified slightly to improve its
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
        description = description + '\n\n' + tag if description else tag
        # Replace empty lines in the description with a dot and indent all
        # lines to make the description compatible with the control file
        # format. It's a shame that the deb822 package won't do this...
        return '\n'.join('  ' + line if line and not line.isspace() else ' .'
                         for line in description.splitlines())

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
                selected_extras = set(e.lower() for e in self.requirement.pip_requirement.extras)
                current_extra = None
                for lnum, line in enumerate(handle, start=1):
                    line = line.strip()
                    if line.startswith('['):
                        current_extra = line.strip('[]').lower()
                    elif line and (current_extra is None or current_extra in selected_extras):
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
            else:
                dependencies.append(debian_package_name)
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

            # Merge any control file fields defined in stdeb.cfg (inside the
            # Python package's source distribution) into the Debian package's
            # control file fields?
            py2deb_cfg = os.path.join(self.requirement.source_directory, 'stdeb.cfg')
            parser = configparser.RawConfigParser()
            parser.read(py2deb_cfg)
            for section_name in ('DEFAULT', self.python_name):
                if parser.has_section(section_name):
                    overrides = dict(parser.items(section_name))
                    logger.debug("Found %i control file field override(s) in section %s of %s: %r",
                                 len(overrides), section_name, py2deb_cfg, overrides)
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
        :returns: A list with pathnames of ``*.so`` files.
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
            dependencies = sorted(dependency.strip() for dependency in output.split(','))
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


# vim: ts=4 sw=4
