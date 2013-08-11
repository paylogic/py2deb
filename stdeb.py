# Fake stdeb module that loads the right version of stdeb depending on platform.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: August 11, 2013
#
# The py2deb package bundles two copies of stdeb:
#
#   -------------------------------------------------------------
#   | Directory             | Version   | Source | Platform     |
#   | --------------------- | --------- | ------ | ------------ |
#   | py2deb/libs/stdeb_old | 0.6.0     | PyPI   | Ubuntu 10.04 |
#   | py2deb/libs/stdeb_new | 0.6.0+git | GitHub | Ubuntu 12.04 |
#   -------------------------------------------------------------
#
# This trickery is needed because stdeb 0.6.0+git is required on Ubuntu 12.04
# but simply doesn't work on Ubuntu 10.04 and hasn't actually been released :-)

# Standard library modules.
import sys

# Internal modules.
from py2deb.util import pick_stdeb_release

if pick_stdeb_release() == 'old':
    from py2deb.libs import stdeb_old
    sys.modules['stdeb'] = stdeb_old
else:
    from py2deb.libs import stdeb_new
    sys.modules['stdeb'] = stdeb_new
