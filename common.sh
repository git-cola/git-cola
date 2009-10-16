#!/bin/sh
unset CDPATH

pushd "$(dirname "$0")" >/dev/null
META="$(pwd)"
popd >/dev/null

# _the_ cola version
VERSION=$(bin/git-cola version | awk '{print $3}')

BASENAME=cola-$VERSION
TARBALL="$BASENAME"-src.tar.gz

RELEASE_TREE="$HOME"/src/cola.tuxfamily.org
RELEASE_TREE_DOC="$RELEASE_TREE"
RELEASE_TREE_RELEASES="$RELEASE_TREE"/releases
RELEASE_TREE_WIN32="$RELEASE_TREE_RELEASES"/win32
RELEASE_TREE_DARWIN="$RELEASE_TREE_RELEASES"/darwin


do_or_die() {
	if ! "$@"; then
		status=$?
		echo "error running: $@"
		echo "exit status: $status"
		exit $status
	fi
}

title() {
	echo
	echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
	echo "    $@"
	echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
	echo
}

ensure_dir_exists() {
	if ! test -d "$1"; then
		mkdir -p "$1"
	fi
}
