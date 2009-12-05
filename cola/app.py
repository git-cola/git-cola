# Copyright (C) 2009, David Aguilar <davvid@gmail.com>
"""Provides the cola QApplication subclass"""
# style note: we use camelCase here since we're masquerading a Qt class

import os

from PyQt4 import QtCore
from PyQt4 import QtGui

from cola import utils
from cola import resources

_app = None
def instance(argv):
    global _app
    if not _app:
        _app = QtGui.QApplication(argv)
    return _app


class ColaApplication(object):
    """The main cola application

    ColaApplication handles i18n of user-visible data
    """

    def __init__(self, argv, locale=None, gui=True):
        """Initialize our QApplication for translation
        """
        # monkey-patch Qt's app translate() to handle .po files
        if gui:
            self._app = instance(argv)
            self._app.setWindowIcon(QtGui.QIcon(resources.icon('git.svg')))
            self._translate_base = QtGui.QApplication.translate
            QtGui.QApplication.translate = self.translate
        else:
            self._app = QtCore.QCoreApplication(argv)
            self._translate_base = QtCore.QCoreApplication.translate
            QtCore.QCoreApplication.translate = self.translate

        # Find the current language settings and apply them
        if not locale:
            locale = str(QtCore.QLocale().system().name())

        qmfile = utils.qm_for_locale(locale)
        if os.path.exists(qmfile):
            translator = QtCore.QTranslator(self._app)
            translator.load(qmfile)
            self._app.installTranslator(translator)

    def translate(self, context, txt):
        """Supports @@noun/@@verb and context-less translation
        """
        # We set the context to '' to properly handle .qm files
        trtxt = unicode(self._translate_base('', txt))
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
