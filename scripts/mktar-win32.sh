#!/bin/sh
cd $(dirname $0)
cd ..

VERSION=$(scripts/version.sh)
BASENAME=ugit-win32-$VERSION
FILE=$BASENAME.tar.gz
DIR=installroot

if [ -d $DIR ]; then
	mv $DIR $DIR.old.$$
fi

scripts/build-win32.sh

if [ -e $BASENAME ]; then
	echo "error: $BASENAME exists"
	exit -1
fi
rsync -avr $DIR/ $BASENAME/
tar czf $FILE $BASENAME/
rm -rf $DIR $BASENAME
if [ -d $DIR.old.$$ ]; then
	mv -v $DIR.old.$$ $DIR
fi
if [ -e $HOME/htdocs/ugit/releases ]; then
	mv -v $FILE $HOME/htdocs/ugit/releases
fi
