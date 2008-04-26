#!/bin/sh
. $(dirname $0)/common.sh
waf_backup
	dpkg-buildpackage -A
waf_restore

rm -rf debian/bld
rm -rf debian/ugit
rm ../ugit_*.changes
mv ../ugit_*.deb .

alien --to-rpm ugit_*.deb

if [ -d $HOME/htdocs/ugit/releases ];
then
	mv ugit_*.deb ugit-*.rpm $HOME/htdocs/ugit/releases
fi
