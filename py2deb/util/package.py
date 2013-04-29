import glob
import os
import re

from pkg_resources import parse_requirements
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
        self.dependencies = []
        self.debfile = None
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
    
    def is_built(self):
        '''
        Check if a package already exists by checking the package repository.
        '''
        pattern = '%s_%s-1_*.deb' % (self.plname, self.version)
        matches = glob.glob(os.path.join(PKG_REPO, pattern))
        return len(matches) > 0

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
        for dep in self.dependencies:
            deplist.extend(self._depends())

        return deplist

    def _depends(self, dep=None):
        req_list = [x for x in parse_requirements(dep)]
        if not req_list:
            return []

        req = req_list[0] # Always one entry
        name = self._plname(req.key)

        if req.specs:
            return ['%s (%s %s)' % (name, spec[0], spec[1])
                    for spec in req.specs]
        else:
            return [name]
