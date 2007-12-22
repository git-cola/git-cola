#!/bin/sh
PYUIC4=`which pyuic4`
PREFIX=installroot
UGITLIBS=$PREFIX/ugitlibs
cd `dirname $0`
cd ..

echo
echo "This is not for mass consumption."
echo "To create files for distribution, use:"
echo
echo "./configure --prefix=/usr --destdir=/my/destdir for that."
echo

if [ -z $PYUIC4 ] || [ ! -x $PYUIC4 ]; then
	echo
	echo "Could not find pyuic4."
	echo "You need the pyqt4 developer tools in order to build ugit."
	echo
fi

mkdir -p $UGITLIBS
cp README $PREFIX/README.txt
cp bin/ugit.py $PREFIX
cp scripts/ugit-*.sh $PREFIX
cp ugitlibs/* $UGITLIBS


if [ -x $PYUIC4 ] && [ ! -z $PYUIC4 ]; then
	for file in ui/*.ui; do
			pyuic4 -x $file -o $UGITLIBS/`basename $file .ui`.py
	done
fi

echo "Done building."
echo "Run 'python $PREFIX/ugit.py' to launch ugit"
