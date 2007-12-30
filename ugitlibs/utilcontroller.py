#!/usr/bin/env python
from PyQt4.QtGui import QDialog
import qtutils
from qobserver import QObserver
from views import BranchDialog
from views import CommitBrowser

def choose_branch(title, parent, branches):
		dlg = BranchDialog(parent,branches)
		dlg.setWindowTitle(dlg.tr(title))
		return dlg.get_selected()

def select_commits(model, parent, revs, summaries):
	'''Use the CommitBrowser to select commits from a list.'''
	model = model.clone(init=False)
	model.set_revisions(revs)
	model.set_summaries(summaries)
	view = CommitBrowser(parent)
	ctl = SelectCommitsController(model, view)
	return ctl.select_commits()

class SelectCommitsController(QObserver):
	def __init__(self, model, view):
		QObserver.__init__(self, model, view)
		self.connect(view.commitList, 'itemSelectionChanged()',
				self.commit_sha1_selected )

	def select_commits(self):
		summaries = self.model.get_summaries()
		if not summaries:
			msg = self.tr('No commits exist in this branch.')
			self.show_output(msg)
			return([],[])

		qtutils.set_items(self.view.commitList, summaries)

		self.view.show()
		result = self.view.exec_()
		if result != QDialog.Accepted: return([],[])

		revs = self.model.get_revisions()
		list_widget = self.view.commitList
		selection = qtutils.get_selection_list(list_widget, revs)
		if not selection: return([],[])

		# also return the selected index numbers
		index_nums = range(len(revs))
		idxs = qtutils.get_selection_list(list_widget, index_nums)

		return(selection, idxs)

	def commit_sha1_selected(self):
		row, selected = qtutils.get_selected_row(self.view.commitList)
		if not selected:
			self.view.commitText.setText('')
			self.view.revisionLine.setText('')
			return

		# Get the sha1 and put it in the revision line
		sha1 = self.model.get_revision_sha1(row)
		self.view.revisionLine.setText(sha1)
		self.view.revisionLine.selectAll()

		# Lookup the sha1's commit
		commit_diff = self.model.diff(commit=sha1,cached=False)
		self.view.commitText.setText(commit_diff)

		# Copy the sha1 into the clipboard
		qtutils.set_clipboard(sha1)
