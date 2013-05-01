import os

# The absolute path of the directory containing the configuration file `control.ini`.
config_dir = os.path.dirname(os.path.abspath(__file__))

# The absolute path of the directory where generated *.deb files should be stored.
if os.getuid() == 0:
    PKG_REPO = '/var/repos/deb-repo/repository/pl-py2deb'
else:
    PKG_REPO = '/tmp'

# The absolute path of the directory where Debianized dependency names +
# versions are persisted.
if os.getuid() == 0:
    DEPENDENCY_STORE = '/var/lib/pl-py2deb/dependencies'
else:
    DEPENDENCY_STORE = '/tmp/pl-py2deb/dependencies'
