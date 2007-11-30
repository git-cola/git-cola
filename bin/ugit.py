#!/usr/bin/env python
import sys
from PyQt4 import QtCore, QtGui
from ugitmodel import GitModel
from ugitview import GitView
from ugitcontroller import GitController
if __name__ == "__main__":
	app = QtGui.QApplication (sys.argv)
	model = GitModel()
	view = GitView (app.activeWindow())
	ctl = GitController (model, view)
	view.show()
	sys.exit(app.exec_())
