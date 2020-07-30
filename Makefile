# Makefile for py2deb.
#
# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: July 30, 2020
# URL: https://github.com/paylogic/py2deb

PACKAGE_NAME = py2deb
WORKON_HOME ?= $(HOME)/.virtualenvs
VIRTUAL_ENV ?= $(WORKON_HOME)/$(PACKAGE_NAME)
PYTHON ?= python3
PATH := $(VIRTUAL_ENV)/bin:$(PATH)
MAKE := $(MAKE) --no-print-directory
SHELL = bash

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
	@source "$(VIRTUAL_ENV)/bin/activate" && $(PYTHON) scripts/downgrade-pip-on-pypy.py
ifeq ($(TRAVIS), true)
# Setuptools and wheel are build dependencies of cryptography. If we don't
# install them before the main 'pip install' run the setup.py script of
# cryptography attempts to take care of this on its own initiative which for
# some reason fails on PyPy: https://travis-ci.org/github/paylogic/py2deb/jobs/713379963
	@pip install --constraint=constraints.txt 'setuptools >= 40.6.0' wheel
	@pip install --constraint=constraints.txt --requirement=requirements-travis.txt
else
	@pip install --constraint=constraints.txt --requirement=requirements.txt
	@pip uninstall --yes $(PACKAGE_NAME) &>/dev/null || true
	@pip install --no-deps --ignore-installed .
endif

reset:
	@$(MAKE) clean
	@rm -Rf "$(VIRTUAL_ENV)"
	@$(MAKE) install

check: install
	@pip install --upgrade --constraint=constraints.txt --requirement=requirements-checks.txt
	@flake8

test: install
	@pip install --constraint=constraints.txt --requirement=requirements-tests.txt
	@py.test --cov
	@coverage html
	@coverage report --fail-under=90 &>/dev/null

tox: install
	@pip install --constraint=constraints.txt tox
	@tox

readme: install
	@pip install cogapp
	@cog.py -r README.rst

docs: readme
	@pip install --constraint=constraints.txt sphinx
	@cd docs && sphinx-build -nb html -d build/doctrees . build/html

publish: install
	@git push origin && git push --tags origin
	@$(MAKE) clean
	@pip install --constraint=constraints.txt twine wheel
	@$(PYTHON) setup.py sdist bdist_wheel
	@twine upload dist/*
	@$(MAKE) clean

clean:
	@rm -Rf *.egg .cache .coverage .tox build dist docs/build htmlcov
	@find -depth -type d -name __pycache__ -exec rm -Rf {} \;
	@find -type f -name '*.pyc' -delete

.PHONY: default install reset check test tox readme docs publish clean
