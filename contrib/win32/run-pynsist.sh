#!/bin/sh
rm -rf build/nsis &&
make all &&
make doc &&
make htmldir="$PWD/share/doc/git-cola/html" install-doc &&
pynsist pynsist.cfg &&
rm -r share/doc/git-cola/html
