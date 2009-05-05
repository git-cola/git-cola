#!/bin/sh
pinstall() {
    sudo port -v install "$@"
}

pinstall autoconf
pinstall gettext
pinstall zlib
pinstall qt4-mac
pinstall python25
pinstall python_select

sudo python_select python25

pinstall py25-macholib-devel
pinstall py25-sip
pinstall py25-pyqt4
pinstall py25-py2app-devel
pinstall py25-nose
