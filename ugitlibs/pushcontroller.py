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

		self.model_to_view('remote', 'remote_line')
		self.model_to_view('remotes', 'remote_list')
		self.model_to_view('local_branch', 'local_branch_line')
		self.model_to_view('local_branches', 'local_branch_list')
		self.model_to_view('remote_branch', 'remote_branch_line')
		self.model_to_view('remote_branches', 'remote_branch_list')

		self.add_actions('remotes', self.remotes)

		self.add_signals('textChanged(const QString&)',
				view.remote_line,
				view.local_branch_line,
				view.remote_branch_line)
		self.add_signals('itemClicked(QListWidgetItem *)',
				view.remote_list,
				view.local_branch_list,
				view.remote_branch_list)
		self.add_signals('itemSelectionChanged()',
				view.remote_list,
				view.local_branch_list,
				view.remote_branch_list)
		self.add_signals('released()',
				view.push_button)

		self.add_callbacks(
			remote_list = self.remote_list,
			local_branch_list = self.local_branch_list,
			remote_branch_list = self.remote_branch_list,
			push_button = self.push,
		)

		model.notify_observers(
				'remotes','local_branches','remote_branches')

	def push(self):
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

		status, output = self.model.push(remote,
					local_branch, remote_branch,
					ffwd=ffwd, tags=tags)
		if not status:
			self.view.accept()
		qtutils.show_output(output)

	def remotes(self, widget):
		displayed = []
		for remote in self.model.get_remotes():
			url = self.model.remote_url(remote)
			display = '%s\t(%s %s)' \
				% (remote, unicode(self.tr('URL:')), url)
			displayed.append(display)
		qtutils.set_items(widget,displayed)

	def remote_list(self,*rest):
		widget = self.view.remote_list
		remotes = self.model.get_remotes()
		selection = qtutils.get_selected_item(widget,remotes)
		if not selection: return
		self.model.set_remote(selection)
		self.view.remote_line.selectAll()

	def local_branch_list(self,*rest):
		branches = self.model.get_local_branches()
		widget = self.view.local_branch_list
		selection = qtutils.get_selected_item(widget,branches)
		if not selection: return

		self.model.set_local_branch(selection)
		self.model.set_remote_branch(selection)

		self.view.local_branch_line.selectAll()
		self.view.remote_branch_line.selectAll()

	def remote_branch_list(self,*rest):
		widget = self.view.remote_branch_list
		branches = self.model.get_remote_branches()
		selection = qtutils.get_selected_item(widget,branches)
		if not selection: return

		branch = utils.basename(selection)
		self.model.set_remote_branch(branch)
		self.view.remote_branch_line.selectAll()
