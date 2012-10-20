# The default target of this Makefile is...
all::

# The external commands used by this Makefile are...
GIT = git
NOSETESTS = nosetests
PYTHON = python
TAR = tar
CTAGS = ctags

# These values can be overridden on the command-line or via config.mak
prefix = $(HOME)
bindir = $(prefix)/bin
coladir = $(prefix)/share/git-cola/lib
darwin_python = /System/Library/Frameworks/Python.framework/Resources/Python.app/Contents/MacOS/Python
# DESTDIR =

cola_base := git-cola
cola_app_base= $(cola_base).app
cola_app = $(CURDIR)/$(cola_app_base)
cola_version = $(shell env TERM=dummy $(PYTHON) cola/version.py)
cola_dist := $(cola_base)-$(cola_version)

test_flags =
all_test_flags = --with-doctest --exclude=sphinxtogithub $(test_flags)

# User customizations
-include config.mak

setup_args = --prefix=$(prefix)
setup_args += --quiet
setup_args += --force
setup_args += --install-scripts=$(bindir)
setup_args += --record=build/MANIFEST
setup_args += --install-lib=$(coladir)
ifdef DESTDIR
    setup_args += --root=$(DESTDIR)
endif

all::
	$(PYTHON) setup.py build

install: all
	$(PYTHON) setup.py install $(setup_args)
	(cd $(DESTDIR)$(bindir) && \
	! test -e cola && ln -s git-cola cola) || true
	rm -rf $(DESTDIR)$(coladir)/git_cola*
	rm -rf git_cola.egg-info

# Maintainer's dist target
dist:
	$(GIT) archive --format=tar --prefix=$(cola_dist)/ HEAD^{tree} | \
		gzip -f -9 - >$(cola_dist).tar.gz

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
		$(DESTDIR)$(prefix)/bin/git-dag \
		$(DESTDIR)$(prefix)/bin/cola \
		$(DESTDIR)$(prefix)/share/applications/git-cola.desktop \
		$(DESTDIR)$(prefix)/share/applications/git-dag.desktop \
		$(DESTDIR)$(prefix)/share/git-cola \
		$(DESTDIR)$(prefix)/share/doc/git-cola
	rm -f $(DESTDIR)$(prefix)/share/locale/*/LC_MESSAGES/git-cola.mo
	rmdir $(DESTDIR)$(prefix)/share/locale/*/LC_MESSAGES 2>/dev/null || true
	rmdir $(DESTDIR)$(prefix)/share/locale/* 2>/dev/null || true
	rmdir $(DESTDIR)$(prefix)/share/locale 2>/dev/null || true
	rmdir $(DESTDIR)$(prefix)/share/doc 2>/dev/null || true
	rmdir $(DESTDIR)$(prefix)/share/applications 2>/dev/null || true
	rmdir $(DESTDIR)$(prefix)/share 2>/dev/null || true
	rmdir $(DESTDIR)$(prefix)/bin 2>/dev/null || true
	rmdir $(DESTDIR)$(prefix) 2>/dev/null || true

test: all
	$(NOSETESTS) $(all_test_flags)

coverage:
	$(NOSETESTS) --with-coverage --cover-package=cola $(all_test_flags)

clean:
	$(MAKE) -C share/doc/git-cola clean
	find . -name .noseids -print0 | xargs -0 rm -f
	find . -name '*.py[co]' -print0 | xargs -0 rm -f
	rm -rf build dist tmp tags git-cola.app
	rm -rf share/locale

tags:
	find . -name '*.py' -print0 | xargs -0 $(CTAGS) -f tags

pot:
	$(PYTHON) setup.py build_pot -N -d .

mo:
	$(PYTHON) setup.py build_mo -f

git-cola.app:
	mkdir -p $(cola_app)/Contents/MacOS
	mkdir -p $(cola_app)/Contents/Resources
	cp darwin/git-cola $(cola_app)/Contents/MacOS
	cp darwin/Info.plist darwin/PkgInfo $(cola_app)/Contents
	$(MAKE) prefix=$(cola_app)/Contents/Resources install install-doc
	cp darwin/git-cola.icns $(cola_app)/Contents/Resources
	ln -sf $(darwin_python) $(cola_app)/Contents/Resources/git-cola

app-tarball: git-cola.app
	$(TAR) czf $(cola_dist).app.tar.gz $(cola_app_base)

.PHONY: all install doc install-doc install-html test clean tags
.PHONY: git-cola.app app-tarball
