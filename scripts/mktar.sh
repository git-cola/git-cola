#!/bin/sh
if [ $# -lt 1 ]; then
	echo "usage: mktar [BASENAME]"; exit -1
fi
FILE="$1".tar.gz
BLD="$1".bld
DIR=installroot
if [ -d $DIR ]; then
	mv $DIR $DIR.old."$$"
fi
./configure --prefix=$DIR --blddir="$BLD" \
&& make && make install \
&& rsync -avr $DIR/ "$1/" \
&& tar czf "$FILE" "$1/" \
&& rm -rf $DIR "$1" "$BLD"

if [ -d $DIR.old.$$ ]; then
	mv -v $DIR.old.$$ $DIR
fi
if [ -e $HOME/htdocs/ugit ]; then
	mv -v "$FILE" $HOME/htdocs/ugit
fi
