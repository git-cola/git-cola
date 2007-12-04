import os
from PyQt4.QtGui import QListWidgetItem, QIcon, QPixmap

from qobserver import QObserver
import ugitcmds
import ugitutils
from ugitview import GitCommandDialog

class GitController (QObserver):
	'''The controller is a mediator between the view and the model.
	This allows for a clean decoupling between view and model classes.'''

	def __init__ (self, model, view):
		QObserver.__init__ (self, model, view)

		model.add_observer (self)

		# Binds a specific model attribute to a view widget,
		# and vice versa.
		self.model_to_view (model, 'commitmsg', 'commitText')

		# When a model attribute changes, this runs a specific action
		self.add_actions (model, 'staged', self.staged_action)
		self.add_actions (model, 'unstaged', self.unstaged_action)

		# Routes signals for multiple widgets to our callbacks
		# defined below.
		self.add_signals ('textChanged()', view.commitText)
		self.add_signals ('stateChanged(int)', view.untrackedCheckBox)

		self.add_signals ('pressed()',
				view.rescanButton,
				view.stageButton,
				view.commitButton,
				view.pushButton,
				view.signOffButton,)

		self.add_signals ('triggered()',
				view.browseBranch,
				view.browseOtherBranch,
				view.visualizeAll,
				view.visualizeCurrent,
				view.unstage,)

		# These callbacks are called in response to the signals
		# defined above.  One property of the QObserver callback
		# mechanism is that the model is passed in as the first
		# argument to the callback.  This allows for a single
		# controller to manage multiple models, though this
		# isn't used at the moment.

		self.add_callbacks (model, {
				# Push Buttons
				'rescanButton': self.rescan_callback,
				'stageButton': self.stage_callback,
				'signOffButton': self.signoff_callback,
				'commitButton': self.commit_callback,
				# Checkboxes
				'untrackedCheckBox': self.rescan_callback,
				# Menu Actions
				'unstage': self.unstage_callback,
				'browseBranch': self.browse_branch,
				'browseOtherBranch': self.browse_other_branch,
				'visualizeCurrent': self.viz_current_callback,
				'visualizeAll': self.viz_all_callback,
				})

		# chdir to the root of the git tree.  This is critical
		# to being able to properly use the git porcelain.
		cdup = ugitcmds.git_show_cdup()
		if cdup: os.chdir (cdup)

		# Default to creating a new commit (i.e. not an amend commit)
		view.newCommitRadio.setChecked (True)

		self.set_branch_menu_item()
		self.rescan_callback (model)

	def set_branch_menu_item (self):
		'''Sets up items that mention the current branch name.'''

		current_branch = ugitcmds.git_current_branch()
		menu_text = 'Browse ' + current_branch + ' branch'
		self.view.browseBranch.setText (menu_text)

		status_text = 'Current branch: ' + current_branch
		self.view.statusBar().showMessage (status_text)

	def update_listwidget (self, listwidget, modelitems, is_staged):
		'''A helper method to populate a QListWidget with the
		contents of modelitems.'''

		listwidget.clear()
		for modelitem in modelitems:
			item = self.file_to_widget_item (modelitem, is_staged)
			listwidget.addItem( item )

	def unstaged_action (self, model, *args):
		'''This action is called when the model's unstaged list
		changes.  This is a thin wrapper around update_listwidget.'''

		listwidget = self.view.unstagedList
		unstaged = model.get_unstaged()
		self.update_listwidget (listwidget, unstaged, False)

	def staged_action (self, model, *args):
		'''This action is called when the model's staged list
		changes.  This is a thin wrapper around update_listwidget.'''

		listwidget = self.view.stagedList
		staged = model.get_staged()
		self.update_listwidget (listwidget, staged, True)

	def get_selection_from_view (self, list_widget, model_list):
		'''Returns an array of model items that correspond to
		the selected QListWidget indices.'''

		selected = []
		for idx in range (list_widget.count()):
			item = list_widget.item (idx)
			if item.isSelected():
				selected.append (model_list[idx])
		return selected

	def apply_to_list (self, command, model, widget, model_list):
		'''This is a helper method that retrieves the current
		selection list, applies a command to that list, and
		displays a dialog showing the output of that command.'''

		apply_list = self.get_selection_from_view (widget, model_list)
		output = command (apply_list)
		if output:
			dialog = GitCommandDialog (self.view, output=output)
			dialog.show()
			self.rescan_callback (model)

	def stage_callback (self, model, *args):
		'''Use "git add" to add items to the git index.
		This is a thin wrapper around apply_to_list.'''

		widget = self.view.unstagedList
		model_list = model.get_unstaged()
		self.apply_to_list (ugitcmds.git_add,
				model, widget, model_list)
	
	def unstage_callback (self, model, *args):
		'''Use "git reset" to remove items from the git index.
		This is a thin wrapper around apply_to_list.'''

		widget = self.view.stagedList
		model_list = model.get_staged()
		self.apply_to_list (ugitcmds.git_reset,
				model, widget, model_list)
	
	def rescan_callback (self, model, *args):
		'''Populates view widgets with results from "git status."'''

		# This allows us to defer notification until the
		# we finish processing data
		model.set_notify(False)

		# Reset the staged and unstaged model lists
		# NOTE: the model's unstaged list is used to
		# hold both unstaged and untracked files.
		model.staged = []
		model.unstaged = []

		# Read git status items
		( staged_items,
		  unstaged_items,
		  untracked_items ) = ugitcmds.git_status()

		# Gather items to be committed
		for staged in staged_items:
			if staged not in model.get_staged():
				model.add_staged (staged)

		# Gather unindexed items
		for unstaged in unstaged_items:
			if unstaged not in model.get_unstaged():
				model.add_unstaged (unstaged)

		# Gather untracked items
		if self.view.untrackedCheckBox.isChecked():
			for untracked in untracked_items:
				if untracked not in model.get_unstaged():
					model.add_unstaged (untracked)

		# Re-enable notifications and emit changes
		model.set_notify(True)
		model.notify_observers ('staged', 'unstaged')

	def file_to_widget_item (self, filename, is_staged):
		'''Given a filename, return a QListWidgetItem suitable
		for adding to a QListWidget.  "is_staged" controls whether
		to use icons for the staged or unstaged list widget.'''

		if is_staged:
			icon_file = ugitutils.get_staged_icon (filename)
		else:
			icon_file = ugitutils.get_icon (filename)

		icon = QIcon (QPixmap (icon_file))
		item = QListWidgetItem()
		item.setText (filename)
		item.setIcon (icon)
		return item

	def commit_callback (self, model, *args):
		'''Sets up data and calls ugitcmds.commit.'''

		msg = model.get_commitmsg()
		amend = self.view.amendRadio.isChecked()
		commit_all = self.view.commitAllCheckBox.isChecked()

		files = []
		if not commit_all:
			files = self.get_selection_from_view (
					self.view.stagedList,
					model.get_staged() )

		output = ugitcmds.git_commit (msg, amend, commit_all, files)
		if output:
			dialog = GitCommandDialog (self.view, output)
			dialog.show()

		# Reset the commitmsg and rescan changes
		if not output.startswith ('ERROR'):
			model.set_commitmsg ('')
		self.rescan_callback (model)

	def signoff_callback (self, model, *args):
		'''Adds a standard Signed-off by: tag to the end
		of the current commit message.'''

		msg = model.get_commitmsg()
		signoff = 'Signed-off by: %s <%s>' % (
				model.get_name(), model.get_email() )

		if signoff not in msg:
			model.set_commitmsg( '%s\n\n%s' % ( msg, signoff ) )

	def viz_all_callback (self, model):
		'''Visualizes the entire git history using gitk.'''
		os.system ('gitk --all &')
	
	def viz_current_callback (self, model):
		'''Visualizes the current branch's history using gitk.'''
		branch = ugitcmds.git_current_branch()
		os.system ('gitk %s &' % ugitutils.shell_quote (branch))

	def browse_branch (self, model):
		print "MODEL::::::::::", model

	def browse_other_branch (self, model):
		print "MODEL::::::::::", model
