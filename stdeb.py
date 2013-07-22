# Fake stdeb module that loads the right version of stdeb depending on platform.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 22, 2013
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

import sys

def is_lucid_lynx():
    """
    Check the contents of ``/etc/issue.net`` to determine whether we are
    running on Ubuntu 10.04 (Lucid Lynx).

    :returns: ``True`` if running on Ubuntu 10.04, ``False`` otherwise.
    """
    try:
        with open('/etc/issue.net') as handle:
            return '10.04' in handle.read()
    except Exception:
        return False

if is_lucid_lynx():
    from py2deb.libs import stdeb_old
    sys.modules['stdeb'] = stdeb_old
else:
    from py2deb.libs import stdeb_new
    sys.modules['stdeb'] = stdeb_new
