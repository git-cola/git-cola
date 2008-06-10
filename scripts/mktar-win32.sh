#!/bin/sh
. $(dirname $0)/common.sh

VERSION=$(scripts/version.sh)
BASENAME=cola-win32-$VERSION
FILE=$BASENAME.tar.gz
DIR=installroot

if [ -d $DIR ]; then
	echo "ERROR: '$DIR' already exists."
	exit -1
fi

scripts/build-win32.sh || exit -1

if [ -e $BASENAME ]; then
	echo "error: $BASENAME exists"
	exit -1
fi
rsync -avr $DIR/ $BASENAME/
tar czf $FILE $BASENAME/
rm -rf $DIR $BASENAME
if [ -e $HOME/htdocs/cola/releases ]; then
	mv -v $FILE $HOME/htdocs/cola/releases
fi
