#!/usr/bin/env python
# Copyright(C) 2007, David Aguilar <davvid@gmail.com>
# License: GPL v2 or later
import os
import sys
import platform

from PyQt4 import QtGui
from PyQt4 import QtCore

version = platform.python_version()

try:
	thisfile = os.path.realpath(__file__)
	sys.path.insert(0, os.path.dirname(os.path.dirname(thisfile)))
	sys.path.insert(0, os.path.join(
			os.path.dirname(os.path.dirname(thisfile)),
			'lib', 'python' + version[:3],
			'site-packages'))
	sys.path.insert(0, os.path.dirname(thisfile))
except:
	sys.path.insert(0, os.getcwd())


from ugit.models import Model
from ugit.views import View
from ugit.controllers import Controller
from ugit import utils

if __name__ == "__main__":
	app = QtGui.QApplication(sys.argv)
	app.setWindowIcon(QtGui.QIcon(utils.get_icon('git.png')))
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
