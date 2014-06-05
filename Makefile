# Makefile for py2deb.
#
# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: June 5, 2014
# URL: https://github.com/paylogic/py2deb

PROJECT_NAME = py2deb
WORKON_HOME ?= $(HOME)/.virtualenvs
VIRTUAL_ENV ?= $(WORKON_HOME)/$(PROJECT_NAME)
ACTIVATE = . "$(VIRTUAL_ENV)/bin/activate"

default:
	@echo 'Makefile for $(PROJECT_NAME)'
	@echo
	@echo 'Usage:'
	@echo
	@echo '    make install    install the package in a virtual environment'
	@echo '    make reset      recreate the virtual environment'
	@echo '    make test       run the test suite'
	@echo '    make coverage   run the tests, report coverage'
	@echo '    make docs       update documentation using Sphinx'
	@echo '    make publish    publish changes to GitHub/PyPI'
	@echo '    make clean      cleanup temporary files'
	@echo

install:
	test -d "$(VIRTUAL_ENV)" || virtualenv --system-site-packages "$(VIRTUAL_ENV)"
	test -x "$(VIRTUAL_ENV)/bin/pip" || $(ACTIVATE) && easy_install pip
	test -x "$(VIRTUAL_ENV)/bin/pip-accel" || $(ACTIVATE) && pip install pip-accel
	$(ACTIVATE) && pip-accel install --requirement=requirements.txt
	$(ACTIVATE) && pip uninstall --yes $(PROJECT_NAME) || true
	$(ACTIVATE) && pip install --no-deps --editable .

clean:
	rm -Rf *.egg *.egg-info .coverage build dist docs/build htmlcov
	find -depth -type d -name __pycache__ -exec rm -Rf {} \;
	find -type f -name '*.pyc' -delete

reset: clean
	rm -Rf "$(VIRTUAL_ENV)"
	make --no-print-directory install

test: install
	$(ACTIVATE) && python setup.py test

coverage: install
	test -x "$(VIRTUAL_ENV)/bin/coverage" || $(ACTIVATE) && pip-accel install coverage
	$(ACTIVATE) && coverage run --source=$(PROJECT_NAME) setup.py test
	$(ACTIVATE) && coverage html

docs: install
	test -x "$(VIRTUAL_ENV)/bin/sphinx-build" || $(ACTIVATE) && pip-accel install sphinx
	$(ACTIVATE) && cd docs && sphinx-build -b html -d build/doctrees . build/html

publish:
	git push origin && git push --tags origin
	make clean && python setup.py sdist upload

.PHONY: default install clean reset test coverage docs publish
