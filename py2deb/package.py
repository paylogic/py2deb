# vim: fileencoding=utf-8

"""
py2deb.package: Model of a Python → Debian package during conversion
====================================================================
"""

# From http://www.debian.org/doc/debian-policy/ch-relationships.html#s-virtual:
#
#   If a relationship field has a version number attached, only real packages
#   will be considered to see whether the relationship is satisfied (or the
#   prohibition violated, for a conflict or breakage). In other words, if a
#   version number is specified, this is a request to ignore all Provides for
#   that package name and consider only real packages. The package manager will
#   assume that a package providing that virtual package is not of the "right"
#   version. A Provides field may not contain version numbers, and the version
#   number of the concrete package which provides a particular virtual package
#   will not be considered when considering a dependency on or conflict with
#   the virtual package name.

# Standard library modules.
import ConfigParser
import glob
import logging
import os
import re
import StringIO

# External dependencies.
from pkg_resources import Requirement
from humanfriendly import concatenate, pluralize

# Internal modules.
from py2deb.util import find_architecture, transform_package_name

# Initialize the logger.
logger = logging.getLogger(__name__)

class Package:

    """
    Wrapper for Python packages that will be converted to Debian packages.
    """

    def __init__(self, name, version, directory, name_mapping, name_prefix, install_prefix, replacements):
        self.name = name.lower()
        self.version = version
        self.directory = os.path.abspath(directory)
        self.name_mapping = name_mapping
        self.name_prefix = name_prefix
        self.is_isolated_package = bool(install_prefix)
        self.replacements = replacements
        self.debian_name = transform_package_name(self.name_prefix, self.name, self.is_isolated_package, self.name_mapping)
        self.py_requirements = self.python_requirements or []

    def __repr__(self):
        """
        Return a textual representation of the Package object.
        """
        return "Package(name=%r, version=%r)" % (self.name, self.version)

    @property
    def metadata(self):
        """
        Return package metadata loaded from the ``PKG-INFO`` file.
        """
        parser = ConfigParser.RawConfigParser()
        for filename in self.find_egg_info_files('PKG-INFO'):
            logger.debug("Reading package metadata from %s ..", filename)
            fp = StringIO.StringIO()
            fp.write('[DEFAULT]\n')
            with open(filename) as handle:
                fp.write(handle.read())
            fp.seek(0)
            try:
                parser.readfp(fp)
            except Exception, e:
                logger.warn("Failed to read package metadata: %s", e)
        fields = {}
        for name, value in parser.items('DEFAULT'):
            fields[name.lower()] = value
        return fields

    @property
    def python_requirements(self):
        """
        Returns a list of :py:class:`pkg_resources.Requirement` objects.
        """
        requirements = []
        # The file `requires.txt' contains the Python package requirements.
        for filename in self.find_egg_info_files('requires.txt'):
            with open(filename) as handle:
                for line in handle:
                    line = line.strip()
                    # Stop at extra requirements (optional dependencies).
                    if line.startswith('['):
                        break
                    elif line:
                        requirements.append(Requirement.parse(line))
        logger.debug("Python requirements of %s (%s): %r", self.name, self.version, requirements)
        return requirements

    @property
    def release(self):
        """
        The version number and release number, separated by a dash.
        """
        return "%s-1" % self.version

    @property
    def debian_file_pattern(self):
        """
        Regular expression to find Debian package archives for the Python package.
        """
        return r'^%s_%s_(all|%s)\.deb$' % (re.escape(self.debian_name),
                                           re.escape(self.release),
                                           re.escape(find_architecture()))

    @property
    def py_dependencies(self):
        """
        List of required Python packages.
        """
        return [req.key for req in self.python_requirements]

    @property
    def debian_dependency(self):
        """
        The entry in a Debian package's ``Depends:`` field required to depend
        on the converted package.
        """
        if self.name in self.replacements:
            return self.replacements[self.name]
        else:
            return '%s (=%s)' % (self.debian_name, self.release)

    @property
    def debian_dependencies(self):
        """
        List with required Debian packages of this Python package in the
        format of the ``Depends:`` line as used in Debian package ``control``
        files.
        """
        # Useful link:
        # http://www.python.org/dev/peps/pep-0440/#version-specifiers
        dependencies = []
        for req in self.python_requirements:
            if req.key in self.replacements:
                dependencies.append(self.replacements[req.key])
            else:
                name = transform_package_name(self.name_prefix, req.key, self.is_isolated_package, self.name_mapping)
                if not req.specs:
                    dependencies.append(name)
                else:
                    for constraint, version in req.specs:
                        if constraint == '<':
                            dependencies.append('%s (%s %s)' % (name, '<<', version))
                        elif constraint == '>':
                            dependencies.append('%s (%s %s)' % (name, '>>', version))
                        elif constraint == '==':
                            dependencies.append('%s (%s %s)' % (name, '=', '%s-1' % version))
                        elif constraint == '!=':
                            dependencies.append('%s (%s %s) | %s (%s %s)' %
                                (name, '<<', version, name, '>>', version))
                        else:
                            dependencies.append('%s (%s %s)' % (name, constraint, version))
        dependencies = sorted(dependencies)
        logger.debug("Debian requirements of %s (%s): %r", self.debian_name, self.version, dependencies)
        return dependencies

    def find_egg_info_files(self, pattern):
        """
        When pip unpacks a source distribution it creates a subdirectory
        ``pip-egg-info`` which contains the package's metadata in a declarative
        and easy to parse format. This method finds such metadata files.

        :param pattern: The :py:mod:`glob` pattern to search for (a string).
        :returns: A list of matched filenames (strings).
        """
        full_pattern = os.path.join(self.directory, 'pip-egg-info', '*.egg-info', pattern)
        logger.debug("Looking for `%s' file(s) using pattern %s ..", pattern, full_pattern)
        matches = glob.glob(full_pattern)
        logger.debug("Matched %s: %s", pluralize(len(matches), "file", "files"), concatenate(matches))
        return matches
