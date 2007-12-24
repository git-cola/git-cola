import os
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QDialog
from Window import Ui_Window
from CommandDialog import Ui_CommandDialog
from CommitBrowser import Ui_CommitBrowser
from BranchDialog import Ui_BranchDialog
from CreateBranchDialog import Ui_CreateBranchDialog
from PushDialog import Ui_PushDialog

from syntax import GitSyntaxHighlighter

class GitView(Ui_Window, QtGui.QMainWindow):
	'''The main ugit interface.'''
	def __init__(self, parent=None):
		QtGui.QMainWindow.__init__(self, parent)
		Ui_Window.__init__(self)
		self.setupUi(self)
		GitSyntaxHighlighter(self.displayText.document())

class GitCommandDialog(Ui_CommandDialog, QtGui.QDialog):
	'''A simple dialog to display command output.'''
	def __init__(self, parent=None, output=None):
		QtGui.QDialog.__init__(self, parent)
		Ui_CommandDialog.__init__(self)
		self.setupUi(self)
		if output: self.set_command(output)

	def set_command(self, output):
		self.commandText.setText(output)

class GitBranchDialog(Ui_BranchDialog, QtGui.QDialog):
	'''A dialog to display available branches.'''
	def __init__(self, parent=None, branches=None):
		QtGui.QDialog.__init__(self, parent)
		Ui_BranchDialog.__init__(self)
		self.setupUi(self)
		self.reset()
		if branches: self.addBranches(branches)

	def reset(self):
		self.branches = []
		self.comboBox.clear()

	def addBranches(self, branches):
		for branch in branches:
			self.branches.append(branch)
			self.comboBox.addItem(branch)

	def getSelectedBranch(self):
		self.show()
		if self.exec_() == QDialog.Accepted:
			return self.branches [ self.comboBox.currentIndex() ]
		else:
			return None

class GitCommitBrowser(Ui_CommitBrowser, QtGui.QDialog):
	'''A dialog to display commits in for selection.'''
	def __init__(self, parent=None):
		QtGui.QDialog.__init__(self, parent)
		Ui_CommitBrowser.__init__(self)
		self.setupUi(self)
		# Make the list widget slighty larger
		self.splitter.setSizes([ 50, 200 ])
		GitSyntaxHighlighter(self.commitText.document())

class GitCreateBranchDialog(Ui_CreateBranchDialog, QtGui.QDialog):
	'''A dialog for creating or updating branches.'''
	def __init__(self, parent=None):
		QtGui.QDialog.__init__(self, parent)
		Ui_CreateBranchDialog.__init__(self)
		self.setupUi(self)

class GitPushDialog(Ui_PushDialog, QtGui.QDialog):
	'''A dialog for pushing branches.'''
	def __init__(self, parent=None):
		QtGui.QDialog.__init__(self, parent)
		Ui_PushDialog.__init__(self)
		self.setupUi(self)
