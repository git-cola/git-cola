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
# make pylint [color=1]         # run pylint; color=1 colorizes output
# make fmt                      # run the code formatter
# make check [color=1]          # run test, doc and pylint
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
CERCIS = cercis
CP = cp
FIND = find
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

PYTEST_FLAGS = $(QUIET) $(TEST_VERBOSE)
uname_S := $(shell uname -s)
ifneq ($(uname_S),Linux)
    PYTEST_FLAGS += --ignore=cola/inotify.py
endif

TOX_FLAGS = $(VERBOSE_SHORT) --develop --skip-missing-interpreters
TOX_ENVS ?= py{36,37,38,39,310,311}

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
install_args += --disable-pip-version-check
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
    cola_full_version := $(shell ./bin/git-cola version --brief)

git-cola.app::
	$(MKDIR_P) $(cola_app)/Contents/MacOS
	$(MKDIR_P) $(cola_app_resources)
	$(PYTHON3) -m venv $(cola_app_resources)
	$(cola_app_resources)/bin/pip install --requirement requirements/requirements.txt
	$(cola_app_resources)/bin/pip install --requirement requirements/requirements-optional.txt
	$(cola_app_resources)/bin/pip install --requirement requirements/requirements-dev.txt

	$(CP) contrib/darwin/Info.plist contrib/darwin/PkgInfo $(cola_app)/Contents
ifneq ($(cola_full_version),)
	sed -i -e s/0.0.0.0/$(cola_full_version)/ $(cola_app)/Contents/Info.plist
endif
	sed -i -e s/0.0.0/$(cola_version)/ $(cola_app)/Contents/Info.plist
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

.PHONY: pylint
pylint::
	$(PYLINT) --version
	$(PYLINT) $(PYLINT_FLAGS) $(flags) \
	$(ALL_PYTHON_DIRS)

# Pre-commit checks
.PHONY: check
ifdef file
check::
	$(PYLINT) $(PYLINT_FLAGS) --output-format=colorized $(flags) $(file)
else
check:: all
check:: test
check:: doc
check:: pylint
endif

.PHONY: fmt
fmt::
	$(GIT) ls-files -- '*.py' | \
	$(GREP) -v ^qtpy | \
	$(XARGS) $(CERCIS)

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
	$(TOX) $(TOX_FLAGS) --parallel auto -e "${TOX_ENVS}" $(flags)

.PHONY: tox-check
tox-check::
	$(TOX) $(TOX_FLAGS) --parallel auto -e check $(flags)
