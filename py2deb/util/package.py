import glob
import os
import re

from pkg_resources import Requirement
from debian.deb822 import Deb822

from py2deb.config import PKG_REPO

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
        return self._plname(self.name)

    def _plname(self, name):
        name = name.lower()
        name = re.sub('^python-', '', name)
        name = re.sub('[^a-z0-9]+', '-', name)
        name = name.strip('-')
        return 'pl-python-' + name

    def add_requirement(self, req):
        '''
        Adds a requirement to the list of the requirements of this package
        if it is an instance of pkg_resources.Requirement, else it'll try 
        to make it into a Requirement.
        '''
        if not isinstance(req, Requirement):
            req = Requirement.parse(req)
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
        Creates a list of dependencies in the format of a Depends field of a control file.
        '''
        deplist = []
        for req in self._requirements:
            name = self._plname(req.key)

            if req.specs:
                deplist.extend(['%s (%s %s)' % (name, spec[0], spec[1])
                        for spec in req.specs])
            else:
                deplist.append(name)

        return deplist
        

        
