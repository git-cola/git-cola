#!/bin/sh
unset CDPATH
COLA_TOP=$(git rev-parse --show-toplevel)
curdir=$(pwd)
cd "$(dirname "$0")"
META=$(pwd)
cd "$curdir"
unset curdir

# This variable must be defined in config
GITHUB_TOKEN=UNDEFINED

WIN32_LOGIN=Administrator@localhost
WIN32_SSH_PORT=2002
WIN32_COLA_DIR=git-cola
WIN32_PYTHON=/c/Python27
WIN32_GIT="/c/Progra~1/Git/bin"

DOCUMENT_ROOT="$COLA_TOP/../git-cola.github.com"
RELEASES="$DOCUMENT_ROOT/releases"

# _the_ cola version
if test -e bin/git-cola && test -z "$VERSION"
then
	VERSION=$(bin/git-cola version --brief)
	vVERSION="v$VERSION"
fi

if test -e "$META/config"
then
	. "$META/config"
fi

do_or_die() {
	if ! "$@"; then
		status=$?
		echo "error running: $@"
		echo "exit status: $status"
		exit $status
	fi
}

title() {
	echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
	echo "$*"
	echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
}

ensure_dir_exists() {
	if ! test -d "$1"; then
		do_or_die mkdir -p "$1"
	fi
}
