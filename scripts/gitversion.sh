#!/bin/sh
unset CDPATH #just in case
cd $(dirname $0)
. ./version.sh >/dev/null
VN=$(git rev-parse HEAD 2>/dev/null | cut -c1-7)
LF='
'
case "$VN" in
*$LF*) (exit 1) ;;
[0-9]*)
	test -z "$(git diff-index --name-only HEAD)" ||
		VN="$VN-dirty" ;;
esac
echo "VERSION='$VERSION.$VN'"
