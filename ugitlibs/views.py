import os
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QMainWindow
from maingui import Ui_maingui
from outputgui import Ui_outputgui
from optionsgui import Ui_optionsgui
from branchgui import Ui_branchgui
from commitgui import Ui_commitgui
from createbranchgui import Ui_createbranchgui
from pushgui import Ui_pushgui
from syntax import DiffSyntaxHighlighter
import qtutils

class View(Ui_maingui, QMainWindow):
	'''The main ugit interface.'''
	def __init__(self, parent=None):
		QMainWindow.__init__(self, parent)
		Ui_maingui.__init__(self)
		self.setupUi(self)
		DiffSyntaxHighlighter(self.displayText.document())
		self.set_display = self.displayText.setText
		self.set_info = self.displayLabel.setText
		self.action_undo = self.commitText.undo
		self.action_redo = self.commitText.redo
		self.action_paste = self.commitText.paste
		self.action_select_all = self.commitText.selectAll
		# Qt does not support noun/verbs
		self.commitButton.setText(qtutils.tr('Commit@@verb'))
		self.menuCommit.setTitle(qtutils.tr('Commit@@verb'))
		# Default to creating a new commit(i.e. not an amend commit)
		self.newCommitRadio.setChecked(True)

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

class OutputGUI(Ui_outputgui, QDialog):
	'''A simple dialog to display command output.'''
	def __init__(self, parent=None, output=None):
		QDialog.__init__(self, parent)
		Ui_outputgui.__init__(self)
		self.setupUi(self)
		if output: self.set_output(output)
	def set_output(self, output):
		self.outputText.setText(output)

class BranchGUI(Ui_branchgui, QDialog):
	'''A dialog for choosing branches.'''
	def __init__(self, parent=None, branches=None):
		QDialog.__init__(self, parent)
		Ui_branchgui.__init__(self)
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

class CommitGUI(Ui_commitgui, QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		Ui_commitgui.__init__(self)
		self.setupUi(self)
		# Make the list widget slighty larger
		self.splitter.setSizes([ 50, 200 ])
		DiffSyntaxHighlighter(self.commitText.document())

class CreateBranchGUI(Ui_createbranchgui, QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		Ui_createbranchgui.__init__(self)
		self.setupUi(self)

class PushGUI(Ui_pushgui, QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		Ui_pushgui.__init__(self)
		self.setupUi(self)

class OptionsGUI(Ui_optionsgui, QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		Ui_optionsgui.__init__(self)
		self.setupUi(self)
