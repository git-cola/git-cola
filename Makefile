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

cola_app = $(CURDIR)/git-cola.app
cola_version = $(shell env TERM=dummy $(PYTHON) cola/version.py)
cola_dist := cola-$(cola_version)

python_path = $(CURDIR):$(CURDIR)/thirdparty:$(PYTHONPATH)
python_version = $(shell env TERM=dummy $(PYTHON) -c 'import distutils.sysconfig as sc; print(sc.get_python_version())')
python_site := $(prefix)/lib*/python$(python_version)/site-packages

test_flags =
all_test_flags = --with-doctest --exclude=sphinxtogithub $(test_flags)

# User customizations
-include config.mak

ifdef standalone
standalone_args	?= --standalone
endif


all::
	$(PYTHON) setup.py build

install: all
	$(PYTHON) setup.py --quiet install \
		$(standalone_args) \
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
		$(DESTDIR)$(prefix)/bin/cola \
		$(DESTDIR)$(prefix)/share/applications/cola.desktop \
		$(DESTDIR)$(prefix)/share/git-cola \
		$(DESTDIR)$(prefix)/share/doc/git-cola

test: all
	@env PYTHONPATH=$(python_path) \
	$(NOSETESTS) $(all_test_flags)

coverage:
	@env PYTHONPATH=$(python_path) \
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
	$(TAR) czf git-cola-$(cola_version).app.tar.gz $(cola_app)

.PHONY: all install doc install-doc install-html test clean tags
.PHONY: git-cola.app app-tarball
