#!/bin/sh
PYUIC4=`which pyuic4`
PREFIX=installroot
BINDIR=$PREFIX/bin
UGITLIBS=$PREFIX/ugitlibs
ICONDIR=$PREFIX/share/ugit/icons
QMDIR=$PREFIX/share/ugit/qm
cd `dirname $0`
cd ..

if [ -z $PYUIC4 ] || [ ! -x $PYUIC4 ]; then
	echo
	echo "Could not find pyuic4."
	echo "You need the pyqt4 developer tools in order to build ugit."
	echo
fi

mkdir -p $UGITLIBS
mkdir -p $ICONDIR
mkdir -p $QMDIR

cp README $PREFIX/README.txt
cp bin/* scripts/ugit-*.sh $BINDIR
cp ugitlibs/* $UGITLIBS
cp icons/* $ICONDIR


if [ -x $PYUIC4 ] && [ ! -z $PYUIC4 ]; then
	for file in ui/*.ui; do
			pyuic4 -x $file -o $UGITLIBS/`basename $file .ui`.py
	done
fi

for file in po/*.po; do
	msgfmt --qt -o $QMDIR/`basename $file .po`.qm $file
done
