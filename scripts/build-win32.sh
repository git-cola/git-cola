#!/bin/sh
PREFIX=installroot
BINDIR=$PREFIX/bin
UGITLIBS=$PREFIX/ugitlibs
ICONDIR=$PREFIX/share/ugit/icons
QMDIR=$PREFIX/share/ugit/qm
DOCDIR=$PREFIX/share/doc/ugit
cd $(dirname $0)
cd ..

mkdir -p $BINDIR
mkdir -p $UGITLIBS
mkdir -p $ICONDIR
mkdir -p $QMDIR
mkdir -p $DOCDIR

cp README $DOCDIR/README.txt
cp bin/* $BINDIR
cp scripts/ugit-win32.sh $BINDIR
cp scripts/py2exe-* $BINDIR
cp ugit/* $UGITLIBS
cp icons/* $ICONDIR

PYUIC4=$(which pyuic4)
if [ -z $PYUIC4 ] || [ ! -x $PYUIC4 ]; then
	echo
	echo "Could not find pyuic4."
	echo "You need the pyqt4 developer tools in order to build ugit."
	echo
else
	for file in ui/*.ui; do
		BASENAME=$(basename $file .ui)
		$PYUIC4 -x $file -o $UGITLIBS/$BASENAME.py
	done
fi

MSGFMT=$(which msgfmt)
if [ -z $MSGFMT ] || [ ! -x $MSGFMT ]; then
	echo
	echo "Could not find msgfmt."
	echo "You need the msgfmt from GNU gettext in order to create"
	echo "the translation files for ugit."
	echo
else
	for file in po/*.po; do
		BASENAME=$(basename $file .po)
		$MSGFMT --qt -o $QMDIR/$BASENAME.qm $file
	done
fi
