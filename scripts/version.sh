#!/bin/sh
unset CDPATH
cd $(dirname $0)
cd ..
eval echo $(grep VERSION ugitlibs/defaults.py | perl -p -e 's/.*= //')
