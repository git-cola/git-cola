prefix	?= $(HOME)
DESTDIR	?= /
PYTHON	?= python

all:
	$(PYTHON) setup.py build && rm -rf build

install:
	$(PYTHON) setup.py install \
		--prefix=$(prefix) \
		--root=$(DESTDIR) \
		--force && \
	rm -rf $(DESTDIR)$(prefix)/lib && \
	cd $(DESTDIR)$(prefix)/bin && \
	((! test -e cola && ln -s git-cola cola) || true) && \
	rm -rf build

doc:
	cd share/doc/cola && $(MAKE) all

install-doc:
	$(MAKE) -C share/doc/cola install

install-html:
	$(MAKE) -C share/doc/cola install-html

uninstall:
	rm -rf  "$(DESTDIR)$(prefix)"/bin/git-cola \
		"$(DESTDIR)$(prefix)"/bin/git-difftool* \
		"$(DESTDIR)$(prefix)"/bin/cola \
		"$(DESTDIR)$(prefix)"/share/applications/cola.desktop \
		"$(DESTDIR)$(prefix)"/share/cola \
		"$(DESTDIR)$(prefix)"/share/doc/cola

test:
	@env PYTHONPATH=$(CURDIR):$(PYTHONPATH) \
		nosetests --verbose --with-doctest --with-id

coverage:
	@env PYTHONPATH=$(CURDIR):$(PYTHONPATH) \
		nosetests --verbose --with-doctest --with-id --with-coverage \
		--cover-package=cola

clean:
	for dir in share/doc/cola test; do \
		(cd $$dir && $(MAKE) clean); \
	done
	find cola -name '*.py[co]' -print0 | xargs -0 rm -f
	find cola/gui -name '[^_]*.py' -print0 | xargs -0 rm -f
	find jsonpickle -name '*.py[co]' -print0 | xargs -0 rm -f
	find share -name '*.qm' -print0 | xargs -0 rm -f
	find simplejson -name '*.py[co]' -print0 | xargs -0 rm -f
	rm -rf build tmp
	rm -f tags

tags:
	ctags -R cola/*.py cola/views/*.py cola/controllers/*.py

.PHONY: all install doc install-doc install-html test clean
