#!/usr/bin/env python
import os
import cmds
import qtutils
from qobserver import QObserver

class GitCreateBranchController(QObserver):
	def __init__(self, model, view):
		QObserver.__init__(self, model, view)

		self.model_to_view(model, 'revision', 'revisionLine')
		self.model_to_view(model, 'local_branch', 'branchLine')

		self.add_signals('textChanged(const QString&)',
				view.revisionLine,
				view.branchLine)

		self.add_signals('itemSelectionChanged()',
				view.branchRootList)

		self.add_signals('released()',
				view.createBranchButton,
				view.localBranchRadio,
				view.remoteBranchRadio,
				view.tagRadio)

		self.add_callbacks(model, {
				'branchRootList': self.item_changed,
				'createBranchButton': self.create_branch,
				'localBranchRadio': self.__display_model,
				'remoteBranchRadio': self.__display_model,
				'tagRadio': self.__display_model,
				})

		model.init_branch_data()
		self.__display_model(model)
	
	######################################################################
	# Qt callbacks

	def create_branch(self, *rest):
		'''This callback is called when the "Create Branch"
		button is called.'''

		revision = self.model.get_revision()
		branch = self.model.get_local_branch()
		existing_branches = cmds.git_branch()

		if not branch or not revision:
			qtutils.information(self.view,
				'Missing Data',
				('Please provide both a branch name and '
				+ 'revision expression.' ))
			return

		check_branch = False
		if branch in existing_branches:

			if self.view.noUpdateRadio.isChecked():
				qtutils.information(self.view,
					'Warning: Branch Already Exists...',
					('The "' + branch + '"'
					+ ' branch already exists and '
					+ '"Update Existing Branch?" = "No."'))
				return

			# Whether we should prompt the user for lost commits
			commits = cmds.git_rev_list_range(revision, branch)
			check_branch = bool(commits)

		if check_branch:
			lines = []
			for commit in commits:
				lines.append(commit[0][:8] +'\t'+ commit[1])

			lost_commits = '\n\t'.join(lines)

			result = qtutils.question(self.view,
					'Warning: Commits Will Be Lost...',
					('Updating the '
					+ branch + ' branch will lose the '
					+ 'following commits:\n\n\t'
					+ lost_commits + '\n\n'
					+ 'Continue anyways?'))

			if not result: return

		# TODO: Settings for git branch
		track = self.view.remoteBranchRadio.isChecked()
		fetch = self.view.fetchCheckBox.isChecked()
		ffwd = self.view.fastForwardUpdateRadio.isChecked()
		reset = self.view.resetRadio.isChecked()

		output = cmds.git_create_branch(branch, revision, track=track)
		qtutils.show_command(self.view, output)
		self.view.accept()

	def item_changed(self, *rest):
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
		# Assume that we only want to use
		# the last part of the branch name so that "origin/master"
		# becomes just "master."  Avoid creating branches named HEAD.
		if not self.view.remoteBranchRadio.isChecked():
			return

		branch = utils.basename(rev)
		#branch = os.path.basename(rev)
		if branch == 'HEAD': return
		self.model.set_local_branch(branch)

	######################################################################

	def __display_model(self, *rest):
		'''Visualize the current state of the model.'''
		branch_sources = self.__get_branch_sources()
		self.view.branchRootList.clear()
		for branch_source in branch_sources:
			self.view.branchRootList.addItem(branch_source)
	
	def __get_branch_sources(self):
		'''Get the list of items for populating the branch root list.'''

		if self.view.localBranchRadio.isChecked():
			return self.model.get_local_branches()

		elif self.view.remoteBranchRadio.isChecked():
			return self.model.get_remote_branches()

		elif self.view.tagRadio.isChecked():
			return self.model.get_tags()
