#!/bin/sh
unset CDPATH

curdir="$(pwd)"
cd "$(dirname "$0")"
META="$(pwd)"
cd "$curdir"
unset curdir

# _the_ cola version
if test -e bin/git-cola
then
	VERSION=$(bin/git-cola version | awk '{print $3}')
fi

WEB_SOURCE="$HOME"/src/cola-web

RELEASE_TREE="$HOME"/src/cola.tuxfamily.org
RELEASE_TREE_DOC="$RELEASE_TREE"
RELEASE_TREE_RELEASES="$RELEASE_TREE"/releases
RELEASE_TREE_WIN32="$RELEASE_TREE_RELEASES"/win32
RELEASE_TREE_DARWIN="$RELEASE_TREE_RELEASES"/darwin

TF_USER=unknown
TF_HTDOCS=/home/gitcola/cola.tuxfamily.org-web/htdocs
TF_SSH_HOST=ssh.tuxfamily.org

if test -e "$META"/config.sh
then
	. "$META"/config.sh
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
	echo
	echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
	echo "    $@"
	echo "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
	echo
}

ensure_dir_exists() {
	if ! test -d "$1"; then
		do_or_die mkdir -p "$1"
	fi
}
