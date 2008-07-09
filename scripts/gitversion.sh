#!/bin/sh
VN=$(git describe HEAD 2>/dev/null)
VN=$(echo "$VN" | sed -e 's/-/./g')
LF='
'
case "$VN" in
*$LF*) (exit 1) ;;
v[0-9]*)
    test -z "$(git diff-index --name-only HEAD)" ||
        VN="$VN-dirty" ;;
esac
VN=$(expr "$VN" : v*'\(.*\)')
echo "VERSION='$VN'"
