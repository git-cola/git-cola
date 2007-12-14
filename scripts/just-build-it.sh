#!/bin/sh

# If waf doesn't work for you (and you're too busy to
# properly setup $PYTHONPATH) then you can try this
# script

PYUIC4=`which pyuic4`
if [ -z $PYUIC4 ] || [ ! -x $PYUIC4 ]; then
	echo
	echo "ERROR:"
	echo "Could not find pyuic4."
	echo "You need the pyqt4 developer tools in order to build ugit."
	echo "You can also download an installation snapshot from:"
	echo "    http://ugit.justroots.com/"
	echo
	exit -1
fi

cd `dirname $0`
cd ..
mkdir -p installroot/ugitlibs
cp bin/ugit.py installroot/
cp py/* installroot/ugitlibs/

for file in ui/*.ui; do
	pyuic4 -x $file -o installroot/ugitlibs/`basename $file .ui`.py
done

echo "Done building."
echo "Run 'python installroot/ugit.py' to laucnh ugit"
