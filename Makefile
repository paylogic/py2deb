# Makefile for py2deb.
#
# Author: Peter Odding <peter@peterodding.com>
# Last Change: July 21, 2013

default:
	@echo 'Makefile for py2deb'
	@echo
	@echo 'Usage:'
	@echo
	@echo '    make test       run the test suite'
	@echo '    make clean      cleanup all temporary files'
	@echo

test:
	python setup.py test

clean:
	rm -Rf build dist *.egg *.egg-info
