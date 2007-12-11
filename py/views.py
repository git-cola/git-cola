import os
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import SIGNAL
from Window import Ui_Window
from CommandDialog import Ui_CommandDialog
from CommitBrowser import Ui_CommitBrowser
from BranchDialog import Ui_BranchDialog

class GitView (Ui_Window, QtGui.QMainWindow):
	'''The main ugit interface.'''
	def __init__ (self, parent=None, autosetup=True):
		QtGui.QMainWindow.__init__ (self, parent)
		Ui_Window.__init__ (self)
		if autosetup:
			self.setupUi (self)

class GitCommandDialog (Ui_CommandDialog, QtGui.QDialog):
	'''A simple dialog to display command output.'''
	def __init__ (self, parent=None, output=None, autosetup=True):
		QtGui.QDialog.__init__ (self, parent)
		Ui_CommandDialog.__init__ (self)
		if autosetup:
			self.setupUi (self)
			if output is not None:
				self.set_command_output (output)

	def set_command_output (self, output):
		self.commandText.setHtml (output)

class GitBranchDialog (Ui_BranchDialog, QtGui.QDialog):
	'''A dialog to display available branches.'''
	def __init__ (self, parent=None, autosetup=True):
		QtGui.QDialog.__init__ (self, parent)
		Ui_BranchDialog.__init__ (self)
		if autosetup:
			self.setupUi (self)
			self.reset()

	def reset (self):
		self.branches = []
		self.comboBox.clear()

	def addBranches (self, branches):
		for branch in branches:
			self.branches.append (branch)
			self.comboBox.addItem (branch)

	def getSelectedBranch (self):
		return self.branches [ self.comboBox.currentIndex() ]

class GitCommitBrowser (Ui_CommitBrowser, QtGui.QDialog):
	'''A dialog to display commits in for selection.'''
	def __init__ (self, parent=None, autosetup=True):
		QtGui.QDialog.__init__ (self, parent)
		Ui_CommitBrowser.__init__ (self)
		if autosetup:
			self.setupUi (self)
			# Make the commit list slighty larger than the
			# commit message widget
			self.splitter.setSizes ([ 50, 200 ])
