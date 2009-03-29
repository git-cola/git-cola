# Copyright (C) 2009, David Aguilar <davvid@gmail.com>
"""Provides the cola QApplication subclass"""

import os

from PyQt4 import QtCore
from PyQt4 import QtGui

from cola import utils


class ColaApplication(QtGui.QApplication):
    """This makes translation work by throwing away the context
    """

    def __init__(self, argv, locale=None):
        """Initialize our QApplication for translation
        """
        QtGui.QApplication.__init__(self, argv)

        # Handle i18n -- load translation files and install a translator
        # We do this by monkey-patching QApplication.translate
        self._translate = QtGui.QApplication.translate
        QtGui.QApplication.translate = self.translate
        if not locale:
            locale = str(QtCore.QLocale().system().name())
        qmfile = utils.get_qm_for_locale(locale)
        if os.path.exists(qmfile):
            translator = QtCore.QTranslator(self)
            translator.load(qmfile)
            self.installTranslator(translator)

        self.setWindowIcon(QtGui.QIcon(utils.get_icon('git.png')))

    def translate(self, context, *args):
        """Supports @@noun/@@verb and context-less translation
        """
        # We set the context to '' to properly handle .qm files
        trtxt = unicode(self._translate('', *args))
        if trtxt[-6:-4] == '@@': # handle @@verb / @@noun
            trtxt = trtxt[:-6]
        return trtxt
