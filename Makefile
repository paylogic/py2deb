# Makefile for py2deb.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: October 12, 2013

default:
	@echo 'Makefile for py2deb'
	@echo
	@echo 'Usage:'
	@echo
	@echo '    make test         run the test suite'
	@echo '    make clean        cleanup all temporary files'
	@echo '    make stdeb.cfg    generate stdeb.cfg'
	@echo

test:
	python setup.py test

clean:
	rm -Rf build dist *.egg *.egg-info

stdeb.cfg:
	python -c 'from py2deb import generate_stdeb_cfg; generate_stdeb_cfg()' > stdeb.cfg

.PHONY: default test clean stdeb.cfg
