#!/bin/sh
. $(dirname $0)/common.sh
waf_backup
    dpkg-buildpackage -A
waf_restore

rm -rf debian/bld
rm -rf debian/cola
rm ../cola_*.changes
mv ../cola_*.deb .

alien --to-rpm cola_*.deb

if [ -d $HOME/htdocs/cola/releases ];
then
    mv cola_*.deb cola-*.rpm $HOME/htdocs/cola/releases
fi
