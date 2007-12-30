#!/bin/sh
FILE="$1".tar.gz
DIR=installroot

if [ $# -lt 1 ]; then
	echo "usage: mktar [BASENAME]"; exit -1
fi
if [ -d $DIR ]; then
	mv $DIR $DIR.old.$$
fi

scripts/build-win32.sh

if [ -e "$1" ]; then
	echo "error: $1 exists"
	exit -1
fi
rsync -avr $DIR/ "$1/"
tar czf "$FILE" "$1/"
rm -rf $DIR "$1"
if [ -d $DIR.old.$$ ]; then
	mv -v $DIR.old.$$ $DIR
fi
if [ -e $HOME/htdocs/ugit ]; then
	mv -v "$FILE" $HOME/htdocs/ugit
fi
