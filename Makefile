# Makefile for py2deb.
#
# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: August 4, 2020
# URL: https://github.com/paylogic/py2deb

PACKAGE_NAME = py2deb
WORKON_HOME ?= $(HOME)/.virtualenvs
VIRTUAL_ENV ?= $(WORKON_HOME)/$(PACKAGE_NAME)
PYTHON ?= python3
PATH := $(VIRTUAL_ENV)/bin:$(PATH)
MAKE := $(MAKE) --no-print-directory
SHELL = bash

# Configure pip not to use binary wheels on PyPy 3, with the goal of
# stabilizing Travis CI builds. My trials in getting this to work:
#
# 1. I struggled to work around several issues involving pip using wheels on
#    PyPy 3 but subsequently "crashing" (tracebacks) in one of several ways due
#    to the use of wheels.
#
# 2. After wasting quite a few more hours than I care to admit on (1) I decided
#    to preserve my sanity by "giving in" and just disabling wheels on PyPy 3
#    altogether. This seemed like a simple solution, but it wasn't 😇.
#
# 3. Unfortunately even (2) is not enough, because some of our requirements use
#    the "setup_requires" feature. This used to be handled by setuptools, but
#    nowadays it's handled by a nested pip process, and that will try to use
#    wheels even when the parent process received the "--no-binary=:all:"
#    command line option 😞. I guess this is a bug in the packaging ecosystem
#    (I assume pip) but that doesn't really help me at this point.
#
# 4. To work around (3) some of the "transitive build requirements" are listed
#    in requirements-tests.txt which means they're installed by the top level
#    pip process which does respect the "--no-binary=:all:" option.
#
# Here's an overview of my weekend of experimentation to find a way
# to successfully set up a usable py2deb test environment for PyPy 3:
# https://github.com/paylogic/py2deb/compare/4ab626b6582...affa7158560
ifeq ($(findstring pypy3,$(PYTHON)),pypy3)
NO_BINARY_OPTION := :all:
else
NO_BINARY_OPTION := :none:
endif

# Define how we run 'pip' in a single place (DRY).
PIP_CMD := python -m pip

# Define how we run 'pip install' in a single place (DRY).
PIP_INSTALL_CMD := $(PIP_CMD) install \
	--constraint=constraints.txt \
	--no-binary=$(NO_BINARY_OPTION)

default:
	@echo "Makefile for $(PACKAGE_NAME)"
	@echo
	@echo 'Usage:'
	@echo
	@echo '    make install    install the package in a virtual environment'
	@echo '    make reset      recreate the virtual environment'
	@echo '    make check      check coding style (PEP-8, PEP-257)'
	@echo '    make test       run the test suite, report coverage'
	@echo '    make tox        run the tests on all Python versions'
	@echo '    make readme     update usage in readme'
	@echo '    make docs       update documentation using Sphinx'
	@echo '    make publish    publish changes to GitHub/PyPI'
	@echo '    make clean      cleanup all temporary files'
	@echo

install:
	@test -d "$(VIRTUAL_ENV)" || mkdir -p "$(VIRTUAL_ENV)"
	@test -x "$(VIRTUAL_ENV)/bin/python" || virtualenv --python=$(PYTHON) "$(VIRTUAL_ENV)"
ifeq ($(findstring pypy,$(PYTHON)),pypy)
# Downgrade pip on PyPy in an attempt to avoid wheel incompatibilities.
	@source "$(VIRTUAL_ENV)/bin/activate" && $(PYTHON) scripts/pypy.py
endif
ifeq ($(TRAVIS), true)
# Setuptools and wheel are build dependencies of cryptography. If we don't
# install them before the main 'pip install' run the setup.py script of
# cryptography attempts to take care of this on its own initiative which
# fails on PyPy due to incompatibilities between pip and PyPy:
# https://travis-ci.org/github/paylogic/py2deb/jobs/713379963
	@$(PIP_INSTALL_CMD) --upgrade 'setuptools >= 40.6.0' wheel
	@$(PIP_INSTALL_CMD) --requirement=requirements-travis.txt
else
	@$(PIP_INSTALL_CMD) --requirement=requirements.txt
	@$(PIP_CMD) uninstall --yes $(PACKAGE_NAME) &>/dev/null || true
	@$(PIP_INSTALL_CMD) --no-deps --ignore-installed .
endif

reset:
	@$(MAKE) clean
	@rm -Rf "$(VIRTUAL_ENV)"
	@$(MAKE) install

check: install
	@$(PIP_INSTALL_CMD) --upgrade --requirement=requirements-checks.txt
	@flake8

test: install
	@$(PIP_INSTALL_CMD) --requirement=requirements-tests.txt
	@py.test --cov
	@coverage html
	@coverage report --fail-under=90 &>/dev/null

tox: install
	@$(PIP_INSTALL_CMD) tox
	@tox

readme: install
	@$(PIP_INSTALL_CMD) cogapp
	@cog.py -r README.rst

docs: readme
	@$(PIP_INSTALL_CMD) sphinx
	@cd docs && sphinx-build -nb html -d build/doctrees . build/html

publish: install
	@git push origin && git push --tags origin
	@$(MAKE) clean
	@$(PIP_INSTALL_CMD) twine wheel
	@$(PYTHON) setup.py sdist bdist_wheel
	@twine upload dist/*
	@$(MAKE) clean

clean:
	@rm -Rf *.egg .cache .coverage .tox build dist docs/build htmlcov
	@find -depth -type d -name __pycache__ -exec rm -Rf {} \;
	@find -type f -name '*.pyc' -delete

.PHONY: default install reset check test tox readme docs publish clean
