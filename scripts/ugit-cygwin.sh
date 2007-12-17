#!/bin/sh

# This worked for me.  I used the default Python2.5 download
# from python.org and the default PyQt4 binary package from Riverbank.
# YMMV.
# Why does PYTHONPATH use backslashes?
# Because we want a native Windows Python, not cygwin's python.
ME=`realpath $0`
DIR=`dirname $0`
PATH=/cygwin/c/Python25:$PATH
PYTHONPATH="$DIR"
export PATH PYTHONPATH
exec python "$DIR"/ugit.py
