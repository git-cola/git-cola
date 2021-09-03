# The default target of this Makefile is...
all::

# Development
# -----------
# make V=1                      # generate files; V=1 increases verbosity
# make test [flags=...]         # run tests; flags=-x fails fast, --ff failed first
# make test V=2                 # V=2 increases test verbosity
# make doc                      # build docs
# make flake8                   # python style checks
# make pylint [color=1]         # run pylint; color=1 colorizes output
# make pylint3k [color=1]       # run python2+3 compatibility checks
# make format                   # run the black python formatter
# make check [color=1]          # run test, doc, flake8, pylint3k, and pylint
# make check file=<filename>    # run checks on <filename>
#
# Release Prep
# ------------
# make pot      # update main translation template
# make po       # merge translations
# make mo       # generate message files
# make i18n     # all three of the above
#
# Installation
# ------------
# make prefix=<path> install
# DESTDIR is also supported.
#
# To disable distutil's replacement of "#!/usr/bin/env python" with
# the path to the build environment's python, pass USE_ENV_PYTHON=1
# when invoking make.
#
# The external commands used by this Makefile are...
BLACK = black
CTAGS = ctags
CP = cp
FIND = find
FLAKE8 = flake8
GREP = grep
GIT = git
GZIP = gzip
LN = ln
LN_S = $(LN) -s -f
MARKDOWN = markdown
MKDIR_P = mkdir -p
PIP = pip
PYTHON ?= python
PYLINT = $(PYTHON) -B -m pylint
PYTEST = $(PYTHON) -B -m pytest
RM = rm -f
RM_R = rm -fr
RMDIR = rmdir
TAR = tar
TOX = tox
XARGS = xargs

# Flags
# -----
ifdef V
    VERBOSE = --verbose
    ifeq ($(V),2)
        TEST_VERBOSE = --verbose
        VERBOSE_SHORT = -vv
    else
        VERBOSE_SHORT = -v
    endif
else
    QUIET = --quiet
endif

FLAKE8_FLAGS = $(VERBOSE)

PYTEST_FLAGS = $(QUIET) $(TEST_VERBOSE)
uname_S := $(shell uname -s)
ifneq ($(uname_S),Linux)
    PYTEST_FLAGS += --ignore=cola/inotify.py
endif

TOX_FLAGS = $(VERBOSE_SHORT) --develop --skip-missing-interpreters
TOX_ENVS ?= py{27,36,37,38,39,lint}

PYLINT_SCORE_FLAG := $(shell sh -c '$(PYLINT) --score=no --help >/dev/null 2>&1 && echo " --score=no" || true')
PYLINT_FLAGS = --rcfile=.pylintrc
ifdef color
    PYLINT_FLAGS += --output-format=colorized
endif
ifneq ($(PYLINT_SCORE_FLAGSCORE),)
    PYLINT_FLAGS += $(PYLINT_SCORE_FLAG)
endif

# These values can be overridden on the command-line or via config.mak
prefix = $(HOME)
bindir = $(prefix)/bin
datadir = $(prefix)/share/git-cola
python_lib := $(shell $(PYTHON) -c \
    'import distutils.sysconfig as sc; print(sc.get_python_lib(prefix=""))')
pythondir = $(prefix)/$(python_lib)
hicolordir = $(prefix)/share/icons/hicolor/scalable/apps
# DESTDIR =

cola_base := git-cola
cola_app_base= $(cola_base).app
cola_app = $(CURDIR)/$(cola_app_base)

# Read $(VERSION) from cola/_version.py and strip quotes.
include cola/_version.py
cola_version := $(subst ',,$(VERSION))
cola_dist := $(cola_base)-$(cola_version)

SETUP ?= $(PYTHON) setup.py

build_args += build
ifdef USE_ENV_PYTHON
    build_args += --use-env-python
endif

install_args += install
install_args += --prefix="$(prefix)"
install_args += --force
install_args += --install-scripts="$(bindir)"
install_args += --record=build/MANIFEST
ifdef DESTDIR
    install_args += --root="$(DESTDIR)"
    export DESTDIR
endif
export prefix

ifdef NO_PRIVATE_LIBS
    install_args += --no-private-libs
endif
ifdef NO_VENDOR_LIBS
    install_args += --no-vendor-libs
endif

PYTHON_DIRS = cola
PYTHON_DIRS += test

ALL_PYTHON_DIRS = $(PYTHON_DIRS)
ALL_PYTHON_DIRS += extras

PYTHON_SOURCES = bin/git-cola
PYTHON_SOURCES += bin/git-cola-sequence-editor
PYTHON_SOURCES += bin/git-dag
PYTHON_SOURCES += setup.py

# User customizations
-include config.mak

.PHONY: all
all:: build

.PHONY: build_version
build_version:
	@GIT=$(GIT) ./extras/generate-build-version.sh 2>/dev/null || true

.PHONY: build
build: build_version
	$(SETUP) $(QUIET) $(VERBOSE) $(build_args)

.PHONY: install
install: all
	$(SETUP) $(QUIET) $(VERBOSE) $(install_args)
	$(MKDIR_P) "$(DESTDIR)$(hicolordir)"
	$(LN_S) "$(datadir)/icons/git-cola.svg" \
		"$(DESTDIR)$(hicolordir)/git-cola.svg"
	$(LN_S) git-cola "$(DESTDIR)$(bindir)/cola"

.PHONY: doc
doc:
	$(MAKE) -C share/doc/git-cola all

.PHONY: html
html:
	$(MAKE) -C share/doc/git-cola html

.PHONY: man
man:
	$(MAKE) -C share/doc/git-cola man

.PHONY: install-doc
install-doc:
	$(MAKE) -C share/doc/git-cola install

.PHONY: install-html
install-html:
	$(MAKE) -C share/doc/git-cola install-html

.PHONY: install-man
install-man:
	$(MAKE) -C share/doc/git-cola install-man

.PHONY: uninstall
uninstall:
	$(RM) "$(DESTDIR)$(prefix)"/bin/git-cola
	$(RM) "$(DESTDIR)$(prefix)"/bin/git-cola-sequence-editor
	$(RM) "$(DESTDIR)$(prefix)"/bin/git-dag
	$(RM) "$(DESTDIR)$(prefix)"/bin/cola
	$(RM) "$(DESTDIR)$(prefix)"/share/applications/git-cola.desktop
	$(RM) "$(DESTDIR)$(prefix)"/share/applications/git-cola-folder-handler.desktop
	$(RM) "$(DESTDIR)$(prefix)"/share/applications/git-dag.desktop
	$(RM) "$(DESTDIR)$(prefix)"/share/metainfo/git-dag.appdata.xml
	$(RM) "$(DESTDIR)$(prefix)"/share/metainfo/git-cola.appdata.xml
	$(RM) "$(DESTDIR)$(prefix)"/share/icons/hicolor/scalable/apps/git-cola.svg
	$(RM_R) "$(DESTDIR)$(prefix)"/share/doc/git-cola
	$(RM_R) "$(DESTDIR)$(prefix)"/share/git-cola
	$(RM) "$(DESTDIR)$(prefix)"/share/locale/*/LC_MESSAGES/git-cola.mo
	$(RM_R) "$(DESTDIR)$(pythondir)"/git_cola-*
	$(RM_R) "$(DESTDIR)$(pythondir)"/cola
	$(RMDIR) -p "$(DESTDIR)$(pythondir)" 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)"/share/applications 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)"/share/metainfo 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)"/share/doc 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)"/share/locale/*/LC_MESSAGES 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)"/share/locale/* 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)"/share/locale 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)"/share/icons/hicolor/scalable/apps 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)"/share/icons/hicolor/scalable 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)"/share/icons/hicolor 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)"/share/icons 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)"/share 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)"/bin 2>/dev/null || true
	$(RMDIR) "$(DESTDIR)$(prefix)" 2>/dev/null || true

.PHONY: test
test: all
	$(PYTEST) $(PYTEST_FLAGS) $(flags) $(PYTHON_DIRS)

.PHONY: coverage
coverage:
	$(PYTEST) $(PYTEST_FLAGS) --cov=cola $(flags) $(PYTHON_DIRS)

.PHONY: clean
clean:
	$(FIND) $(ALL_PYTHON_DIRS) -name '*.py[cod]' -print0 | $(XARGS) -0 $(RM)
	$(FIND) $(ALL_PYTHON_DIRS) -name __pycache__ -print0 | $(XARGS) -0 $(RM_R)
	$(RM_R) build dist tags git-cola.app
	$(RM_R) share/locale
	$(MAKE) -C share/doc/git-cola clean

.PHONY: tags
tags:
	$(FIND) $(ALL_PYTHON_DIRS) -name '*.py' -print0 | $($XARGS) -0 $(CTAGS) -f tags

# Update i18n files
.PHONY: i18n
i18n:: pot
i18n:: po
i18n:: mo

.PHONY: pot
pot:
	$(SETUP) build_pot --build-dir=po --no-lang

.PHONY: po
po:
	$(SETUP) build_pot --build-dir=po

.PHONY: mo
mo:
	$(SETUP) build_mo --force

.PHONY: git-cola.app
git-cola.app:
	$(MKDIR_P) $(cola_app)/Contents/MacOS
	$(MKDIR_P) $(cola_app)/Contents/Resources
	$(CP) contrib/darwin/Info.plist contrib/darwin/PkgInfo \
	$(cola_app)/Contents
	$(CP) contrib/darwin/git-cola $(cola_app)/Contents/MacOS
	$(CP) contrib/darwin/git-cola.icns $(cola_app)/Contents/Resources
	$(MAKE) prefix=$(cola_app)/Contents/Resources install install-doc

.PHONY: app-tarball
app-tarball: git-cola.app
	$(TAR) czf $(cola_dist).app.tar.gz $(cola_app_base)

# Preview the markdown using "make README.html"
%.html: %.md
	$(MARKDOWN) $< >$@

.PHONY: flake8
flake8:
	$(FLAKE8) --version
	$(FLAKE8) $(FLAKE8_FLAGS) $(flags) \
	$(PYTHON_SOURCES) $(ALL_PYTHON_DIRS) contrib

.PHONY: pylint3k
pylint3k:
	$(PYLINT) --version
	$(PYLINT) $(PYLINT_FLAGS) --py3k $(flags) \
	$(PYTHON_SOURCES) $(ALL_PYTHON_DIRS)

.PHONY: pylint
pylint:
	$(PYLINT) --version
	$(PYLINT) $(PYLINT_FLAGS) $(flags) \
	$(PYTHON_SOURCES) $(ALL_PYTHON_DIRS)

# Pre-commit checks
.PHONY: check
ifdef file
check:
	$(FLAKE8) $(FLAKE8_FLAGS) $(flags) $(file)
	$(PYLINT) $(PYLINT_FLAGS) --output-format=colorized $(flags) $(file)
	$(PYLINT) $(PYLINT_FLAGS) --output-format=colorized --py3k $(flags) $(file)
else
# NOTE: flake8 is not part of "make check" because the pytest-flake8 plugin runs flake8
# checks during "make test" via pytest.
check:: all
check:: test
check:: doc
check:: pylint3k
check:: pylint
endif

.PHONY: format
format:
	$(GIT) ls-files -- '*.py' | \
	$(GREP) -v ^qtpy | \
	$(XARGS) $(BLACK) --skip-string-normalization --target-version=py27
	$(BLACK) --skip-string-normalization --target-version=py27 $(PYTHON_SOURCES)

.PHONY: requirements
requirements:
	$(PIP) install --requirement requirements/requirements.txt

.PHONY: requirements-dev
requirements-dev:
	$(PIP) install --requirement requirements/requirements-dev.txt

.PHONY: tox
tox:
	$(TOX) $(TOX_FLAGS) $(flags)

.PHONY: tox-check
tox-check:
	$(TOX) $(TOX_FLAGS) --parallel auto -e "$(TOX_ENVS)" $(flags)
