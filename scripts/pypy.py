"""
Downgrade to pip < 20.2 when running on PyPy.

Unfortunately pip 20.2 (the most recent release at the time of writing) breaks
compatibility with PyPy, thereby causing Travis CI builds of py2deb to fail as
well. For details please refer to https://github.com/pypa/pip/issues/8653.
"""

import pip
import platform
import subprocess
import sys

from distutils.version import LooseVersion

if platform.python_implementation() == "PyPy":
    installed_release = LooseVersion(pip.__version__)
    known_bad_release = LooseVersion("20.2")
    if installed_release >= known_bad_release:
        sys.stderr.write("[scripts/pypy.py] Removing incompatible pip release ..\n")
        subprocess.call([sys.executable, "-m", "pip", "uninstall", "--yes", "pip"])
        sys.stderr.write("[scripts/pypy.py] Installing compatible pip using setuptools ..\n")
        subprocess.check_call([sys.executable, "-m", "easy_install", "--always-unzip", "pip < 20.2"])
