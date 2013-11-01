# Makefile for py2deb.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: November 1, 2013

WORKON_HOME ?= $(HOME)/.virtualenvs
VIRTUAL_ENV ?= $(WORKON_HOME)/py2deb

default:
	@echo "Makefile for py2deb"
	@echo
	@echo "Usage:"
	@echo
	@echo "    make test         run test suite"
	@echo "    make clean        cleanup temporary files"
	@echo "    make reset        (re)create virtual environment"
	@echo "    make stdeb.cfg    generate stdeb.cfg"
	@echo
	@echo "Variables:"
	@echo
	@echo "    WORKON_HOME = $(WORKON_HOME)"
	@echo "    VIRTUAL_ENV = $(VIRTUAL_ENV)"
	@echo

test:
	python setup.py test

clean:
	rm -Rf build dist *.egg *.egg-info

reset: clean
	# (Re)create the Python virtual environment.
	rm -Rf "$(VIRTUAL_ENV)"
	virtualenv "$(VIRTUAL_ENV)"
	# Install pip-accel for faster installation of dependencies from PyPI.
	. "$(VIRTUAL_ENV)/bin/activate" && pip install pip-accel
	# Use pip-accel to install all dependencies based on requirements.txt.
	. "$(VIRTUAL_ENV)/bin/activate" && pip-accel install -r requirements.txt
	# Install py2deb using pip instead of pip-accel because we specifically
	# *don't* want a cached binary distribution archive to be installed :-)
	. "$(VIRTUAL_ENV)/bin/activate" && pip install --no-deps .

stdeb.cfg:
	python -c 'from py2deb import generate_stdeb_cfg; generate_stdeb_cfg()' > stdeb.cfg

.PHONY: default test clean reset stdeb.cfg
