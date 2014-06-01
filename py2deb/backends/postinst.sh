#!/bin/sh -e

# Generic post-installation script for Debian binary packages that generates
# *.pyc files for Debian packages containing Python modules. This isn't
# necessary for packages built using py_support or dh_python2, however those
# are not always an option...

SCRIPT_NAME="$0"
PACKAGE_NAME="`basename "$SCRIPT_NAME" .postinst`"
if [ -z "$PACKAGE_NAME" ]; then
  echo "Warning: Failed to determine name of package! (py2deb postinst script)" >&2
else
  # Compile *.py files to *.pyc files.
  dpkg -L $PACKAGE_NAME | grep '\.py$' | xargs --delimiter '\n' --no-run-if-empty python -m py_compile || true
fi
