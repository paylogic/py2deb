import os

config_dir = os.path.dirname(os.path.abspath(__file__))

# Destination of built packages.
if os.getuid() == 0:
    PKG_REPO = '/var/repos/deb-repo/repository/pl-py2deb'
else:
    PKG_REPO = '/tmp'
