# The default target of this Makefile is...
all::

# The external commands used by this Makefile are...
CTAGS = ctags
CP = cp
FIND = find
FLAKE8 = flake8
GIT = git
GZIP = gzip
LN = ln
LN_S = $(LN) -s -f
MARKDOWN = markdown
MKDIR_P = mkdir -p
NOSETESTS = nosetests
PIP = pip
PYLINT = pylint
PYTHON = python
RM = rm -f
RM_R = rm -fr
RMDIR = rmdir
TAR = tar

# Flags
FLAKE8_FLAGS = --max-line-length=80 --statistics --doctests --format=pylint
PYLINT_FLAGS = --py3k --output-format=colorized --rcfile=.pylintrc

# These values can be overridden on the command-line or via config.mak
prefix = $(HOME)
bindir = $(prefix)/bin
datadir = $(prefix)/share/git-cola
coladir = $(datadir)/lib
hicolordir = $(prefix)/share/icons/hicolor/scalable/apps
darwin_python = /System/Library/Frameworks/Python.framework/Resources/Python.app/Contents/MacOS/Python
# DESTDIR =

cola_base := git-cola
cola_app_base= $(cola_base).app
cola_app = $(CURDIR)/$(cola_app_base)
cola_version = $(shell $(PYTHON) bin/git-cola version --brief)
cola_dist := $(cola_base)-$(cola_version)

NOSE_FLAGS = --with-doctest
NOSE_FLAGS += --with-id
NOSE_FLAGS += --exclude=sphinxtogithub
NOSE_FLAGS += --exclude=extras
# Allows "make test flags=--stop"
flags =
NOSE ?= $(NOSETESTS) $(NOSE_FLAGS) $(flags)

SETUP ?= $(PYTHON) setup.py
setup_args += --prefix=$(prefix)
setup_args += --quiet
setup_args += --force
setup_args += --install-scripts=$(bindir)
setup_args += --record=build/MANIFEST
setup_args += --install-lib=$(coladir)
ifdef DESTDIR
    setup_args += --root=$(DESTDIR)
    export DESTDIR
endif
export prefix

# If NO_VENDOR_LIBS is specified on the command line then pass it to setup.py
ifdef NO_VENDOR_LIBS
    setup_args += --no-vendor-libs
endif

PYTHON_DIRS = cola
PYTHON_DIRS += test

ALL_PYTHON_DIRS = $(PYTHON_DIRS)
ALL_PYTHON_DIRS += extras

PYTHON_SOURCES = bin/git-cola
PYTHON_SOURCES += bin/git-dag
PYTHON_SOURCES += share/git-cola/bin/git-xbase
PYTHON_SOURCES += setup.py

# User customizations
-include config.mak

all:: build
.PHONY: all

build:
	$(SETUP) build
.PHONY: build

install: all
	$(SETUP) install $(setup_args)
	$(MKDIR_P) $(DESTDIR)$(hicolordir)
	$(LN_S) $(datadir)/icons/git-cola.svg $(DESTDIR)$(hicolordir)/git-cola.svg
	$(LN_S) git-cola $(DESTDIR)$(bindir)/cola
	$(RM_R) $(DESTDIR)$(coladir)/git_cola*
	$(RM_R) git_cola.egg-info
.PHONY: install

# Maintainer's dist target
dist:
	$(GIT) archive --format=tar --prefix=$(cola_dist)/ HEAD^{tree} | \
		$(GZIP) -f -9 - >$(cola_dist).tar.gz
.PHONY: dist

doc:
	$(MAKE) -C share/doc/git-cola all
.PHONY: doc

html:
	$(MAKE) -C share/doc/git-cola html
.PHONY: html

man:
	$(MAKE) -C share/doc/git-cola man
.PHONY: man

install-doc:
	$(MAKE) -C share/doc/git-cola install
.PHONY: install-doc

install-html:
	$(MAKE) -C share/doc/git-cola install-html
.PHONY: install-html

install-man:
	$(MAKE) -C share/doc/git-cola install-man
.PHONY: install-man

uninstall:
	$(RM) $(DESTDIR)$(prefix)/bin/git-cola
	$(RM) $(DESTDIR)$(prefix)/bin/git-dag
	$(RM) $(DESTDIR)$(prefix)/bin/cola
	$(RM) $(DESTDIR)$(prefix)/share/applications/git-cola.desktop
	$(RM) $(DESTDIR)$(prefix)/share/applications/git-cola-folder-handler.desktop
	$(RM) $(DESTDIR)$(prefix)/share/applications/git-dag.desktop
	$(RM) $(DESTDIR)$(prefix)/share/icons/hicolor/scalable/apps/git-cola.svg
	$(RM_R) $(DESTDIR)$(prefix)/share/git-cola
	$(RM_R) $(DESTDIR)$(prefix)/share/doc/git-cola
	$(RM) $(DESTDIR)$(prefix)/share/locale/*/LC_MESSAGES/git-cola.mo
	-$(RMDIR) $(DESTDIR)$(prefix)/share/locale/*/LC_MESSAGES 2>/dev/null
	-$(RMDIR) $(DESTDIR)$(prefix)/share/locale/* 2>/dev/null
	-$(RMDIR) $(DESTDIR)$(prefix)/share/locale 2>/dev/null
	-$(RMDIR) $(DESTDIR)$(prefix)/share/doc 2>/dev/null
	-$(RMDIR) $(DESTDIR)$(prefix)/share/applications 2>/dev/null
	-$(RMDIR) $(DESTDIR)$(prefix)/share 2>/dev/null
	-$(RMDIR) $(DESTDIR)$(prefix)/bin 2>/dev/null
	-$(RMDIR) $(DESTDIR)$(prefix) 2>/dev/null
.PHONY: uninstall

test: all
	$(NOSE) $(PYTHON_DIRS)
.PHONY: test

coverage:
	$(NOSE) --with-coverage --cover-package=cola $(PYTHON_DIRS)
.PHONY: coverage

clean:
	$(FIND) $(ALL_PYTHON_DIRS) -name '*.py[cod]' -print0 | xargs -0 rm -f
	$(RM_R) build dist tags git-cola.app
	$(RM_R) share/locale
	$(MAKE) -C share/doc/git-cola clean
.PHONY: clean

tags:
	$(FIND) $(ALL_PYTHON_DIRS) -name '*.py' -print0 | xargs -0 $(CTAGS) -f tags
.PHONY: tags

pot:
	$(SETUP) build_pot -N -d po
.PHONY: pot

mo:
	$(SETUP) build_mo -f
.PHONY: mo

git-cola.app:
	$(MKDIR_P) $(cola_app)/Contents/MacOS
	$(MKDIR_P) $(cola_app)/Contents/Resources
	$(CP) contrib/darwin/Info.plist contrib/darwin/PkgInfo $(cola_app)/Contents
	$(CP) contrib/darwin/git-cola $(cola_app)/Contents/MacOS
	$(CP) contrib/darwin/git-cola.icns $(cola_app)/Contents/Resources
	$(MAKE) prefix=$(cola_app)/Contents/Resources install install-doc
	$(LN_S) $(darwin_python) $(cola_app)/Contents/Resources/git-cola
.PHONY: git-cola.app

app-tarball: git-cola.app
	$(TAR) czf $(cola_dist).app.tar.gz $(cola_app_base)
.PHONY: app-tarball

# Preview the markdown using "make README.html"
%.html: %.md
	$(MARKDOWN) $< >$@

flake8:
	$(FLAKE8) $(FLAKE8_FLAGS) $(PYTHON_SOURCES) $(PYTHON_DIRS)
.PHONY: flake8

pylint:
	$(PYLINT) $(PYLINT_FLAGS) $(PYTHON_SOURCES) $(ALL_PYTHON_DIRS)
.PHONY: pylint

requirements:
	$(PIP) install --requirement requirements.txt
	$(PIP) install --requirement extras/requirements-dev.txt
.PHONY: requirements
