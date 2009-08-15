test_flags ?=

all_test_flags ?= --with-doctest --verbose --with-id $(test_flags)

all:
	@cd .. && \
	env PYTHONPATH=$(CURDIR)/..:$(PYTHONPATH) \
	nosetests $(all_test_flags)

clean:
	find $(CURDIR) -name '*.py[co]' -print0 | xargs -0 rm -f
