prefix	?= $(HOME)
DESTDIR	?= /
PYTHON	?= python

all:
	$(PYTHON) setup.py build

install:
	$(PYTHON) setup.py install --prefix=$(prefix) --root=$(DESTDIR) --force
	cd $(DESTDIR)$(prefix)/bin && rm -f cola && ln -s git-cola cola

doc:
	cd share/doc/cola && $(MAKE) all

install-doc:
	$(MAKE) -C share/doc/cola install

install-html:
	$(MAKE) -C share/doc/cola install-html

test:
	@env PYTHONPATH=$(CURDIR):$(CURDIR)/build/lib:$(PYTHONPATH) nosetests

clean:
	for dir in share/doc/cola test; do \
		(cd $$dir && $(MAKE) clean); \
	done
	find cola -name '*.py[co]' -print0 | xargs -0 rm -f
	find cola/gui -name '[^_]*.py' -print0 | xargs -0 rm -f
	find share -name '*.qm' -print0 | xargs -0 rm -f
	rm -rf build tmp
	rm -f tags

tags:
	ctags -R cola/*.py cola/views/*.py cola/controllers/*.py

.PHONY: all install doc install-doc install-html test clean
