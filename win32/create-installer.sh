#!/bin/sh

if ! test -d win32; then
	echo "Please run this script from the root of the cola source tree"
	exit 1
fi

# Add Python and Gettext to our path
PATH=/c/Python26:"/c/Program Files/Gnu/bin":"$PWD"/win32:"$PATH"
export PATH

VERSION=$(bin/git-cola version | awk '{print $3}')

while test $# -gt 0;
do
	case "$1" in
	-v|--version)
		shift
		VERSION="$1"
		shift
		;;
	*)
		echo "Usage: $0 [--version <version>]"
		exit 1
		;;
	esac
done

BASENAME=git-cola-$VERSION
ETC=$BASENAME/etc
ROOT="$PWD"/$BASENAME
TARGET="$ROOT".exe

echo "Building installer for git-cola v$VERSION"

python setup.py --quiet install \
	--root="$ROOT" \
	--prefix='.' \
	--install-scripts=bin
rm -rf "$ROOT"/lib "$ROOT"/Lib build

cp $BASENAME/bin/git-cola $BASENAME/bin/git-cola.pyw
mkdir -p $ETC 2>/dev/null
cp win32/git.bmp win32/gpl-2.0.rtf win32/git.ico $ETC

NOTES=$ETC/ReleaseNotes.txt

printf "git-cola: v$VERSION\nBottled-on: $(date)\n\n\n" > $NOTES
printf "To run cola, just type 'cola' from a Git Bash session.\n\n\n" >> $NOTES
if test -f meta/ReleaseNotes; then
	cat meta/ReleaseNotes  >> $NOTES
fi

tag=$(git tag | tail -2 | head -1)
echo "--------------------------------------------------------" >> $NOTES
echo "      Changes since $tag" >> $NOTES
echo "--------------------------------------------------------" >> $NOTES
echo >> $NOTES
git shortlog $tag.. >> $NOTES

# LF -> CRLF
vim -c "set ff=dos" -c "wq" $NOTES

OUTPUTDIR="$(pwd -W)" &&
sed -e "s/%APPVERSION%/$VERSION/" -e "s@%OUTPUTDIR%@$OUTPUTDIR@" \
	< win32/install.iss > $BASENAME/install.iss &&
cd "$BASENAME" &&
echo "Lauching Inno Setup compiler ..." &&
/share/InnoSetup/ISCC.exe install.iss /q | grep -Ev "\s*Reading|\s*Compressing" &&
cd .. &&
rm -rf "$BASENAME"
