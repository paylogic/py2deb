"""
The :py:mod:`stdeb` module bundled with :py:mod:`py2deb` is a "fake module"
which loads the right version of stdeb depending on the current platform. The
py2deb package bundles two copies of stdeb:

=========  =========  =======  ===============================
Directory  Version    Source   Platform
=========  =========  =======  ===============================
stdeb_old  0.6.0      PyPI_    Ubuntu 10.04 (Lucid Lynx)
stdeb_new  0.6.0+git  GitHub_  Ubuntu 12.04 (Precise Pangolin)
=========  =========  =======  ===============================

This trickery is needed because stdeb 0.6.0+git is required on Ubuntu 12.04
but simply doesn't work on Ubuntu 10.04 and hasn't actually been released :-)

.. _PyPI: https://pypi.python.org/pypi/stdeb
.. _GitHub: https://github.com/astraw/stdeb
"""

# Standard library modules.
import os
import pipes
import sys

def pick_stdeb_release():
    """
    Find the latest version of the ``python-all`` package available on the
    current platform (regardless of whether it is currently installed) and
    check whether it's equal to or greater than 2.6.6-3: If it is the new stdeb
    is picked, otherwise the old stdeb is picked.
    """
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
