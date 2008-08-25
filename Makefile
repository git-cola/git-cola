prefix	?= $(HOME)
DESTDIR	?= /
PYTHON	?= python

all:
	$(PYTHON) setup.py build

install:
	$(PYTHON) setup.py install --prefix=$(prefix) --root=$(DESTDIR) --force
	cd $(DESTDIR)$(prefix)/bin && rm -f cola && ln -s git-cola cola

## # TODO: doc, install-doc, install-html
## doc:
## 	cd Documentation && $(MAKE) all
##
## install-doc:
## 	$(MAKE) -C Documentation install
##
## install-html:
## 	$(MAKE) -C Documentation install-html

test: all
	cd t && $(MAKE) all

clean:
## 	for dir in Documentation t; do \
## 		(cd $$dir && $(MAKE) clean); \
## 	done
	rm -rf build tmp
	find cola t -name '*.py[co]' -print0 | xargs -0 rm -f
	find cola/views -name '[^_]*.py' -print0 | xargs -0 rm -f
	find po -name '*.qm' -print0 | xargs -0 rm -f
	rm -f tags

tags:
	ctags -R cola/*.py cola/views/*.py cola/controllers/*.py

.PHONY: all install doc install-doc install-html test clean
