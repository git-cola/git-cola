import os

from qobserver import QObserver
import cmds
import utils
import qtutils

class GitPushController(QObserver):
	def __init__(self, model, view):
		QObserver.__init__(self,model,view)

		self.model_to_view(model, 'remote',    'remoteText')
		self.model_to_view(model, 'local_branch', 'localBranchText')
		self.model_to_view(model, 'remote_branch', 'remoteBranchText')

		self.add_actions(model,'remotes',        self.remotes)
		self.add_actions(model,'remote_branches', self.remote_branches)
		self.add_actions(model,'local_branches', self.local_branches)

		self.add_signals('released()',
				view.pushButton,
				view.cancelButton)

		self.add_signals('itemSelectionChanged()',
				view.remoteList,
				view.localBranchList,
				view.remoteBranchList)

		self.add_signals('textChanged (const QString&)',
				view.remoteText,
				view.localBranchText,
				view.remoteBranchText)

		self.add_callbacks(model, {
			'remoteList': self.remote_list,
			'localBranchList': self.local_branch_list,
			'remoteBranchList': self.remote_branch_list,
			'cancelButton': lambda(m): self.view.reject(),
			'pushButton': self.push,
		})

		model.init_branch_data()

	def push(self, *rest):
		if not self.model.get_remote():
			errmsg = 'ERROR: Please specify a remote.'
			qtutils.show_command(self.view, errmsg)
			return

		if not self.model.get_remote_branch():
			errmsg = 'ERROR: Please specify a remote branch.'
			qtutils.show_command(self.view, errmsg)
			return

		if not self.model.get_local_branch():
			msg = ('Pushing with an empty local branch '
				+ 'will remove the remote branch.\n'
				+ 'Continue?')
			if not qtutils.question(self.view,
				'WARNING', msg):
				return

		remote = self.model.get_remote()
		local_branch = self.model.get_local_branch()
		remote_branch = self.model.get_remote_branch()
		force = self.view.allowNonFFCheckBox.isChecked()

		status, output = cmds.git_push(remote,
					local_branch, remote_branch,
					force=force)

		qtutils.show_command(self.view, output)
		if not status:
			self.view.accept()

	def remote_list(self, *rest):
		widget = self.view.remoteList
		remotes = self.model.get_remotes()
		selection = qtutils.get_selection_from_list(widget,remotes)
		if not selection: return

		self.model.set_remote(selection[0])
		self.view.remoteText.selectAll()
		self.model.notify_observers('remote_branches')

	def local_branch_list(self, *rest):
		branches = self.model.get_local_branches()
		widget = self.view.localBranchList
		selection = qtutils.get_selection_from_list(widget,branches)
		if not selection: return

		self.model.set_local_branch(selection[0])
		self.model.set_remote_branch(selection[0])

		self.view.localBranchText.selectAll()
		self.view.remoteBranchText.selectAll()

	def remote_branch_list(self, *rest):
		widget = self.view.remoteBranchList
		branches = self.__current_remote_branches()
		selection = qtutils.get_selection_from_list(widget,branches)
		if not selection: return

		branch = utils.basename(selection[0])
		self.model.set_remote_branch(branch)
		self.view.remoteBranchText.selectAll()


	def remotes(self,*rest):
		widget = self.view.remoteList
		remotes = self.model.get_remotes()
		qtutils.set_items(widget,remotes)

	def remote_branches(self,*rest):
		widget = self.view.remoteBranchList
		branches = self.__current_remote_branches()
		qtutils.set_items(widget,branches)

	def local_branches(self,*rest):
		widget = self.view.localBranchList
		branches = self.model.get_local_branches()
		qtutils.set_items(widget,branches)

	def __current_remote_branches(self):
		branches = []
		remote = self.model.get_remote()
		if not remote: return branches
		for branch in self.model.get_remote_branches():
			if (not branch.endswith('HEAD')
					and branch.startswith(remote)):
				branches.append(branch)
		return branches
