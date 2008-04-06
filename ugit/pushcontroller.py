import os
from PyQt4.QtGui import QDialog

import utils
import qtutils
from qobserver import QObserver
from views import PushGUI

def push_branches(model, parent):
	model = model.clone()
	view = PushGUI(parent)
	controller = PushController(model,view)
	view.show()
	return view.exec_() == QDialog.Accepted

class PushController(QObserver):
	def __init__(self, model, view):
		QObserver.__init__(self,model,view)

		self.add_observables(
				'remote',
				'remotes',
				'local_branch',
				'local_branches',
				'remote_branch',
				'remote_branches',
				)

		self.add_actions('remotes', self.display_remotes)
		self.add_callbacks(
			remotes = self.update_remotes,
			local_branches = self.update_local_branches,
			remote_branches = self.update_remote_branches,
			push_button = self.push_to_remote_branch,
			)
		self.refresh_view()

	def display_remotes(self, widget):
		displayed = []
		for remote in self.model.get_remotes():
			url = self.model.remote_url(remote)
			display = '%s\t(%s %s)' \
				% (remote, unicode(self.tr('URL:')), url)
			displayed.append(display)
		qtutils.set_items(widget,displayed)

	def push_to_remote_branch(self):
		if not self.model.get_remote():
			errmsg = self.tr('No repository selected.')
			qtutils.show_output(errmsg)
			return

		if not self.model.get_remote_branch():
			errmsg = self.tr('Please supply a branch name.')
			qtutils.show_output(errmsg)
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
		ffwd = self.view.ffwd_only_checkbox.isChecked()
		tags = self.view.tags_checkbox.isChecked()

		status, output = self.model.push_helper(
					remote,
					local_branch,
					remote_branch,
					ffwd=ffwd,
					tags=tags
					)
		qtutils.show_output(output)
		if not status:
			self.view.accept()

	def update_remotes(self,*rest):
		widget = self.view.remotes
		remotes = self.model.get_remotes()
		selection = qtutils.get_selected_item(widget,remotes)
		if not selection: return
		self.model.set_remote(selection)
		self.view.remote.selectAll()

	def update_local_branches(self,*rest):
		branches = self.model.get_local_branches()
		widget = self.view.local_branches
		selection = qtutils.get_selected_item(widget,branches)
		if not selection: return

		self.model.set_local_branch(selection)
		self.model.set_remote_branch(selection)

		self.view.local_branch.selectAll()
		self.view.remote_branch.selectAll()

	def update_remote_branches(self,*rest):
		widget = self.view.remote_branches
		branches = self.model.get_remote_branches()
		selection = qtutils.get_selected_item(widget,branches)
		if not selection: return

		branch = utils.basename(selection)
		if branch == 'HEAD': return
		self.model.set_remote_branch(branch)
		self.view.remote_branch.selectAll()
