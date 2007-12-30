import os
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QMainWindow
from Window import Ui_Window
from CommandDialog import Ui_CommandDialog
from CommitBrowser import Ui_CommitBrowser
from BranchDialog import Ui_BranchDialog
from CreateBranchDialog import Ui_CreateBranchDialog
from PushDialog import Ui_PushDialog
from syntax import DiffSyntaxHighlighter
import qtutils

class View(Ui_Window, QMainWindow):
	'''The main ugit interface.'''
	def __init__(self, parent=None):
		QMainWindow.__init__(self, parent)
		Ui_Window.__init__(self)
		self.setupUi(self)

		DiffSyntaxHighlighter(self.displayText.document())

		# Qt does not handle noun/verb support
		self.commitButton.setText(qtutils.tr('Commit@@verb'))
		self.menuCommit.setTitle(qtutils.tr('Commit@@verb'))

		self.set_display = self.displayText.setText
		self.set_info = self.displayLabel.setText

		self.action_undo = self.commitText.undo
		self.action_redo = self.commitText.redo
		self.action_paste = self.commitText.paste
		self.action_select_all = self.commitText.selectAll

	def action_cut(self):
		self.action_copy()
		self.action_delete()

	def action_copy(self):
		cursor = self.commitText.textCursor()
		selection = cursor.selection().toPlainText()
		qtutils.set_clipboard(selection)

	def action_delete(self):
		self.commitText.textCursor().removeSelectedText()

	def reset_display(self):
		self.set_display('')
		self.set_info('')

	def copy_display(self):
		cursor = self.displayText.textCursor()
		selection = cursor.selection().toPlainText()
		qtutils.set_clipboard(selection)

	def diff_selection(self):
		cursor = self.displayText.textCursor()
		offset = cursor.position()
		selection = cursor.selection().toPlainText()
		num_selected_lines = selection.count(os.linesep)
		return offset, selection


class CommandDialog(Ui_CommandDialog, QDialog):
	'''A simple dialog to display command output.'''
	def __init__(self, parent=None, output=None):
		QDialog.__init__(self, parent)
		Ui_CommandDialog.__init__(self)
		self.setupUi(self)
		if output: self.set_output(output)

	def set_output(self, output):
		self.commandText.setText(output)

class BranchDialog(Ui_BranchDialog, QDialog):
	'''A dialog for choosing branches.'''

	def __init__(self, parent=None, branches=None):
		QDialog.__init__(self, parent)
		Ui_BranchDialog.__init__(self)
		self.setupUi(self)
		self.reset()
		if branches: self.add(branches)

	def reset(self):
		self.branches = []
		self.comboBox.clear()

	def add(self, branches):
		for branch in branches:
			self.branches.append(branch)
			self.comboBox.addItem(branch)

	def get_selected(self):
		self.show()
		if self.exec_() == QDialog.Accepted:
			return self.branches [ self.comboBox.currentIndex() ]
		else:
			return None

class CommitBrowser(Ui_CommitBrowser, QDialog):
	'''A dialog to display commits for selection.'''
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		Ui_CommitBrowser.__init__(self)
		self.setupUi(self)
		# Make the list widget slighty larger
		self.splitter.setSizes([ 50, 200 ])
		DiffSyntaxHighlighter(self.commitText.document())

class CreateBranchDialog(Ui_CreateBranchDialog, QDialog):
	'''A dialog for creating or updating branches.'''
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		Ui_CreateBranchDialog.__init__(self)
		self.setupUi(self)

class PushDialog(Ui_PushDialog, QDialog):
	'''A dialog for pushing branches.'''
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		Ui_PushDialog.__init__(self)
		self.setupUi(self)
