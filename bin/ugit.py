#!/usr/bin/env python
# Copyright(C) 2007, David Aguilar <davvid@gmail.com>
# License: GPL v2 or later
import os
import sys
import platform

from PyQt4 import QtGui
from PyQt4 import QtCore

version = platform.python_version()
ugit = os.path.realpath(__file__)
sys.path.insert(0, os.path.dirname(os.path.dirname(ugit)))
sys.path.insert(0, os.path.join(
		os.path.dirname(os.path.dirname(ugit)),
		'lib', 'python' + version[:3],
		'site-packages'))
sys.path.insert(0, os.path.dirname(ugit))

from ugitlibs.models import Model
from ugitlibs.views import View
from ugitlibs.controllers import Controller
from ugitlibs import utils

if __name__ == "__main__":
	app = QtGui.QApplication(sys.argv)
	locale = str(QtCore.QLocale().system().name())
	qmfile = utils.get_qm_for_locale(locale)
	if os.path.exists(qmfile):
		translator = QtCore.QTranslator()
		translator.load(qmfile)
		app.installTranslator(translator)
	model = Model()
	view = View(app.activeWindow())
	ctl = Controller(model, view)
	view.show()
	sys.exit(app.exec_())
