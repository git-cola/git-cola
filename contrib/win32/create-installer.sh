#!/bin/sh
cd "$(git rev-parse --show-toplevel)"

WIN32="$PWD/contrib/win32"

if ! test -d "$WIN32"
then
	echo "Please run this script from the git-cola source tree"
	exit 1
fi

# Add Python and Gettext to our path
for python in "/c/Python27" "/c/Python26" "/c/Python25"
do
	if test -d "$python"
	then
		break
	fi
done
PATH="$python":/bin:/usr/bin:/mingw/bin:"/c/Program Files/Gnu/bin":"$WIN32":"$PATH"
export PATH

VERSION=$(bin/git-cola version --brief)

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
ROOT=$BASENAME
TARGET="$ROOT".exe

echo "Building installer for git-cola $VERSION"

python setup.py --quiet install \
	--prefix="$ROOT" \
	--install-scripts="$ROOT"/bin
rm -rf "$ROOT/lib" "$ROOT/Lib" build

cp "$BASENAME/bin/git-cola" $BASENAME/bin/git-cola.pyw
cp "$BASENAME/bin/git-dag" $BASENAME/bin/git-dag.pyw
mkdir -p $ETC 2>/dev/null
cp "$WIN32/git.bmp" "$WIN32/gpl-2.0.rtf" "$WIN32/git.ico" "$ETC"

NOTES="$ETC/ReleaseNotes.txt"

printf "git-cola: v$VERSION\nBottled-on: $(date)\n\n\n" > $NOTES
printf "To run cola, just type 'cola' from a Git Bash session.\n\n\n" >> $NOTES

tag=$(git tag | tail -2 | head -1)
echo "--------------------------------------------------------" >> $NOTES
echo "      Changes since $tag" >> $NOTES
echo "--------------------------------------------------------" >> $NOTES
echo >> $NOTES
git shortlog $tag.. >> $NOTES

# LF -> CRLF
vim -c "set ff=dos" -c "wq" $NOTES
sed -e "s/%APPVERSION%/$VERSION/" -e "s@%OUTPUTDIR%@""$PWD""@" \
	< "$WIN32/install.iss" > "$BASENAME/install.iss" &&
(
	cd "$BASENAME" &&
	echo "Lauching Inno Setup compiler ..." &&
	/share/InnoSetup/ISCC.exe install.iss |
	grep -Ev "\s*Reading|\s*Compressing"
) &&
rm -rf "$BASENAME"
