#!/bin/bash -e

# This shell script is run by tox from the project directory, one level up.
# This explains why we have to use `scripts/' in the pathname below.

# Downgrade to pip < 20.2 when running on PyPy inside tox.
echo "[scripts/pypy.sh] pip before downgrade: $(pip --version)" >&2
python scripts/pypy.py
echo "[scripts/pypy.sh] pip after downgrade: $(pip --version)" >&2

# Continue installing packages as normal.
python -m pip install "$@"
