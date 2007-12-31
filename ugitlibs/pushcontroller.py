import os
from PyQt4.QtGui import QDialog

import utils
import qtutils
from qobserver import QObserver
from views import PushGUI

def push_branches(model, parent):
	model = model.clone(init=False)
	view = PushGUI(parent)
	controller = PushController(model,view)
	view.show()
	return view.exec_() == QDialog.Accepted

class PushController(QObserver):
	def __init__(self, model, view):
		QObserver.__init__(self,model,view)

		self.model_to_view('remote', 'remoteText')
		self.model_to_view('remotes', 'remoteList')
		self.model_to_view('local_branch', 'localBranchText')
		self.model_to_view('local_branches', 'localBranchList')
		self.model_to_view('remote_branch', 'remoteBranchText')
		self.model_to_view('remote_branches', 'remoteBranchList')

		self.add_actions('remotes', self.remotes)

		self.add_signals('textChanged(const QString&)',
				view.remoteText,
				view.localBranchText,
				view.remoteBranchText)
		self.add_signals('itemClicked(QListWidgetItem *)',
				view.remoteList,
				view.localBranchList,
				view.remoteBranchList)
		self.add_signals('itemSelectionChanged()',
				view.remoteList,
				view.localBranchList,
				view.remoteBranchList)
		self.add_signals('released()',
				view.pushButton,
				view.cancelButton)

		self.add_callbacks(
			remoteList = self.remote_list,
			localBranchList = self.local_branch_list,
			remoteBranchList = self.remote_branch_list,
			pushButton = self.push,
		)

		self.connect(view.cancelButton, 'released()', view.reject)
		model.notify_observers(
				'remotes','local_branches','remote_branches')

	def push(self):
		if not self.model.get_remote():
			errmsg = self.tr('No repository selected.')
			qtutils.show_output(self.view, errmsg)
			return

		if not self.model.get_remote_branch():
			errmsg = self.tr('Please supply a branch name.')
			qtutils.show_output(self.view, errmsg)
			return

		if not self.model.get_local_branch():
			msg = self.tr('Pushing with an empty local branch '
				+ 'will remove the remote branch.\n'
				+ 'Continue?')
			if not qtutils.question(self.view, self.tr('warning'), msg):
				return

		remote = self.model.get_remote()
		local_branch = self.model.get_local_branch()
		remote_branch = self.model.get_remote_branch()
		ffwd = self.view.allowFFOnlyCheckBox.isChecked()
		tags = self.view.tagsCheckBox.isChecked()

		status, output = self.model.push(remote,
					local_branch, remote_branch,
					ffwd=ffwd, tags=tags)

		qtutils.show_output(self.view, output)
		if not status:
			self.view.accept()

	def remotes(self, widget):
		displayed = []
		for remote in self.model.get_remotes():
			url = self.model.remote_url(remote)
			display = '%s\t(%s %s)' \
				% (remote, unicode(self.tr('URL:')), url)
			displayed.append(display)
		qtutils.set_items(widget,displayed)

	def remote_list(self,*rest):
		widget = self.view.remoteList
		remotes = self.model.get_remotes()
		selection = qtutils.get_selected_item(widget,remotes)
		if not selection: return
		self.model.set_remote(selection)
		self.view.remoteText.selectAll()

	def local_branch_list(self,*rest):
		branches = self.model.get_local_branches()
		widget = self.view.localBranchList
		selection = qtutils.get_selected_item(widget,branches)
		if not selection: return

		self.model.set_local_branch(selection)
		self.model.set_remote_branch(selection)

		self.view.localBranchText.selectAll()
		self.view.remoteBranchText.selectAll()

	def remote_branch_list(self,*rest):
		widget = self.view.remoteBranchList
		branches = self.model.get_remote_branches()
		selection = qtutils.get_selected_item(widget,branches)
		if not selection: return

		branch = utils.basename(selection)
		self.model.set_remote_branch(branch)
		self.view.remoteBranchText.selectAll()
