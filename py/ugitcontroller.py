import os
from qobserver import QObserver
import ugitcmds
import ugitutils
from ugitview import GitCommandDialog
from PyQt4.QtGui import QListWidgetItem, QIcon, QPixmap

class GitController (QObserver):

	def __init__ (self, model, view):
		QObserver.__init__ (self, model, view)
		model.add_observer (self)

		self.add_signals ('textChanged()', view.commitText)
		self.add_signals ('stateChanged(int)', view.untrackedCheckBox)

		self.model_to_view (model, 'commitmsg', 'commitText')

		self.add_signals ('pressed()',
				view.rescanButton,
				view.stageButton,
				view.pushButton,
				view.signOffButton,)

		self.add_signals ('triggered()',
				view.browseBranch,
				view.browseOtherBranch,
				view.unstage,)

		self.add_callbacks (model, {
				# Push Buttons
				'rescanButton': self.rescan_callback,
				'stageButton': self.stage_callback,
				'signOffButton': self.signoff_callback,
				# Menu Actions
				'unstage': self.unstage_callback,
				'browseOtherBranch': self.browse_other_branch,
				'browseBranch': self.browse_branch,
				# Checkboxes
				'untrackedCheckBox': self.rescan_callback,
				})

		self.add_actions (model, 'staged', self.staged_action)
		self.add_actions (model, 'unstaged', self.unstaged_action)

		# chdir to the root of the git tree
		cdup = ugitcmds.git_show_cdup()
		if cdup: os.chdir (cdup)

		view.newCommitRadio.setChecked (True)
		self.set_branch_menu_item()
		self.rescan_callback (model)

	def set_branch_menu_item (self):
		current_branch = ugitcmds.git_current_branch()
		menu_text = 'Browse ' + current_branch + ' branch'
		self.view.browseBranch.setText (menu_text)
	
	def get_selection_from_view (self, list_widget, model_list):
		selected = []
		for idx in range (list_widget.count()):
			item = list_widget.item (idx)
			if item.isSelected():
				selected.append (model_list[idx])
		return selected

	def apply_to_list (self, command, model, widget, model_list):
		apply_list = self.get_selection_from_view (widget, model_list)
		output = command (apply_list)
		if output:
			dialog = GitCommandDialog (self.view, output=output)
			dialog.show()
			self.rescan_callback (model)
	
	def unstage_callback (self, model, *args):
		widget = self.view.stagedList
		model_list = model.get_staged()
		self.apply_to_list (ugitcmds.git_reset,
				model, widget, model_list)
	
	def stage_callback (self, model, *args):
		widget = self.view.unstagedList
		model_list = model.get_unstaged()
		self.apply_to_list (ugitcmds.git_add,
				model, widget, model_list)

	def rescan_callback (self, model, *args):

		# This allows us to defer notification until the
		# we finish processing data
		model.set_notify(False)

		# Reset the staged and unstaged model lists
		model.staged = []
		model.unstaged = []

		# Read git status
		status = ugitcmds.git_status()

		# Gather items to be committed
		staged_items = ugitcmds.git_modified (status, staged=True)
		for staged in staged_items:
			if staged not in model.get_staged():
				model.add_staged (staged)

		# Gather unindexed items
		unstaged_items = ugitcmds.git_modified (status, staged=False)
		for unstaged in unstaged_items:
			if unstaged not in model.get_unstaged():
				model.add_unstaged (unstaged)

		# Gather untracked items
		if self.view.untrackedCheckBox.checkState():
			untracked_items = ugitcmds.git_untracked (status)
			for untracked in untracked_items:
				if untracked not in model.get_unstaged():
					model.add_unstaged (untracked)

		# Re-enable notifications and emit changes
		model.set_notify(True)
		model.notify_observers ('staged', 'unstaged')

	def file_to_widget_item (self, filename):
		icon = QIcon (QPixmap (ugitutils.get_icon (filename)))
		item = QListWidgetItem ()
		item.setText (filename)
		item.setIcon (icon)
		return item

	def update_listwidget (self, modelitems, listwidget):
		listwidget.clear()
		for modelitem in modelitems:
			item = self.file_to_widget_item (modelitem)
			listwidget.addItem( item )

	def unstaged_action (self, model, *args):
		listwidget = self.view.unstagedList
		self.update_listwidget (model.get_unstaged(), listwidget)

	def staged_action (self, model, *args):
		listwidget = self.view.stagedList
		self.update_listwidget (model.get_staged(), listwidget)

	def signoff_callback (self, model, *args):
		msg = model.get_commitmsg()
		signoff = 'Signed-off by: %s <%s>' % (
				model.get_name(), model.get_email() )

		if signoff not in msg:
			model.set_commitmsg( '%s\n\n%s' % ( msg, signoff ) )

	def browse_branch (self, model):
		print "MODEL::::::::::"
		print model

	def browse_other_branch (self, model):
		print "MODEL::::::::::"
		print model
