# Fake stdeb module that loads the right version of stdeb depending on platform.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: October 20, 2013
#
# The py2deb package bundles two copies of stdeb:
#
#   -------------------------------------------------
#   | Directory | Version   | Source | Platform     |
#   | --------- | --------- | ------ | ------------ |
#   | stdeb_old | 0.6.0     | PyPI   | Ubuntu 10.04 |
#   | stdeb_new | 0.6.0+git | GitHub | Ubuntu 12.04 |
#   -------------------------------------------------
#
# This trickery is needed because stdeb 0.6.0+git is required on Ubuntu 12.04
# but simply doesn't work on Ubuntu 10.04 and hasn't actually been released :-)

# Standard library modules.
import os
import pipes
import sys

def pick_stdeb_release():
    # Find the newest version of the `python-all' package available on the
    # current platform (regardless of whether it is currently installed).
    # XXX `sort --version-sort' isn't supported in Ubuntu 9.04 (Jaunty) and it
    # looks like `sort --general-numeric-sort' works fine for our purpose.
    handle = os.popen("apt-cache show python-all | awk '/^Version:/ {print $2}' | sort --general-numeric-sort | tail -n1")
    python_all_version = handle.read().strip()
    handle.close()
    # Use dpkg's support for raw version comparisons to check whether the
    # newest available version of the `python-all' package is >= 2.6.6-3.
    if os.system("dpkg --compare-versions %s '>=' 2.6.6-3" % pipes.quote(python_all_version)) == 0:
        return __import__('stdeb_new')
    else:
        return __import__('stdeb_old')

sys.modules['stdeb'] = pick_stdeb_release()
