import os
from PyQt4.QtGui import QDialog

from ugit import utils
from ugit import qtutils
from ugit.views import RemoteView
from ugit.qobserver import QObserver

def remote_action(model, parent, action):
	model = model.clone()
	model.create(
		remotename='',
		tags_checkbox=False,
		ffwd_only_checkbox=True,
		)
	if action == "Fetch":
		model.set_tags_checkbox(True)
	view = RemoteView(parent, action)
	controller = RemoteController(model, view, action)
	view.show()
	return view.exec_() == QDialog.Accepted

class RemoteController(QObserver):
	def init(self, model, view, action):
		self.add_observables(
				'remotename',
				'remotes',
				'local_branch',
				'local_branches',
				'remote_branch',
				'remote_branches',
				'tags_checkbox',
				'ffwd_only_checkbox',
				)

		self.action_method = {
			"Fetch": self.fetch_action,
			"Push": self.push_action,
			"Pull": self.pull_action,
		}[action]

		self.add_actions( remotes = self.display_remotes )
		self.add_callbacks(
			action_button = self.action_method,
			remotes = self.update_remotes,
			local_branches = self.update_local_branches,
			remote_branches = self.update_remote_branches,
			)
		self.refresh_view()
		if self.view.select_first_remote():
			self.model.set_remotename(self.model.get_remotes()[0])

	def display_remotes(self, widget):
		displayed = []
		for remotename in self.model.get_remotes():
			url = self.model.remote_url(remotename)
			display = '%s\t(%s %s)' \
				% (remotename, unicode(self.tr('URL:')), url)
			displayed.append(display)
		qtutils.set_items(widget,displayed)

	def update_remotes(self,*rest):
		widget = self.view.remotes
		remotes = self.model.get_remotes()
		selection = qtutils.get_selected_item(widget,remotes)
		if not selection: return
		self.model.set_remotename(selection)
		self.view.remotename.selectAll()

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

	def check_remote(self):
		if not self.model.get_remotename():
			errmsg = self.tr('No repository selected.')
			qtutils.show_output(errmsg)
			return False
		else:
			return True

	def get_common_args(self):
		return (
			(self.model.get_remotename(),),
			{
				"local_branch": self.model.get_local_branch(),
				"remote_branch": self.model.get_remote_branch(),
				"ffwd": self.model.get_ffwd_only_checkbox(),
				"tags": self.model.get_tags_checkbox(),
			},
		)

	def show_results(self, status, output):
		qtutils.show_output(output)
		if not status:
			self.view.accept()
		else:
			qtutils.raise_logger()

	#+-------------------------------------------------------------
	#+ Actions
	def fetch_action(self):
		if not self.check_remote():
			return
		args, kwargs = self.get_common_args()
		self.show_results(*self.model.fetch_helper(*args, **kwargs))
		return
	
	def pull_action(self):
		if not self.check_remote():
			return
		args, kwargs = self.get_common_args()
		self.show_results(*self.model.pull_helper(*args, **kwargs))

	def push_action(self):
		if not self.check_remote():
			return
		args, kwargs = self.get_common_args()
		self.show_results(*self.model.push_helper(*args, **kwargs))
