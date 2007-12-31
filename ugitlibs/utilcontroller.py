#!/usr/bin/env python
from PyQt4.QtGui import QDialog
import qtutils
from qobserver import QObserver
from views import BranchGUI
from views import CommitGUI
from views import OptionsGUI

def choose_branch(title, parent, branches):
		dlg = BranchGUI(parent,branches)
		dlg.setWindowTitle(dlg.tr(title))
		return dlg.get_selected()

def select_commits(model, parent, revs, summaries):
	'''Use the CommitBrowser to select commits from a list.'''
	model = model.clone(init=False)
	model.set_revisions(revs)
	model.set_summaries(summaries)
	view = CommitGUI(parent)
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
			return []
		qtutils.set_items(self.view.commitList, summaries)
		self.view.show()
		if self.view.exec_() != QDialog.Accepted:
			return []
		revs = self.model.get_revisions()
		list_widget = self.view.commitList
		return qtutils.get_selection_list(list_widget, revs)

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
		commit_diff = self.model.get_commit_diff(sha1)
		self.view.commitText.setText(commit_diff)

		# Copy the sha1 into the clipboard
		qtutils.set_clipboard(sha1)

def update_options(model, parent):
	view = OptionsGUI(parent)
	ctl = OptionsController(model,view)
	view.show()
	return view.exec_() == QDialog.Accepted

class OptionsController(QObserver):
	def __init__(self,model,view):

		self.original_model = model
		model = model.clone(init=False)

		QObserver.__init__(self,model,view)

		model_to_view = {
			'local.user.email': 'localEmailLine',
			'global.user.email': 'globalEmailLine',
			'local.user.name': 'localNameLine',
			'global.user.name': 'globalNameLine',
		}

		for m,v in model_to_view.iteritems():
			self.model_to_view(m,v)

		self.add_signals('textChanged()',
				view.localNameLine, view.globalNameLine,
				view.localEmailLine,view.globalEmailLine)

		self.refresh_gui()

	def refresh_gui(self):
		self.model.notify_all()
