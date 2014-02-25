#!/bin/sh

# Author: Aaron Cook <cookacounty@gmail.com>

# This script will build git-cola on an older Linux distribution,
# e.g. RHEL 5.

# This script assumes you have the appropriate tars already downloaded
# (adjust the versions as needed, or set the appropriate COLA_* variables)
# Note the "rm -rf" at the beginning.
# Replace COLA_PREFIX with your path, or set the COLA_PREFIX environment
# variable.

# Set COLA_NUM_JOBS to control the number of cores used to build.
# This script defaults to 2.
# The only real trick was the python compile options for the utf.
# You should run
# "make prefix=$HOME/apps/git-cola PYTHON=$HOME/apps/git-cola/bin/python install"
# in the git-cola repo after running this script.

# To run git cola, use it directly through $COLA_PREFIX/bin/git-cola.
# There is also a softlink at $COLA_PREFIX/bin/cola.
# You can add the $COLA_PREFIX/bin to your PATH or softlink git-cola (or cola)
# from a directory that is already in your PATH.

# This is the directory where git-cola will be installed
COLA_PREFIX=${COLA_PREFIX:-"$HOME/apps/git-cola"}

COLA_NUM_JOBS=${COLA_NUM_JOBS:-2}
COLA_QT=${COLA_QT:-qt-x11-opensource-src-4.4.3}
COLA_PYQT=${COLA_PYQT:-PyQt-x11-gpl-4.10.1}
COLA_SIP=${COLA_SIP:-sip-4.14.6}
COLA_PYTHON=${COLA_PYTHON:-Python-2.7.5}

rm -rf "$COLA_PREFIX"
mkdir -p "$COLA_PREFIX"

rm -rf "$COLA_QT" "$COLA_PYQT" "$COLA_SIP" "$COLA_PYTHON"

tar -zxvf "$COLA_QT".tar.gz
tar -zxvf "$COLA_PYQT".tar.gz
tar -zxvf "$COLA_SIP".tar.gz
tar -zxvf "$COLA_PYTHON".tgz

compile_top="$PWD"

cd "$compile_top/$COLA_QT"
./configure -prefix $COLA_PREFIX -confirm-license
make -j "$COLA_NUM_JOBS" && make install

cd "$compile_top/$COLA_PYTHON"
./configure --prefix=$COLA_PREFIX --enable-unicode=ucs4
make -j "$COLA_NUM_JOBS" && make install

pybin="$COLA_PREFIX/bin/python"

cd "$compile_top/$COLA_SIP"
"$pybin" ./configure.py &&
make -j "$COLA_NUM_JOBS" && make install

cd "$compile_top/$COLA_PYQT"
"$pybin" ./configure.py -q "$COLA_PREFIX/bin/qmake" &&
make -j "$COLA_NUM_JOBS" && make install
