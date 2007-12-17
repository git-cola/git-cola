#!/usr/bin/env python
# Copyright (C) 2007, David Aguilar <davvid@gmail.com>
# License: GPL v2 or later
import os
import sys
import platform
version = platform.python_version()
sys.path.insert (0, os.path.join(
		os.path.dirname (os.path.dirname(__file__)),
		'lib', 'python' + version[:3],
		'site-packages'))
sys.path.insert (0, os.path.dirname(__file__))

from PyQt4 import QtCore, QtGui
from ugitlibs.models import GitModel
from ugitlibs.views import GitView
from ugitlibs.controllers import GitController
if __name__ == "__main__":
	app = QtGui.QApplication (sys.argv)
	model = GitModel()
	view = GitView (app.activeWindow())
	ctl = GitController (model, view)
	view.show()
	sys.exit(app.exec_())
