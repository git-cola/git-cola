#!/usr/bin/env python
import os
import re
import cmds
import qtutils
from qobserver import QObserver

class GitCreateBranchController (QObserver):
	def __init__ (self, model, view):
		QObserver.__init__ (self, model, view)

		self.model_to_view (model, 'revision', 'revisionLine')
		self.model_to_view (model, 'branch', 'branchNameLine')

		self.add_signals ('textChanged (const QString&)',
				view.revisionLine,
				view.branchNameLine)

		self.add_signals ('itemSelectionChanged()',
				view.branchRootList)

		self.add_signals ('released()',
				view.createBranchButton,
				view.localBranchRadio,
				view.remoteBranchRadio,
				view.tagRadio)

		self.add_callbacks (model, {
				'branchRootList': self.cb_item_changed,
				'createBranchButton': self.cb_create_branch,
				'localBranchRadio':
					lambda(m): self.__display_model (m),
				'remoteBranchRadio':
					lambda(m): self.__display_model (m),
				'tagRadio':
					lambda(m): self.__display_model (m),
				})

		self.__display_model (model)
	
	######################################################################
	# CALLBACKS
	######################################################################

	def cb_create_branch (self, model):
		'''This callback is called when the "Create Branch"
		button is called.'''

		revision = model.get_revision()
		branch = model.get_branch()
		existing_branches = cmds.git_branch()

		if not branch or not revision:
			qtutils.information (self.view,
				'Missing Data',
				('Please provide both a branch name and '
				+ 'revision expression.' ))
			return

		check_branch = False
		if branch in existing_branches:

			if self.view.noUpdateRadio.isChecked():
				qtutils.information (self.view,
					'Warning: Branch Already Exists...',
					('The "' + branch + '"'
					+ ' branch already exists and '
					+ '"Update Existing Branch?" = "No."'))
				return

			# Whether we should prompt the user for lost commits
			commits = cmds.git_rev_list_range (revision, branch)
			check_branch = bool (commits)

		if check_branch:
			lines = []
			for commit in commits:
				lines.append (commit[0][:8] +'\t'+ commit[1])

			lost_commits = '\n\t'.join (lines)

			result = qtutils.question (self.view,
					'Warning: Commits Will Be Lost...',
					('Updating the '
					+ branch + ' branch will lose the '
					+ 'following commits:\n\n\t'
					+ lost_commits + '\n\n'
					+ 'Continue anyways?'))

			if not result: return

		# Settings for git branch
		track = self.view.remoteBranchRadio.isChecked()
		fetch = self.view.fetchCheckBox.isChecked()
		ffwd = self.view.fastForwardUpdateRadio.isChecked()
		reset = self.view.resetRadio.isChecked()

		output = cmds.git_create_branch (branch, revision, track=track)
		qtutils.show_command_output (self.view, output)
		self.view.accept()

	def cb_item_changed (self, model):
		'''This callback is called when the item selection changes
		in the branchRootList.'''

		qlist = self.view.branchRootList
		( row, selected ) = qtutils.get_selected_row (qlist)
		if not selected: return

		sources = self.__get_branch_sources (model)
		rev = sources[row]

		# Update the model with the selection
		model.set_revision (rev)

		# Only set the branch name field if we're
		# branching from a remote branch.
		# Assume that we only want to use
		# the last part of the branch name so that "origin/master"
		# becomes just "master."  Avoid creating branches named HEAD.
		if not self.view.remoteBranchRadio.isChecked():
			return

		base_regex = re.compile ('(.*?/)?([^/]+)$')
		match = base_regex.match (rev)
		if match:
			branch = match.group (2)
			#branch = os.path.basename (rev)
			if branch == 'HEAD': return
			model.set_branch (branch)

	######################################################################
	# PRIVATE HELPER METHODS
	######################################################################

	def __display_model (self, model):
		'''Visualize the current state of the model.'''
		branch_sources = self.__get_branch_sources (model)
		self.view.branchRootList.clear()
		for branch_source in branch_sources:
			self.view.branchRootList.addItem (branch_source)
	
	def __get_branch_sources (self, model):
		'''Get the list of items for populating the branch root list.'''

		if self.view.localBranchRadio.isChecked():
			return model.get_local_branches()

		elif self.view.remoteBranchRadio.isChecked():
			return model.get_remote_branches()

		elif self.view.tagRadio.isChecked():
			return model.get_tags()
