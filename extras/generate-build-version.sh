#!/bin/sh

GIT=${GIT:-git}

if "$GIT" version 2>&1 >/dev/null && test -e .git
then
    BUILD_VERSION=$("$GIT" describe --first-parent) &&
    echo '"""Generated build version"""' >cola/_build_version.py
    echo "BUILD_VERSION = '$BUILD_VERSION'" >>cola/_build_version.py
fi

exit 0
