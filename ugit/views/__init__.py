import os
import time
from PyQt4 import QtCore
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QMainWindow
from PyQt4.QtGui import QCheckBox
from PyQt4.QtGui import QSplitter

from ugit import qtutils
from ugit.syntax import DiffSyntaxHighlighter
from ugit.syntax import LogSyntaxHighlighter

from main import Ui_main
from push import Ui_push
from branch import Ui_branch
from commit import Ui_commit
from logger import Ui_logger
from search import Ui_search
from options import Ui_options
from createbranch import Ui_createbranch
from merge import Ui_merge

class View(Ui_main, QMainWindow):
	'''The main ugit interface.'''
	def __init__(self, parent=None):
		QMainWindow.__init__(self, parent)
		Ui_main.__init__(self)
		self.setupUi(self)
		self.staged.setAlternatingRowColors(True)
		self.unstaged.setAlternatingRowColors(True)
		self.set_display = self.display_text.setText
		self.set_info = self.displayLabel.setText
		self.action_undo = self.commitmsg.undo
		self.action_redo = self.commitmsg.redo
		self.action_paste = self.commitmsg.paste
		self.action_select_all = self.commitmsg.selectAll

		# Handle automatically setting the horizontal/vertical orientation
		self.splitter.resizeEvent = self.splitter_resize_event

		# Qt does not support noun/verbs
		self.commit_button.setText(qtutils.tr('Commit@@verb'))
		self.commit_menu.setTitle(qtutils.tr('Commit@@verb'))
		# Default to creating a new commit(i.e. not an amend commit)
		self.new_commit_radio.setChecked(True)
		self.toolbar_show_log = self.toolbar.addAction(
				qtutils.get_qicon('git.png'),
				'Show/Hide Log Window')
		self.toolbar_show_log.setEnabled(True)

		# Setup the default dock layout
		self.tabifyDockWidget(self.diff_dock, self.editor_dock)

		dock_area = QtCore.Qt.TopDockWidgetArea
		self.addDockWidget(dock_area, self.status_dock)

		toolbar_area = QtCore.Qt.BottomToolBarArea
		self.addToolBar(toolbar_area, self.toolbar)

		# Diff/patch syntax highlighter
		DiffSyntaxHighlighter(self.display_text.document())

	def splitter_resize_event(self, event):
		width = self.splitter.width()
		height = self.splitter.height()
		if width > height:
			self.splitter.setOrientation(QtCore.Qt.Horizontal)
		else:
			self.splitter.setOrientation(QtCore.Qt.Vertical)
		QSplitter.resizeEvent(self.splitter, event)

	def action_cut(self):
		self.action_copy()
		self.action_delete()
	def action_copy(self):
		cursor = self.commitmsg.textCursor()
		selection = cursor.selection().toPlainText()
		qtutils.set_clipboard(selection)
	def action_delete(self):
		self.commitmsg.textCursor().removeSelectedText()
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
		num_selected_lines = selection.count('\n')
		return offset, selection

class LogView(Ui_logger, QDialog):
	'''A simple dialog to display command logs.'''
	def __init__(self, parent=None, output=None):
		QDialog.__init__(self, parent)
		Ui_logger.__init__(self)
		self.setupUi(self)
		self.setWindowTitle(self.tr('Git Command Log'))
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
		cursor.insertText(time.asctime() + '\n')
		for line in unicode(output).splitlines():
			cursor.insertText(line + '\n')
		cursor.insertText('\n')
		cursor.movePosition(cursor.End)
		text.setTextCursor(cursor)

class BranchView(Ui_branch, QDialog):
	'''A dialog for choosing branches.'''
	def __init__(self, parent=None, branches=None):
		QDialog.__init__(self, parent)
		Ui_branch.__init__(self)
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

class CommitView(Ui_commit, QDialog):
	def __init__(self, parent=None, title=None):
		QDialog.__init__(self, parent)
		Ui_commit.__init__(self)
		self.setupUi(self)
		if title: self.setWindowTitle(title)
		# Make the list widget slighty larger
		self.splitter.setSizes([ 50, 200 ])
		DiffSyntaxHighlighter(self.commit_text.document(),
				whitespace=False)

class CreateBranchView(Ui_createbranch, QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		Ui_createbranch.__init__(self)
		self.setupUi(self)

class PushView(Ui_push, QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		Ui_push.__init__(self)
		self.setupUi(self)

class OptionsView(Ui_options, QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		Ui_options.__init__(self)
		self.setupUi(self)

class SearchView(Ui_search, QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		Ui_search.__init__(self)
		self.setupUi(self)
		self.input.setFocus()
		DiffSyntaxHighlighter(self.commit_text.document(),
				whitespace=False)

class MergeView(Ui_merge, QDialog):
	def __init__(self, parent=None):
		QDialog.__init__(self, parent)
		Ui_search.__init__(self)
		self.setupUi(self)
		self.revision.setFocus()
