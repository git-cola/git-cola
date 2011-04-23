# Copyright (C) 2009, David Aguilar <davvid@gmail.com>
"""Provides the cola QApplication subclass"""
# style note: we use camelCase here since we're masquerading a Qt class

import os

from PyQt4 import QtCore
from PyQt4 import QtGui

from cola import utils
from cola import resources
from cola import i18n
from cola.decorators import memoize


@memoize
def instance(argv):
    return QtGui.QApplication(list(argv))


class ColaApplication(object):
    """The main cola application

    ColaApplication handles i18n of user-visible data
    """

    def __init__(self, argv, locale=None, gui=True):
        """Initialize our QApplication for translation
        """
        if locale:
            os.environ['LANG'] = locale
        i18n.install()

        # monkey-patch Qt's translate() to use our translate()
        if gui:
            self._app = instance(tuple(argv))
            self._app.setWindowIcon(QtGui.QIcon(resources.icon('git.svg')))
            self._translate_base = QtGui.QApplication.translate
            QtGui.QApplication.translate = self.translate
        else:
            self._app = QtCore.QCoreApplication(argv)
            self._translate_base = QtCore.QCoreApplication.translate
            QtCore.QCoreApplication.translate = self.translate

    def translate(self, context, txt):
        """
        Translate strings with gettext

        Supports @@noun/@@verb specifiers.

        """
        trtxt = i18n.gettext(txt)
        if trtxt[-6:-4] == '@@': # handle @@verb / @@noun
            trtxt = trtxt[:-6]
        return trtxt

    def activeWindow(self):
        """Wrap activeWindow()"""
        return self._app.activeWindow()

    def exec_(self):
        """Wrap exec_()"""
        return self._app.exec_()

    def setStyleSheet(self, txt):
        """Wrap setStyleSheet(txt)"""
        return self._app.setStyleSheet(txt)
