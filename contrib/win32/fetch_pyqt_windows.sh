#!/bin/bash

set -e

# Download and the PyQt4 Windows installer and unpack files from it into
# pynsist_pkgs

cd "$(dirname "0")"

PY_VERSION=2.7
PYQT_VERSION=4.11.4
QT_VERSION=4.8.7
BITNESS=32

INSTALLER_FILE=PyQt4-${PYQT_VERSION}-gpl-Py${PY_VERSION}-Qt${QT_VERSION}-x${BITNESS}.exe
URL=http://sourceforge.net/projects/pyqt/files/PyQt4/PyQt-${PYQT_VERSION}/${INSTALLER_FILE}

if ! test -e "$INSTALLER_FILE"
then
    echo "Downloading $URL"
    curl --location "$URL/download" -o "$INSTALLER_FILE"
fi

rm -rf pyqt4-windows
mkdir pyqt4-windows
7z x -opyqt4-windows "$INSTALLER_FILE"

PKGS=../../pynsist_pkgs
rm -rf $PKGS
mkdir $PKGS

echo "Rearranging files into pynsist_pkgs..."
mv 'pyqt4-windows/Lib/site-packages'/* $PKGS
rm $PKGS/PyQt4/assistant.exe $PKGS/PyQt4/designer.exe

rm -r pyqt4-windows
echo "Done"
