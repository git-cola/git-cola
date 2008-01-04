import os
import time
from PyQt4.QtCore import Qt
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
from syntax import LogSyntaxHighlighter
import qtutils

class View(Ui_maingui, QMainWindow):
	'''The main ugit interface.'''
	def __init__(self, parent=None):
		QMainWindow.__init__(self, parent)
		Ui_maingui.__init__(self)
		self.setupUi(self)
		self.set_display = self.display_text.setText
		self.set_info = self.displayLabel.setText
		self.action_undo = self.commit_text.undo
		self.action_redo = self.commit_text.redo
		self.action_paste = self.commit_text.paste
		self.action_select_all = self.commit_text.selectAll
		# Qt does not support noun/verbs
		self.commit_button.setText(qtutils.tr('Commit@@verb'))
		self.commit_menu.setTitle(qtutils.tr('Commit@@verb'))
		# Default to creating a new commit(i.e. not an amend commit)
		self.new_commit_radio.setChecked(True)
		self.toolbar_show_log = self.toolbar.addAction(
				qtutils.get_qicon('git.png'),
				'Show/Hide Log Window')
		self.toolbar_show_log.setEnabled(True)
		self.addToolBar(Qt.BottomToolBarArea, self.toolbar)
		# Diff/patch syntax highlighter
		DiffSyntaxHighlighter(self.display_text.document())

	def action_cut(self):
		self.action_copy()
		self.action_delete()
	def action_copy(self):
		cursor = self.commit_text.textCursor()
		selection = cursor.selection().toPlainText()
		qtutils.set_clipboard(selection)
	def action_delete(self):
		self.commit_text.textCursor().removeSelectedText()
	def reset_display(self):
		self.set_display('')
		self.set_info('')
	def copy_display(self):
		cursor = self.display_text.textCursor()
		selection = cursor.selection().toPlainText()
		qtutils.set_clipboard(selection)
	def diff_selection(self):
		cursor = self.display_text.textCursor()
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
		self.setWindowTitle(self.tr('Git Command Output'))
		# Syntax highlight the log window
		LogSyntaxHighlighter(self.output_text.document())
		if output: self.set_output(output)
	def clear(self):
		self.output_text.clear()
	def set_output(self, output):
		self.output_text.setText(output)
	def log(self, output):
		if not output: return
		cursor = self.output_text.textCursor()
		cursor.movePosition(cursor.End)
		text = self.output_text
		cursor.insertText(time.asctime())
		cursor.insertText(os.linesep)
		for line in unicode(output).splitlines():
			cursor.insertText(line)
			cursor.insertText(os.linesep)
		cursor.insertText(os.linesep)
		cursor.movePosition(cursor.End)
		text.setTextCursor(cursor)

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
		self.branch_combo.clear()
	def add(self, branches):
		for branch in branches:
			self.branches.append(branch)
			self.branch_combo.addItem(branch)
	def get_selected(self):
		self.show()
		if self.exec_() == QDialog.Accepted:
			return self.branches[self.branch_combo.currentIndex()]
		else:
			return None

class CommitGUI(Ui_commitgui, QDialog):
	def __init__(self, parent=None, title=None):
		QDialog.__init__(self, parent)
		Ui_commitgui.__init__(self)
		self.setupUi(self)
		if title: self.setWindowTitle(title)
		# Make the list widget slighty larger
		self.splitter.setSizes([ 50, 200 ])
		DiffSyntaxHighlighter(self.commit_text.document(),
				whitespace=False)

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
