#!/bin/sh
cd $(dirname $0)
cd ..
VERSION=$(scripts/version.sh)
BASENAME=ugit-$VERSION
FILE=$BASENAME.tar.gz
BLD=$BASENAME.bld
DIR=installroot
if [ -d $DIR ]; then
	mv $DIR $DIR.old.$$
fi
if [ -e .lock-wscript ]; then
	mv .lock-wscript .lock-wscript.old
fi
./configure --prefix=$DIR --blddir=$BLD \
&& make && make install

if [ $? != 0 ]; then
	echo "error: $?"
	exit
fi

find $DIR -name '*.py[co]' | xargs rm
PYTHONVER=$(python -c 'import sys; sys.stdout.write(sys.version[:3])')

(
	cd $DIR/lib;
	for i in 2.4 2.5; do
		if [ ! -e python$i ]; then
			ln -s python$PYTHONVER python$i
		fi
	done
)

rsync -avr $DIR/ $BASENAME/ \
&& tar czf $FILE $BASENAME/ \
&& rm -rf $DIR $BASENAME $BLD

if [ -d $DIR.old.$$ ]; then
	mv -v $DIR.old.$$ $DIR
fi
if [ -e .lock-wscript.old ]; then
	mv .lock-wscript.old .lock-wscript
fi
if [ -d $HOME/htdocs/ugit/releases ]; then
	mv -v $FILE $HOME/htdocs/ugit/releases
fi
