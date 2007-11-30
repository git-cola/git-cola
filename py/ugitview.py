import os
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import SIGNAL
from ugitWindow import Ui_ugitWindow
class GitView(Ui_ugitWindow, QtGui.QMainWindow):
	def __init__(self, parent=None, autosetup=True):
		QtGui.QMainWindow.__init__(self, parent)
		Ui_ugitWindow.__init__(self)
		if autosetup:
			self.setupUi(self)
