# The default target of this Makefile is...
all::

# The external commands used by this Makefile are...
CTAGS = ctags
CP = cp
FIND = find
GIT = git
GZIP = gzip
LN = ln
MKDIR_P = mkdir -p
NOSETESTS = nosetests
PYTHON = python
RM = rm -f
RM_R = rm -fr
RMDIR = rmdir
TAR = tar

# These values can be overridden on the command-line or via config.mak
prefix = $(HOME)
bindir = $(prefix)/bin
coladir = $(prefix)/share/git-cola/lib
darwin_python = /System/Library/Frameworks/Python.framework/Resources/Python.app/Contents/MacOS/Python
# DESTDIR =

cola_base := git-cola
cola_app_base= $(cola_base).app
cola_app = $(CURDIR)/$(cola_app_base)
cola_version = $(shell $(PYTHON) bin/git-cola version --brief)
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
    export DESTDIR
endif

all::
	$(PYTHON) setup.py build

install: all
	$(PYTHON) setup.py install $(setup_args)
	(cd $(DESTDIR)$(bindir) && \
	! test -e cola && $(LN) -s git-cola cola) || true
	$(RM_R) $(DESTDIR)$(coladir)/git_cola*
	$(RM_R) git_cola.egg-info

# Maintainer's dist target
dist:
	$(GIT) archive --format=tar --prefix=$(cola_dist)/ HEAD^{tree} | \
		$(GZIP) -f -9 - >$(cola_dist).tar.gz

doc:
	$(MAKE) -C share/doc/git-cola prefix=$(prefix) all

html:
	$(MAKE) -C share/doc/git-cola prefix=$(prefix) html

install-doc:
	$(MAKE) -C share/doc/git-cola prefix=$(prefix) install

install-html:
	$(MAKE) -C share/doc/git-cola prefix=$(prefix) install-html

uninstall:
	$(RM) $(DESTDIR)$(prefix)/bin/git-cola
	$(RM) $(DESTDIR)$(prefix)/bin/git-dag
	$(RM) $(DESTDIR)$(prefix)/bin/cola
	$(RM) $(DESTDIR)$(prefix)/share/applications/git-cola.desktop
	$(RM) $(DESTDIR)$(prefix)/share/applications/git-dag.desktop
	$(RM_R) $(DESTDIR)$(prefix)/share/git-cola
	$(RM_R) $(DESTDIR)$(prefix)/share/doc/git-cola
	$(RM) $(DESTDIR)$(prefix)/share/locale/*/LC_MESSAGES/git-cola.mo
	$(RMDIR) $(DESTDIR)$(prefix)/share/locale/*/LC_MESSAGES 2>/dev/null || true
	$(RMDIR) $(DESTDIR)$(prefix)/share/locale/* 2>/dev/null || true
	$(RMDIR) $(DESTDIR)$(prefix)/share/locale 2>/dev/null || true
	$(RMDIR) $(DESTDIR)$(prefix)/share/doc 2>/dev/null || true
	$(RMDIR) $(DESTDIR)$(prefix)/share/applications 2>/dev/null || true
	$(RMDIR) $(DESTDIR)$(prefix)/share 2>/dev/null || true
	$(RMDIR) $(DESTDIR)$(prefix)/bin 2>/dev/null || true
	$(RMDIR) $(DESTDIR)$(prefix) 2>/dev/null || true

test: all
	$(NOSETESTS) $(all_test_flags)

coverage:
	$(NOSETESTS) --with-coverage --cover-package=cola $(all_test_flags)

clean:
	$(MAKE) -C share/doc/git-cola clean
	$(FIND) . -name .noseids -print0 | xargs -0 rm -f
	$(FIND) . -name '*.py[co]' -print0 | xargs -0 rm -f
	$(RM_R) build dist tmp tags git-cola.app
	$(RM_R) share/locale

tags:
	$(FIND) . -name '*.py' -print0 | xargs -0 $(CTAGS) -f tags

pot:
	$(PYTHON) setup.py build_pot -N -d .

mo:
	$(PYTHON) setup.py build_mo -f

git-cola.app:
	$(MKDIR_P) $(cola_app)/Contents/MacOS
	$(MKDIR_P) $(cola_app)/Contents/Resources
	$(CP) darwin/git-cola $(cola_app)/Contents/MacOS
	$(CP) darwin/Info.plist darwin/PkgInfo $(cola_app)/Contents
	$(MAKE) prefix=$(cola_app)/Contents/Resources install install-doc
	$(CP) darwin/git-cola.icns $(cola_app)/Contents/Resources
	$(LN) -sf $(darwin_python) $(cola_app)/Contents/Resources/git-cola

app-tarball: git-cola.app
	$(TAR) czf $(cola_dist).app.tar.gz $(cola_app_base)

.PHONY: all install doc install-doc install-html test clean tags
.PHONY: git-cola.app app-tarball
