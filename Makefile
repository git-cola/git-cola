# The default target of this Makefile is...
.PHONY: all
all::

# Development
# -----------
# make V=1                      # V=1 increases verbosity
# make develop                  # pip install --editable .
# make test [flags=...]         # run tests; flags=-x fails fast, --ff failed first
# make test V=2                 # run tests; V=2 increases test verbosity
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
# make i18n     # make pot + make po
#
# Installation
# ------------
# make prefix=<path> install
# DESTDIR is also supported.
#
# The external commands used by this Makefile are...
BLACK = black
CP = cp
FIND = find
FLAKE8 = flake8
GREP = grep
GIT = git
MARKDOWN = markdown
MSGMERGE = msgmerge
MKDIR_P = mkdir -p
PIP = pip
PYTHON ?= python
PYTHON3 ?= python3
PYLINT = $(PYTHON) -B -m pylint
PYTEST = $(PYTHON) -B -m pytest
RM = rm -f
RM_R = rm -fr
RMDIR = rmdir
TAR = tar
TOX = tox
XARGS = xargs
XGETTEXT = xgettext

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

PYLINT_SCORE_FLAG := $(shell $(PYLINT) --score=no --help >/dev/null 2>&1 && echo " --score=no" || true)
PYLINT_FLAGS = --rcfile=.pylintrc
ifdef color
    PYLINT_FLAGS += --output-format=colorized
endif
ifneq ($(PYLINT_SCORE_FLAGSCORE),)
    PYLINT_FLAGS += $(PYLINT_SCORE_FLAG)
endif

# These values can be overridden on the command-line or via config.mak
prefix = $(HOME)
python_version := $(shell $(PYTHON) -c 'import sys; print("%s.%s" % sys.version_info[:2])')
python_lib = python$(python_version)/site-packages
pythondir = $(prefix)/lib/$(python_lib)
# DESTDIR =

cola_base := git-cola
cola_app_base= $(cola_base).app
cola_app = $(CURDIR)/$(cola_app_base)
cola_app_resources = $(cola_app)/Contents/Resources

# Read $(VERSION) from cola/_version.py and strip quotes.
include cola/_version.py
cola_version := $(subst ',,$(VERSION))
cola_dist := $(cola_base)-$(cola_version)

install_args =
ifdef DESTDIR
	install_args += --root="$(DESTDIR)"
	export DESTDIR
endif
install_args += --prefix="$(prefix)"
export prefix

PYTHON_DIRS = cola
PYTHON_DIRS += test

ALL_PYTHON_DIRS = $(PYTHON_DIRS)

# User customizations
-include config.mak

all::

.PHONY: install
install:: all
	$(PIP) $(QUIET) $(VERBOSE) install $(install_args) .

.PHONY: doc
doc::
	$(MAKE) -C docs all

.PHONY: html
html::
	$(MAKE) -C docs html

.PHONY: man
man::
	$(MAKE) -C docs man

.PHONY: install-doc
install-doc::
	$(MAKE) -C docs install

.PHONY: install-html
install-html::
	$(MAKE) -C docs install-html

.PHONY: install-man
install-man::
	$(MAKE) -C docs install-man

.PHONY: uninstall
uninstall::
	$(RM) "$(DESTDIR)$(prefix)"/bin/cola
	$(RM) "$(DESTDIR)$(prefix)"/bin/git-cola
	$(RM) "$(DESTDIR)$(prefix)"/bin/git-cola-sequence-editor
	$(RM) "$(DESTDIR)$(prefix)"/bin/git-dag
	$(RM) "$(DESTDIR)$(prefix)"/share/applications/git-cola.desktop
	$(RM) "$(DESTDIR)$(prefix)"/share/applications/git-cola-folder-handler.desktop
	$(RM) "$(DESTDIR)$(prefix)"/share/applications/git-dag.desktop
	$(RM) "$(DESTDIR)$(prefix)"/share/metainfo/git-dag.appdata.xml
	$(RM) "$(DESTDIR)$(prefix)"/share/metainfo/git-cola.appdata.xml
	$(RM) "$(DESTDIR)$(prefix)"/share/icons/hicolor/scalable/apps/git-cola.svg
	$(RM_R) "$(DESTDIR)$(prefix)"/share/doc/git-cola
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
test::
	$(PYTEST) $(PYTEST_FLAGS) $(flags) $(PYTHON_DIRS)

.PHONY: coverage
coverage::
	$(PYTEST) $(PYTEST_FLAGS) --cov=cola $(flags) $(PYTHON_DIRS)

.PHONY: clean
clean::
	$(FIND) $(ALL_PYTHON_DIRS) -name '*.py[cod]' -print0 | $(XARGS) -0 $(RM)
	$(FIND) $(ALL_PYTHON_DIRS) -name __pycache__ -print0 | $(XARGS) -0 $(RM_R)
	$(RM_R) build dist tags git-cola.app
	$(MAKE) -C docs clean

# Update i18n files
.PHONY: i18n
i18n:: pot
i18n:: po

# Regenerate git-cola.pot with new translations
.PHONY: pot
pot::
	$(XGETTEXT) \
		--language=Python \
		--keyword=N_ \
		--no-wrap \
		--no-location \
		--omit-header \
		--sort-output \
		--output-dir cola/i18n \
		--output git-cola.pot \
		cola/*.py \
		cola/*/*.py

# Update .po files with new translations from git-cola.pot
.PHONY: po
po::
	for po in cola/i18n/*.po; \
	do \
		$(MSGMERGE) \
			--no-location \
			--no-wrap \
			--no-fuzzy-matching \
			--sort-output \
			--output-file $$po.new \
			$$po \
			cola/i18n/git-cola.pot \
			&& \
		mv $$po.new $$po; \
	\
	done

# Build a git-cola.app bundle.
.PHONY: git-cola.app
git-cola.app::
	$(MKDIR_P) $(cola_app)/Contents/MacOS
	$(MKDIR_P) $(cola_app_resources)
	$(PYTHON3) -m venv $(cola_app_resources)
	$(cola_app_resources)/bin/pip install --requirement requirements/requirements.txt
	$(cola_app_resources)/bin/pip install --requirement requirements/requirements-optional.txt
	$(cola_app_resources)/bin/pip install --requirement requirements/requirements-dev.txt

	$(CP) contrib/darwin/Info.plist contrib/darwin/PkgInfo $(cola_app)/Contents
	$(CP) contrib/darwin/git-cola $(cola_app)/Contents/MacOS
	$(CP) contrib/darwin/git-cola.icns $(cola_app)/Contents/Resources
	$(MAKE) PIP=$(cola_app_resources)/bin/pip \
		prefix=$(cola_app_resources) install
	$(MAKE) SPHINXBUILD=$(cola_app_resources)/bin/sphinx-build \
		prefix=$(cola_app_resources) install-doc

.PHONY: app-tarball
app-tarball:: git-cola.app
	$(TAR) czf $(cola_dist).app.tar.gz $(cola_app_base)

# Preview the markdown using "make README.html"
%.html: %.md
	$(MARKDOWN) $< >$@

.PHONY: flake8
flake8::
	$(FLAKE8) --version
	$(FLAKE8) $(FLAKE8_FLAGS) $(flags) \
	$(ALL_PYTHON_DIRS) contrib

.PHONY: pylint3k
pylint3k::
	$(PYLINT) --version
	$(PYLINT) $(PYLINT_FLAGS) --py3k $(flags) \
	$(ALL_PYTHON_DIRS)

.PHONY: pylint
pylint::
	$(PYLINT) --version
	$(PYLINT) $(PYLINT_FLAGS) $(flags) \
	$(ALL_PYTHON_DIRS)

# Pre-commit checks
.PHONY: check
ifdef file
check::
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
format::
	$(GIT) ls-files -- '*.py' | \
	$(GREP) -v ^qtpy | \
	$(XARGS) $(BLACK) --skip-string-normalization

# Run "make develop" from inside a newly created virtualenv to create an
# editable installation.
.PHONY: develop
develop::
	$(PIP) install --editable .

.PHONY: requirements
requirements::
	$(PIP) install --requirement requirements/requirements.txt

.PHONY: requirements-dev
requirements-dev::
	$(PIP) install --requirement requirements/requirements-dev.txt

.PHONY: requirements-optional
requirements-optional::
	$(PIP) install --requirement requirements/requirements-optional.txt

.PHONY: tox
tox::
	$(TOX) $(TOX_FLAGS) $(flags)

.PHONY: tox-check
tox-check::
	$(TOX) $(TOX_FLAGS) --parallel auto -e "$(TOX_ENVS)" $(flags)
