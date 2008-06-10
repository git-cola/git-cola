#!/bin/sh
. $(dirname $0)/common.sh

PREFIX=installroot
BINDIR=$PREFIX/bin
DOCDIR=$PREFIX/share/doc/cola

try_python /usr/bin/python2.5 "$PREFIX"

# no symlinks on win32
rm -f $BINDIR/bin/cola

cp scripts/py2exe-* $BINDIR
cp scripts/cola-win32.sh $BINDIR

mkdir -p $DOCDIR
cp README $DOCDIR/README.txt
