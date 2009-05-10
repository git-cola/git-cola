#!/bin/sh
# as root
if test -d /opt/local/bin; then
	PATH=/opt/local/bin:"$PATH"
	export PATH
fi
getport() {
    port -v install "$@"
}

getport python25
getport python_select

python_select python25

getport subversion
getport py25-macholib-devel
getport py25-py2app-devel
getport py25-nose
getport py25-pyqt4
