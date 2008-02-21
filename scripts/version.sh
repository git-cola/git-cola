#!/bin/sh
unset CDPATH
cd $(dirname $0)
cd ..
eval echo $(grep VERSION wscript | perl -p -e 's/.*= //')
