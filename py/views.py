import os
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import SIGNAL
from Window import Ui_Window
from CommandDialog import Ui_CommandDialog
from CommitBrowser import Ui_CommitBrowser
from BranchDialog import Ui_BranchDialog
from CreateBranchDialog import Ui_CreateBranchDialog

class GitView (Ui_Window, QtGui.QMainWindow):
	'''The main ugit interface.'''
	def __init__ (self, parent=None):
		QtGui.QMainWindow.__init__ (self, parent)
		Ui_Window.__init__ (self)
		self.setupUi (self)
		self.display_splitter.setSizes ([ 300, 400 ])

class GitCommandDialog (Ui_CommandDialog, QtGui.QDialog):
	'''A simple dialog to display command output.'''
	def __init__ (self, parent=None, output=None):
		QtGui.QDialog.__init__ (self, parent)
		Ui_CommandDialog.__init__ (self)
		self.setupUi (self)
		if output: self.set_command_output (output)

	def set_command_output (self, output):
		self.commandText.setHtml (output)

class GitBranchDialog (Ui_BranchDialog, QtGui.QDialog):
	'''A dialog to display available branches.'''
	def __init__ (self, parent=None):
		QtGui.QDialog.__init__ (self, parent)
		Ui_BranchDialog.__init__ (self)
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
	def __init__ (self, parent=None):
		QtGui.QDialog.__init__ (self, parent)
		Ui_CommitBrowser.__init__ (self)
		self.setupUi (self)
		# Make the list widget slighty larger
		self.splitter.setSizes ([ 50, 200 ])

class GitCreateBranchDialog (Ui_CreateBranchDialog, QtGui.QDialog):
	'''A dialog for creating or updating branches.'''
	def __init__ (self, parent=None):
		QtGui.QDialog.__init__ (self, parent)
		Ui_CreateBranchDialog.__init__ (self)
		self.setupUi (self)
