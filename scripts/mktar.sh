#!/bin/sh
. $(dirname $0)/common.sh
BASENAME=ugit-$VERSION
FILE=$BASENAME.tar.gz
DIR=installroot
if [ -d $DIR ]; then
	echo "ERROR: '$DIR' already exists"
	exit -1
fi

try_python "$(which python)" "$DIR"

rsync -avr $DIR/ $BASENAME/ &&
tar czf $FILE $BASENAME/ &&
rm -rf $DIR $BASENAME

if [ -d $HOME/htdocs/ugit/releases ]; then
	mv -v $FILE $HOME/htdocs/ugit/releases
fi
