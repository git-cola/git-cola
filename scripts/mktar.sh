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

rsync -avr $DIR/ $BASENAME/ &&
tar czf $FILE $BASENAME/ &&
rm -rf $DIR $BASENAME

if [ -d $HOME/htdocs/ugit/releases ]; then
	mv -v $FILE $HOME/htdocs/ugit/releases
fi
