# Standard library modules.
import glob
import os

# External dependencies.
from debian.deb822 import Deb822

# Internal modules.
from py2deb.config import PKG_REPO
from py2deb.util import transform_package_name

class Package:
    '''
    Wrapper for python packages which will get converted to debian packages.
    '''
    def __init__(self, name, version, directory):
        self.name = name.lower()
        self.version = version
        self.directory = os.path.abspath(directory)
        self._requirements = []
        self.debdir = None

    @property
    def plname(self):
        '''
        Get the name that the Debian package should have.
        '''
        return transform_package_name(self.name)

    def add_requirement(self, req):
        '''
        Adds a requirement to the list of the requirements of this package
        if it is an instance of pkg_resources.Requirement, else it'll try
        to make it into a Requirement.
        '''
        assert isinstance(req, Requirement)
        self._requirements.append(req)

    @property
    def is_built(self):
        '''
        Check if a package already exists by checking the package repository.
        '''
        return self.debfile is not None

    @property
    def debfile(self):
        pattern = '%s_%s-1_*.deb' % (self.plname, self.version)
        matches = glob.glob(os.path.join(PKG_REPO, pattern))
        matches.sort()
        if matches:
            return matches[-1]

    def control_patch(self):
        '''
        Creates a Deb822 dict used for merging / patching a control file.
        '''
        return Deb822(dict(Depends=', '.join(self.depends_list())))

    def depends_list(self):
        '''
        Get a list of dependencies in the format of a Depends field of a Debian control file.
        '''
        dependencies = []
        for requirement in self._requirements:
            dependencies.extend(requirement.debian_dependencies)
        return dependencies

class Requirement:

    '''
    Abstract base class to support isinstance() on both Python and
    Debian requirement objects.
    '''

    @property
    def debian_dependencies(self):
        raise Exception, "Not implemented!"

class PythonRequirement(Requirement):

    '''
    Requirement on Python package.
    '''

    def __init__(self, requirement):
        self.req = requirement

    @property
    def debian_dependencies(self):
        '''
        Report the Debian style dependency for this package.
        '''
        name = transform_package_name(self.req.key)
        dependencies = []
        if not self.req.specs:
            dependencies.append(name)
        else:
            for constraint, version in self.req.specs:
                dependencies.append('%s (%s %s)' % (name, constraint, version))
        return dependencies

class DebianRequirement(Requirement):

    '''
    Requirement on Debian package.
    '''

    def __init__(self, package_name):
        self.upstream_package = package_name

    @property
    def debian_dependencies(self):
        '''
        Report the Debian style dependency for this package.
        '''
        return [self.upstream_package]
