#!/bin/sh

waf_backup()
{
	if [ -e .lock-wscript ]; then
		mv .lock-wscript .lock-wscript.old
	fi
}

waf_restore()
{
	if [ -e .lock-wscript.old ]; then
		mv .lock-wscript.old .lock-wscript
	fi
}

try_python()
{
	waf_backup
		echo "+------------------------------------------------"
		echo "+ PYTHON=$1"
		echo "+------------------------------------------------"
		if [ ! -x "$1" ]; then
			echo "$1 is not executable."
			exit -1
		fi
		env PYTHON="$1" \
			./configure \
				--prefix="$2" \
				--blddir="$PWD/tmp.$$" &&
		make &&
		make install
		status=$?

		rm -rf "$PWD/tmp.$$"

		if test -z $status; then
			echo "exited with status code $status"
			exit $status
		fi


	waf_restore
}

cd $(dirname $0)
cd ..

VERSION=$(scripts/version.sh)
