# The default target of this Makefile is...
.PHONY: all
all::

# Usage
# -----
# make prefix=<path> install           # Install git-cola
#
# make doc                             # Build documentation
# make prefix=<path> install-doc       # Install documentation
#
# Variables
# ---------
# prefix - Installation prefix.
# DESTDIR - Temporary staging directory.
#
# The external commands used by this Makefile are...
CP = cp
FIND = find
MKDIR_P = mkdir -p
PIP = pip
PYTHON ?= python3
RM = rm -f
RM_R = rm -fr
RMDIR = rmdir
XARGS = xargs

# These values can be overridden on the command-line or via config.mak
# DESTDIR =
prefix = $(HOME)
python_version := $(shell $(PYTHON) -c 'import sys; print("%s.%s" % sys.version_info[:2])')
python_lib = python$(python_version)/site-packages
pythondir = $(prefix)/lib/$(python_lib)

cola_base := git-cola
cola_app_base= $(cola_base).app
cola_app = $(CURDIR)/$(cola_app_base)
cola_app_resources = $(cola_app)/Contents/Resources

# Read $(VERSION) from cola/_version.py and strip quotes.
include cola/_version.py
cola_version := $(subst ',,$(VERSION))

install_args =
ifdef DESTDIR
	install_args += --root="$(DESTDIR)"
	export DESTDIR
endif
install_args += --prefix="$(prefix)"
install_args += --disable-pip-version-check
install_args += --ignore-installed
install_args += --no-deps
export prefix

PYTHON_DIRS = cola
PYTHON_DIRS += test

ALL_PYTHON_DIRS = $(PYTHON_DIRS)

# User customizations
-include config.mak

all::

.PHONY: install
install:: all
	$(PIP) install $(install_args) .

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

.PHONY: clean
clean::
	$(FIND) $(ALL_PYTHON_DIRS) -name '*.py[cod]' -print0 | $(XARGS) -0 $(RM)
	$(FIND) $(ALL_PYTHON_DIRS) -name __pycache__ -print0 | $(XARGS) -0 $(RM_R)
	$(RM_R) build dist git-cola.app
	$(MAKE) -C docs clean

# Build a git-cola.app bundle.
.PHONY: git-cola.app
git-cola.app::
    cola_full_version := $(shell ./bin/git-cola version --brief)

git-cola.app::
	$(MKDIR_P) $(cola_app)/Contents/MacOS
	$(MKDIR_P) $(cola_app_resources)
	$(PYTHON) -m venv $(cola_app_resources)
	$(cola_app_resources)/bin/pip install '.[docs,extras,pyqt6]'
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

.PHONY: test
test::
	@if type garden >/dev/null 2>&1; then \
		garden test; \
	else \
		echo 'warning: "make test" requires "garden" https://gitlab.com/garden-rs/garden'; \
		echo 'tip: run "cargo install garden-tools" to install "garden".'; \
	fi
