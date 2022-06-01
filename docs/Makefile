prefix ?= $(CURDIR)
docdir ?= $(prefix)/share/doc/git-cola
htmldir ?= $(docdir)/html
mandir ?= $(prefix)/share/man/man1
# DESTDIR =

# External commands
INSTALL ?= install
MKDIR_P ?= mkdir -p
RSYNC ?= rsync
SED ?= sed

RSYNC_FLAGS = -r --delete --delete-excluded
RSYNC_FLAGS += --exclude=.buildinfo --exclude=.gitignore
RSYNC_CMD = $(RSYNC) $(RSYNC_FLAGS)

SPHINXOPTS = -a
SPHINXBUILD = sphinx-build
PAPER =

# Internal variables.
PAPEROPT_a4 = -D latex_paper_size=a4
PAPEROPT_letter = -D latex_paper_size=letter
ALLSPHINXOPTS = -d _build/doctrees $(PAPEROPT_$(PAPER)) $(SPHINXOPTS) .

.PHONY: all help clean html man dirhtml pickle json
.PHONY: htmlhelp qthelp latex changes linkcheck doctest
.PHONY: install install-files install-html install-man

# The default target of this makefile is...
all:: html man

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  html      to make standalone HTML files"
	@echo "  man       to make manual pages"
	@echo "  dirhtml   to make HTML files named index.html in directories"
	@echo "  pickle    to make pickle files"
	@echo "  json      to make JSON files"
	@echo "  htmlhelp  to make HTML files and a HTML help project"
	@echo "  qthelp    to make HTML files and a qthelp project"
	@echo "  latex     to make LaTeX files, you can set PAPER=a4 or PAPER=letter"
	@echo "  changes   to make an overview of all changed/added/deprecated items"
	@echo "  linkcheck to check all external links for integrity"
	@echo "  doctest   to run all doctests embedded in the documentation (if enabled)"

clean:
	-rm -rf _build/doctrees _build/man _build/html/*

html:
	$(SPHINXBUILD) -b html $(ALLSPHINXOPTS) _build/html

man:
	$(SPHINXBUILD) -b man $(ALLSPHINXOPTS) _build/man

dirhtml:
	$(SPHINXBUILD) -b dirhtml $(ALLSPHINXOPTS) _build/dirhtml

pickle:
	$(SPHINXBUILD) -b pickle $(ALLSPHINXOPTS) _build/pickle

json:
	$(SPHINXBUILD) -b json $(ALLSPHINXOPTS) _build/json

htmlhelp:
	$(SPHINXBUILD) -b htmlhelp $(ALLSPHINXOPTS) _build/htmlhelp

qthelp:
	$(SPHINXBUILD) -b qthelp $(ALLSPHINXOPTS) _build/qthelp

latex:
	$(SPHINXBUILD) -b latex $(ALLSPHINXOPTS) _build/latex

changes:
	$(SPHINXBUILD) -b changes $(ALLSPHINXOPTS) _build/changes

linkcheck:
	$(SPHINXBUILD) -b linkcheck $(ALLSPHINXOPTS) _build/linkcheck

doctest:
	$(SPHINXBUILD) -b doctest $(ALLSPHINXOPTS) _build/doctest

install: install-files install-html install-man

install-files:
	$(MKDIR_P) $(DESTDIR)$(docdir)
	$(INSTALL) -m 644 *.html $(DESTDIR)$(docdir)
	$(INSTALL) -m 644 *.rst $(DESTDIR)$(docdir)

install-html: install-files html
	$(MKDIR_P) $(DESTDIR)$(htmldir)
	$(RSYNC_CMD) _build/html/ $(DESTDIR)$(htmldir)/

install-man: man
	$(MKDIR_P) $(DESTDIR)$(mandir)
	$(INSTALL) -m 644 _build/man/git-cola.1 $(DESTDIR)$(mandir)
	$(INSTALL) -m 644 _build/man/git-dag.1 $(DESTDIR)$(mandir)
