all:
	@env PYTHONPATH=$(CURDIR)/..:$(PYTHONPATH) \
		nosetests --verbose --with-doctest --with-id

clean:
	find $(CURDIR) -name '*.py[co]' -print0 | xargs -0 rm -f
