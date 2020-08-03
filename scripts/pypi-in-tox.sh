#!/bin/bash -e

# This shell script is run by tox from the project directory, one level up.
# This explains why we have to use `scripts/' in the pathname below.

# Downgrade to pip < 20.2 on PyPI in tox.
echo "[pypi-in-tox] Pip before downgrade: $(pip --version)" >&2
python scripts/downgrade-pip-on-pypy.py
echo "[pypi-in-tox] Pip after downgrade: $(pip --version)" >&2

# Continue installing packages as normal.
python -m pip install "$@"
