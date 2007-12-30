#!/usr/bin/env python
import os
from PyQt4.QtGui import QDialog

import utils
import qtutils
from qobserver import QObserver
from views import CreateBranchDialog

def create_new_branch(parent,model):
	model = model.clone(init=False)
	view = CreateBranchDialog(parent)
	ctl = CreateBranchController(model,view)
	view.show()
	return view.exec_() == QDialog.Accepted

class CreateBranchController(QObserver):
	def __init__(self, model, view):
		QObserver.__init__(self, model, view)

		self.model_to_view('revision', 'revisionLine')
		self.model_to_view('local_branch', 'branchLine')
		self.add_signals('textChanged(const QString&)',
				view.revisionLine, view.branchLine)

		self.add_signals('itemSelectionChanged()', view.branchRootList)
		self.add_signals('released()',
				view.createBranchButton,
				view.localBranchRadio, view.remoteBranchRadio,
				view.tagRadio)

		self.add_callbacks({
				'branchRootList': self.item_changed,
				'createBranchButton': self.create_branch,
				'localBranchRadio': self.__display_model,
				'remoteBranchRadio': self.__display_model,
				'tagRadio': self.__display_model,
				})

		self.__display_model()

	######################################################################
	# Qt callbacks

	def create_branch(self):
		'''This callback is called when the "Create Branch"
		button is called.'''

		revision = self.model.get_revision()
		branch = self.model.get_local_branch()
		existing_branches = self.model.get_local_branches()

		if not branch or not revision:
			qtutils.information(self.view,
				self.tr('Missing Data'),
				self.tr('Please provide both a branch'
					+ ' name and revision expression.' ))
			return

		check_branch = False
		if branch in existing_branches:

			if self.view.noUpdateRadio.isChecked():
				msg = self.tr("Branch '%s' already exists.")
				msg = unicode(msg) % branch
				qtutils.information(self.view,
						self.tr('warning'), msg)
				return

			# Whether we should prompt the user for lost commits
			commits = self.model.rev_list_range(revision, branch)
			check_branch = bool(commits)

		if check_branch:
			msg = self.tr("Resetting '%s' to '%s' will lose the following commits:")
			lines = [ unicode(msg) % (branch, revision) ]

			for idx, commit in enumerate(commits):
				subject = commit[1][0:min(len(commit[1]),16)]
				if len(subject) < len(commit[1]):
					subject += '...'
				lines.append('\t' + commit[0][:8]
						+'\t' + subject)
				if idx >= 5:
					skip = len(commits) - 5
					lines.append('\t(%d skipped)' % skip)
					break

			lines.extend([
				unicode(self.tr("Recovering lost commits may not be easy.")),
				unicode(self.tr("Reset '%s'?")) % branch
				])

			result = qtutils.question(self.view,
					self.tr('warning'), '\n'.join(lines))

			if not result: return

		# TODO: Settings for git branch
		track = self.view.remoteBranchRadio.isChecked()
		fetch = self.view.fetchCheckBox.isChecked()
		ffwd = self.view.fastForwardUpdateRadio.isChecked()
		reset = self.view.resetRadio.isChecked()

		output = self.model.create_branch(branch, revision, track=track)
		qtutils.show_output(self.view, output)
		self.view.accept()

	def item_changed(self):
		'''This callback is called when the item selection changes
		in the branchRootList.'''

		qlist = self.view.branchRootList
		( row, selected ) = qtutils.get_selected_row(qlist)
		if not selected: return

		sources = self.__get_branch_sources()
		rev = sources[row]

		# Update the model with the selection
		self.model.set_revision(rev)

		# Only set the branch name field if we're
		# branching from a remote branch.
		if not self.view.remoteBranchRadio.isChecked():
			return

		branch = utils.basename(rev)
		if branch == 'HEAD': return

		self.model.set_local_branch(branch)

	######################################################################

	def __display_model(self):
		branches = self.__get_branch_sources()
		qtutils.set_items(self.view.branchRootList, branches)

	def __get_branch_sources(self):
		'''Get the list of items for populating the branch root list.'''

		if self.view.localBranchRadio.isChecked():
			return self.model.get_local_branches()

		elif self.view.remoteBranchRadio.isChecked():
			return self.model.get_remote_branches()

		elif self.view.tagRadio.isChecked():
			return self.model.get_tags()
