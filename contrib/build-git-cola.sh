#!/bin/sh

# Build a complete Python 2.7, Qt4, PyQt4, and git-cola development
# environment from scratch.  This can be used on e.g. RHEL5 where the
# system-provided versions are too old.

# See contrib/build-git-cola.yaml for more details
./contrib/travis-build ./contrib/build-git-cola.yaml "$@"
