#!/bin/sh
. $(dirname $0)/common.sh
waf_backup
	dpkg-buildpackage -A
waf_restore

rm -rf debian/bld
rm -rf debian/ugit
rm ../ugit_*.changes
mv ../ugit_*.deb .
