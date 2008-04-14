#!/bin/sh
. $(dirname $0)/common.sh

PREFIX=installroot
BINDIR=$PREFIX/bin
DOCDIR=$PREFIX/share/doc/ugit

try_python /usr/bin/python2.5 "$PREFIX"
mkdir -p $DOCDIR
# no symlinks on win32
rm -f $BINDIR/bin/ugit

cp scripts/py2exe-* $BINDIR
cp scripts/ugit-win32.sh $BINDIR
cp README $DOCDIR/README.txt
