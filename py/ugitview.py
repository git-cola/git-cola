import os
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import SIGNAL
from ugitWindow import Ui_ugitWindow
from ugitCommandDialog import Ui_ugitCommandDialog
from ugitCommitBrowser import Ui_ugitCommitBrowser

class GitView (Ui_ugitWindow, QtGui.QMainWindow):
	'''The main ugit interface.'''
	def __init__ (self, parent=None, autosetup=True):
		QtGui.QMainWindow.__init__ (self, parent)
		Ui_ugitWindow.__init__ (self)
		if autosetup:
			self.setupUi (self)

class GitCommandDialog (Ui_ugitCommandDialog, QtGui.QDialog):
	'''A simple dialog to display command output.'''
	def __init__ (self, parent=None, output=None, autosetup=True):
		QtGui.QDialog.__init__ (self, parent)
		Ui_ugitCommandDialog.__init__ (self)
		if autosetup:
			self.setupUi (self)
			if output is not None:
				self.set_command_output (output)

	def set_command_output (self, output):
		self.commandText.setText (output)

class GitCommitBrowser (Ui_ugitCommitBrowser, QtGui.QDialog):
	'''A dialog to display commits in for selection.'''
	def __init__ (self, parent=None, autosetup=True):
		QtGui.QDialog.__init__ (self, parent)
		Ui_ugitCommitBrowser.__init__ (self)
		if autosetup:
			self.setupUi (self)
			# Make the commit list slighty larger than the
			# commit message widget
			self.splitter.setSizes ([ 50, 200 ])
