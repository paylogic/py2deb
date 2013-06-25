# Standard library modules.
import glob
import os

# External dependencies.
import pkg_resources

# Internal modules.
from py2deb.util import transform_package_name

class Package:
    """
    Wrapper for python packages that will get converted to debian packages.
    """
    def __init__(self, name, version, directory, prefix='python'):
        self.name = name.lower()
        self.version = version
        self.directory = os.path.abspath(directory)
        self.prefix = prefix
        
        # Init list of python requirements
        self.py_requirements = self._py_requirements() or []

    def _py_requirements(self):
        """
        Returns a list of pkg_resources.Requirement objects
        """
        # requires.txt contains the python requirements/dependencies
        pattern = os.path.join(self.directory, 'pip-egg-info/*.egg-info/requires.txt')
        matches = glob.glob(pattern)
        if len(matches) == 1:
            with open(matches[0]) as r:
                lines = r.readlines()
                return list(self._parse_requires(lines))
                    
    def _parse_requires(self, lines):
        """
        Parses a list of strings (usually from requires.txt)
        to generate pkg_resources.Requirement objects.
        """
        for line in lines:
            # Skip empty lines
            if not line.strip():
                continue
            # Stop at extra requirements (optional dependencies)
            if line.startswith('['):
                break
            yield pkg_resources.Requirement.parse(line)

    @property
    def debian_name(self):
        """
        Valid debian package name.
        """
        return transform_package_name(self.name, self.prefix)

    @property
    def debian_file_pattern(self):
        """
        Valid debian package name.
        """
        return '%s_%s-1_*.deb' % (self.debian_name, self.version)

    @property
    def py_dependencies(self):
        return [req.key for req in self.py_requirements]

    def debian_dependencies(self, replacements):
        """
        Returns a valid debian "Depends" string containing
        all dependencies of this python package.
        """
        dependencies = []
        for req in self.py_requirements:
            if req.key in replacements:
                dependencies.append(replacements.get(req.key))
            else:
                name = transform_package_name(req.key, self.prefix)
                if not req.specs:
                    dependencies.append(name)
                else:
                    for constraint, version in req.specs:
                        if constraint == '<':
                            dependencies.append('%s (%s %s)' % (name, '<<', version))
                        elif constraint == '>':
                            dependencies.append('%s (%s %s)' % (name, '>>', version))
                        elif constraint == '!=':
                            dependencies.append('%s (%s %s) | %s (%s %s)' %
                                (name, '<<', version, name, '>>', version))
                        else:
                            dependencies.append('%s (%s %s)' % (name, constraint, version))

        return dependencies