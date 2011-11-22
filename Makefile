# The default target of this Makefile is...
all::

# The external commands used by this Makefile are...
GIT = git
NOSETESTS = nosetests
PYTHON = python
TAR = tar

# These values can be overridden on the command-line or via config.mak
prefix = $(HOME)
bindir = $(prefix)/bin
# DESTDIR =

cola_base := git-cola
cola_app_base= $(cola_base).app
cola_app = $(CURDIR)/$(cola_app_base)
cola_version = $(shell env TERM=dummy $(PYTHON) cola/version.py)
cola_dist := $(cola_base)-$(cola_version)

python_version = $(shell env TERM=dummy $(PYTHON) -c 'import distutils.sysconfig as sc; print(sc.get_python_version())')
python_site := $(prefix)/lib*/python$(python_version)/site-packages

test_flags =
all_test_flags = --with-doctest --exclude=sphinxtogithub $(test_flags)

# User customizations
-include config.mak


all::
	$(PYTHON) setup.py build

install: all
	$(PYTHON) setup.py --quiet install \
		--prefix=$(DESTDIR)$(prefix) \
		--install-scripts=$(DESTDIR)$(bindir) \
		--force && \
	rm -f $(DESTDIR)$(python_site)/git_cola*
	rmdir -p $(DESTDIR)$(python_site) 2>/dev/null || true
	(cd $(DESTDIR)$(bindir) && \
	! test -e cola && ln -s git-cola cola) || true

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
	find . -name '*.py' -print0 | xargs -0 ctags -f tags

pot:
	$(PYTHON) setup.py build_pot -N -d .

mo:
	$(PYTHON) setup.py build_mo -f

git-cola.app:
	mkdir -p $(cola_app)/Contents/MacOS
	cp darwin/git-cola $(cola_app)/Contents/MacOS
	cp darwin/Info.plist darwin/PkgInfo $(cola_app)/Contents
	$(MAKE) prefix=$(cola_app)/Contents/Resources install install-doc
	cp darwin/git-cola.icns $(cola_app)/Contents/Resources

app-tarball: git-cola.app
	$(TAR) czf $(cola_dist).app.tar.gz $(cola_app_base)

.PHONY: all install doc install-doc install-html test clean tags
.PHONY: git-cola.app app-tarball
