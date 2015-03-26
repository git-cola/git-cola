#!/usr/bin/env bash
# Download and the PyQt4 Windows installer and unpack files from it into
# pynsist_pkgs

set -e

PY_VERSION=3.4
PYQT_VERSION=4.11.3
QT_VERSION=4.8.6
BITNESS=32

INSTALLER_FILE=PyQt4-${PYQT_VERSION}-gpl-Py${PY_VERSION}-Qt${QT_VERSION}-x${BITNESS}.exe
URL=http://sourceforge.net/projects/pyqt/files/PyQt4/PyQt-${PYQT_VERSION}/${INSTALLER_FILE}
#wget -O "$INSTALLER_FILE" "$URL"

rm -rf pyqt4-windows
mkdir pyqt4-windows
7z x -opyqt4-windows "$INSTALLER_FILE"

rm -rf pynsist_pkgs
mkdir pynsist_pkgs

echo "Rearranging files into pynsist_pkgs..."
mv 'pyqt4-windows/Lib/site-packages'/* pynsist_pkgs/
rm pynsist_pkgs/PyQt4/assistant.exe pynsist_pkgs/PyQt4/designer.exe
mv 'pyqt4-windows/$_OUTDIR/'*.pyd pynsist_pkgs/PyQt4/
# These may not be necessary:
mv 'pyqt4-windows/$_OUTDIR/qsci/' 'pyqt4-windows/$_OUTDIR/sip/' pynsist_pkgs/PyQt4/

rm -r pyqt4-windows
echo "Done"
