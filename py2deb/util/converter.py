import fnmatch
import shutil
import glob
import os

from subprocess import Popen, PIPE, STDOUT
from ConfigParser import ConfigParser
from debian.deb822 import Deb822

from py2deb.config import PKG_REPO, config_dir

class Converter:
    '''
    Converts a list of python packages to debian packages.
    '''

    def __init__(self, builddir):
        self.packages = []
        self.builddir = builddir

        self.config = ConfigParser()
        self.config.read(os.path.join(config_dir, 'control.ini'))

    def convert(self):
        '''
        Start the conversion.
        '''
        for package in self.packages:
            if package.is_built():
                print '%s is already built, skipping...' % (package.plname,)
                continue

            print 'Converting %s-%s ...' % (package.name, package.version)

            self.debianize(package)
            self.parse_egg_req(package)
            self.patch_rules(package)
            self.patch_control(package)
            self.install_build_dep(package)
            self.build(package)

            print 'Converted %s-%s to %s' % (package.name, package.version, package.debfile)

            self.move(package, PKG_REPO)

        print '\nConversion completed!'

        # Temporary print of all built packages as a control depends field
        built_packages = ''
        for pkg in self.packages:
            deplist = pkg.depends_list()

            if not deplist:
                continue

            built_packages += ', '.join(deplist)

        print 'Depends: ' + built_packages

    def debianize(self, package):
        '''
        Debianize a python package using stdeb.
        '''
        os.chdir(package.directory)

        p = Popen(['python', 'setup.py', '--command-packages=stdeb.command', 'debianize'],
                  stdout=PIPE, stderr=STDOUT)
        stddata = p.communicate()

        if p.returncode > 0:
            print stddata[0]
            raise Exception('Failed to debianize %s' % (package.name,))

    def parse_egg_req(self, package):
        '''
        Parse .egg-info/requires.txt for dependencies.
        '''
        pattern = 'pip-egg-info/*.egg-info/requires.txt'
        matches = glob.glob(os.path.join(package.directory, pattern))
        
        if matches == 1:
            with open(matches[0]) as r:
                for line in r.readlines():
                    if not line.strip():
                       continue
                    if line.startswith('['):
                        break

                    package.dependencies.append(line)

    def patch_rules(self, package):
        '''
        Patch rules file to prevent dh_python2 to guess dependencies.
        '''
        patch = '\noverride_dh_python2:\n\tdh_python2 --no-guessing-deps\n'

        rules_file = os.path.join(package.directory, 'debian', 'rules')

        lines = []
        with open(rules_file, 'r') as rules:
            lines = rules.readlines()
            for i in range(len(lines)):
                if '%:' in lines[i]:
                    lines.insert(i-1, patch)
                    break
            else:
                raise Exception('Failed to patch %s' % (rules_file,))

        with open(rules_file, 'w+') as rules:
            rules.writelines(lines)

    def patch_control(self, package):
        '''
        Patch control file to add dependencies.
        '''
        control_file = os.path.join(package.directory, 'debian', 'control')

        with open(control_file, 'r') as control:
            paragraphs = list(Deb822.iter_paragraphs(control))
            assert len(paragraphs) == 2, 'Unexpected control file format for %s.' % (package.name,)

        with open(control_file, 'w+') as control:
            control_dict_conf = self._control_patch(package.name)
            control_dict_pkg = package.control_patch()

            for field in control_dict_conf:
                paragraphs[1].merge_fields(field, control_dict_conf)

            for field in control_dict_pkg:
                paragraphs[1].merge_fields(field, control_dict_pkg)

            paragraphs[1]['Package'] = package.plname

            paragraphs[0].dump(control)
            control.write('\n')
            paragraphs[1].dump(control)

    def _control_patch(self, pkg_name):
        fields = []
        if self.config.has_section(pkg_name):
            fields = self.config.items(pkg_name)

        return Deb822(dict((k.title(), v) for k, v in fields
                           if  k.lower() != 'build-depends'))

    def install_build_dep(self, package):
        '''
        Install build dependencies if needed.
        '''
        if self.config.has_option(package.name, 'build-depends'):
            bdep = self.config.get(package.name, 'build-depends')
            self._install_build_dep(*bdep.split())

    def _install_build_dep(self, *packages):
        p = Popen(['sudo', 'apt-get', 'install', '-y'] + list(packages))
        p.wait()
        if p.returncode > 0:
            raise Exception('Failed to install build dependencies: %s' % (packages,))

    def build(self, package):
        '''
        Builds the debian package using dpkg-buildpackage.
        '''
        os.chdir(package.directory)

        p = Popen(['dpkg-buildpackage', '-us', '-uc'])
        p.wait()

        if p.returncode > 0:
            raise Exception('Failed to build %s' % (package.plname,))

        topdir = os.path.dirname(package.directory)
        for item in os.listdir(topdir):
            if fnmatch.fnmatch(item, '%s_*.deb' % package.plname):
                package.debfile = item
                package.debdir = topdir
                break
        else:
            raise Exception("Could not find build of %s" % (package.plname,))

    def move(self, package, destination):
        '''
        Moves a package to the destination if it has been build (thus has a .deb)
        '''
        if package.debdir and package.debfile:
            source = os.path.join(package.debdir, package.debfile)
            shutil.move(source, destination)
            print 'Moved %s to %s' % (package.debfile, destination)
