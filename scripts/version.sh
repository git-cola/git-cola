#!/bin/sh
unset CDPATH
cd $(dirname $0)
cd ..
eval echo $(grep VERSION ugit/defaults.py | perl -p -e 's/.*= //')
