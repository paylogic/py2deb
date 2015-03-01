# Makefile for py2deb.
#
# Author: Peter Odding <peter.odding@paylogic.com>
# Last Change: March 1, 2015
# URL: https://github.com/paylogic/py2deb

PROJECT_NAME = py2deb
WORKON_HOME ?= $(HOME)/.virtualenvs

# Most people prefer $(CURDIR)/.env but I really don't, so if ~/.virtualenvs
# exists (i.e. an explicit choice was made by the user, that is to say me :-)
# we use that, otherwise we fall back to $(CURDIR)/.env.
ifeq ($(shell test -d $(WORKON_HOME) && echo yes || echo no),yes)
	VIRTUAL_ENV = $(WORKON_HOME)/$(PROJECT_NAME)
else
	VIRTUAL_ENV = $(CURDIR)/.env
endif

ACTIVATE = . "$(VIRTUAL_ENV)/bin/activate"

default:
	@echo 'Makefile for $(PROJECT_NAME)'
	@echo
	@echo 'Usage:'
	@echo
	@echo '    make install    install the package in a virtual environment'
	@echo '    make check      check PEP-8 and PEP-257 compliance'
	@echo '    make test       run the test suite'
	@echo '    make coverage   run the tests, report coverage'
	@echo '    make docs       update documentation using Sphinx'
	@echo '    make publish    publish changes to GitHub/PyPI'
	@echo '    make clean      cleanup temporary files'
	@echo '    make reset      recreate the virtual environment'
	@echo

install:
	test -x "$(VIRTUAL_ENV)/bin/python" || virtualenv "$(VIRTUAL_ENV)"
	test -x "$(VIRTUAL_ENV)/bin/pip-accel" || ($(ACTIVATE) && pip install pip-accel)
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

check:
	@test -x "$(VIRTUAL_ENV)/bin/pep8" || ($(ACTIVATE) && pip-accel install pep8)
	@test -x "$(VIRTUAL_ENV)/bin/pep257" || ($(ACTIVATE) && pip-accel install pep257)
	@$(ACTIVATE) && pep8 --max-line-length=120 setup.py docs/conf.py py2deb
	@$(ACTIVATE) && pep257 --ignore=D200 setup.py docs/conf.py py2deb

test: check install
	@test -x "$(VIRTUAL_ENV)/bin/py.test" || ($(ACTIVATE) && pip-accel install pytest)
	$(ACTIVATE) && py.test --capture=no --exitfirst py2deb/tests.py

coverage: check install
	@test -x "$(VIRTUAL_ENV)/bin/coverage" || ($(ACTIVATE) && pip-accel install coverage)
	$(ACTIVATE) && coverage run --source=$(PROJECT_NAME) setup.py test
	$(ACTIVATE) && coverage html --omit=py2deb/tests.py

docs: check install
	@test -x "$(VIRTUAL_ENV)/bin/sphinx-build" || ($(ACTIVATE) && pip-accel install sphinx)
	$(ACTIVATE) && cd docs && sphinx-build -b html -d build/doctrees . build/html

publish: check
	git push origin && git push --tags origin
	make clean && python setup.py sdist upload

.PHONY: default install clean reset test coverage docs publish
