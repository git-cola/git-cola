prefix	?= $(HOME)
DESTDIR	?= /
PYTHON	?= python
PYTHON_VER	?= $(shell $(PYTHON) -c 'import platform; print platform.python_version()[:3]')
PYTHON_SITE	?= $(DESTDIR)$(prefix)/lib/python$(PYTHON_VER)/site-packages
COLA_VER	?= $(shell git describe --abbrev=4 --match='v*.*')
APP	?= git-cola.app
APPZIP	?= $(shell darwin/name-tarball.py)

all:
	$(PYTHON) setup.py build

darwin: all
	$(PYTHON) darwin/py2app-setup.py py2app

$(APP): darwin
	rm -rf $(APP)
	mv dist/$(APP) $(CURDIR)
	find $(APP) -name '*_debug*' | xargs rm -f
	tar cjf $(APPZIP) $(APP)

install:
	$(PYTHON) setup.py install \
		--quiet \
		--prefix=$(DESTDIR)$(prefix) \
		--force && \
	rm -f $(PYTHON_SITE)/git_cola* && \
	(test -d $(PYTHON_SITE) && rmdir -p $(PYTHON_SITE) 2>/dev/null || true) && \
	(cd $(DESTDIR)$(prefix)/bin && \
	 ((! test -e cola && ln -s git-cola cola) || true))

doc:
	$(MAKE) -C share/doc/git-cola prefix=$(prefix) all

html:
	$(MAKE) -C share/doc/git-cola prefix=$(prefix) html

install-doc:
	$(MAKE) -C share/doc/git-cola prefix=$(prefix) install

install-html:
	$(MAKE) -C share/doc/git-cola prefix=$(prefix) install-html

uninstall:
	rm -rf  $(DESTDIR)$(prefix)/bin/git-cola \
		$(DESTDIR)$(prefix)/bin/cola \
		$(DESTDIR)$(prefix)/share/applications/cola.desktop \
		$(DESTDIR)$(prefix)/share/git-cola \
		$(DESTDIR)$(prefix)/share/doc/git-cola

test_flags	?=
all_test_flags	?= --with-doctest $(test_flags)

test: all
	@env PYTHONPATH="$(CURDIR)":"$(PYTHONPATH)" \
	nosetests $(all_test_flags)

coverage:
	@env PYTHONPATH=$(CURDIR):$(PYTHONPATH) \
	nosetests $(all_test_flags) \
		--with-coverage --cover-package=cola

clean:
	$(MAKE) -C share/doc/git-cola clean
	find . -name .noseids -print0 | xargs -0 rm -f
	find . -name '*.py[co]' -print0 | xargs -0 rm -f
	find share -name '*.qm' -print0 | xargs -0 rm -f
	rm -rf cola/builtin_version.* build dist tmp tags git-cola.app

tags:
	ctags cola/*.py cola/*/*.py

.PHONY: all install doc install-doc install-html test clean darwin git-cola.app
