import os
import commands
from PyQt4 import QtGui
from PyQt4.QtCore import QObject
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QClipboard
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QListWidgetItem
from qobserver import QObserver
import cmds
import utils
from gitview import GitCommandDialog
from gitview import GitCommitBrowser

class GitController (QObserver):
	'''The controller is a mediator between the model and view.
	It allows for a clean decoupling between view and model classes.'''

	def __init__ (self, model, view):
		QObserver.__init__ (self, model, view)

		# Register ourselves with the model
		model.add_observer (self)

		# Binds a specific model attribute to a view widget,
		# and vice versa.
		self.model_to_view (model, 'commitmsg', 'commitText')

		# When a model attribute changes, this runs a specific action
		self.add_actions (model, 'staged', self.action_staged)
		self.add_actions (model, 'unstaged', self.action_unstaged)
		self.add_actions (model, 'untracked', self.action_unstaged)

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
				view.rescan,
				view.commitAll,
				view.commitSelected,
				view.getCommitMessage,
				view.stageChanged,
				view.stageUntracked,
				view.stageSelected,
				view.unstageAll,
				view.unstageSelected,
				view.showDiffstat,
				view.browseBranch,
				view.browseOtherBranch,
				view.visualizeAll,
				view.visualizeCurrent,
				view.exportPatches,
				view.cherryPick,)

		self.add_signals ('itemSelectionChanged()',
				view.stagedList,
				view.unstagedList,)

		# Handle double-clicks in the staged/unstaged lists.
		# These are vanilla signal/slots since the qobserver
		# signal routing is already handling these lists' signals.
		QObject.connect ( view.unstagedList,
				SIGNAL ('itemDoubleClicked(QListWidgetItem*)'),
				lambda (x): self.cb_stage_selected (model) )

		QObject.connect ( view.stagedList,
				SIGNAL ('itemDoubleClicked(QListWidgetItem*)'),
				lambda (x): self.cb_unstage_selected (model) )

		# These callbacks are called in response to the signals
		# defined above.  One property of the QObserver callback
		# mechanism is that the model is passed in as the first
		# argument to the callback.  This allows for a single
		# controller to manage multiple models, though this
		# isn't used at the moment.
		self.add_callbacks (model, {
				# Push Buttons
				'rescanButton': self.cb_rescan,
				'stageButton': self.cb_stage_selected,
				'signOffButton': self.cb_signoff,
				'commitButton': self.cb_commit,
				# Checkboxes
				'untrackedCheckBox': self.cb_rescan,
				# List Widgets
				'stagedList': self.cb_diff_staged,
				'unstagedList': self.cb_diff_unstaged,
				# Menu Actions
				'rescan': self.cb_rescan,
				'commitAll': self.cb_commit_all,
				'commitSelected': self.cb_commit_selected,
				'getCommitMessage': self.cb_get_commit_msg,
				'stageChanged': self.cb_stage_changed,
				'stageUntracked': self.cb_stage_untracked,
				'stageSelected': self.cb_stage_selected,
				'unstageAll': self.cb_unstage_all,
				'unstageSelected': self.cb_unstage_selected,
				'showDiffstat': self.cb_show_diffstat,
				'browseBranch': self.cb_browse_current,
				'browseOtherBranch': self.cb_browse_other,
				'visualizeCurrent': self.cb_viz_current,
				'visualizeAll': self.cb_viz_all,
				'exportPatches': self.cb_export_patches,
				'cherryPick': self.cb_cherry_pick,
				})

		# chdir to the root of the git tree.  This is critical
		# to being able to properly use the git porcelain.
		cdup = cmds.git_show_cdup()
		if cdup: os.chdir (cdup)

		# Default to creating a new commit (i.e. not an amend commit)
		view.newCommitRadio.setChecked (True)

		self.__set_branch_ui_items()
		self.cb_rescan (model)

	#####################################################################
	# MODEL ACTIONS
	#####################################################################

	def action_staged (self, model, *args):
		'''This action is called when the model's staged list
		changes.  This is a thin wrapper around update_list_widget.'''
		list_widget = self.view.stagedList
		staged = model.get_staged()
		self.__update_list_widget (list_widget, staged, True)

	def action_unstaged (self, model, *args):
		'''This action is called when the model's unstaged list
		changes.  This is a thin wrapper around update_list_widget.'''
		list_widget = self.view.unstagedList
		unstaged = model.get_unstaged()
		self.__update_list_widget (list_widget, unstaged, False)
		if self.view.untrackedCheckBox.isChecked():
			untracked = model.get_untracked()
			self.__update_list_widget (list_widget, untracked,
					append=True,
					staged=False,
					untracked=True)

	#####################################################################
	# CALLBACKS
	#####################################################################

	def cb_browse_current (self, model):
		print "MODEL::::::::::", model

	def cb_browse_other (self, model):
		print "MODEL::::::::::", model

	def cb_cherry_pick (self, model, *args):
		'''Starts a cherry-picking session.'''
		(revs, summaries) = cmds.git_log (all=True)
		selection, idxs = self.__select_commits (revs, summaries)
		if not selection: return

		output = cmds.git_cherry_pick (selection)
		self.__show_command_output (output, model)

	def cb_commit (self, model, *args):
		'''Sets up data and calls cmds.commit.'''

		msg = model.get_commitmsg()
		amend = self.view.amendRadio.isChecked()
		commit_all = self.view.commitAllCheckBox.isChecked()

		files = []
		if not commit_all:
			files = self.__get_selection_from_view (
					self.view.stagedList,
					model.get_staged() )
		# Perform the commit
		output = cmds.git_commit (msg, amend, commit_all, files)

		# Reset the commitmsg and rescan changes
		if not output.startswith ('ERROR'):
			model.set_commitmsg ('')

		self.__show_command_output (output, model)

	def cb_commit_all (self, model, *args):
		'''Sets the commit-all checkbox and runs cb_commit.'''
		self.view.commitAllCheckBox.setChecked (True)
		self.cb_commit (model, *args)

	def cb_commit_selected (self, model, *args):
		'''Unsets the commit-all checkbox and runs cb_commit.'''
		self.view.commitAllCheckBox.setChecked (False)
		self.cb_commit (model, *args)

	def cb_commit_sha1_selected (self, browser, revs):
		'''This callback is called when a commit browser's
		item is selected.  This callback puts the current
		revision sha1 into the commitText field.
		This callback also puts shows the commit in the
		browser's commit textedit and copies it into
		the global clipboard/selection.'''
		current = browser.commitList.currentRow()
		item = browser.commitList.item (current)
		if not item.isSelected():
			browser.commitText.setText ('')
			browser.revisionLine.setText ('')
			return

		# Get the commit's sha1 and put it in the revision line
		sha1 = revs[current]
		browser.revisionLine.setText (sha1)
		browser.revisionLine.selectAll()

		# Lookup the info for that sha1 and display it
		commit_info = cmds.git_show (sha1, color=True)
		html = utils.ansi_to_html (commit_info)
		browser.commitText.setText (html)

		# Copy the sha1 into the clipboard
		QtGui.qApp.clipboard().setText (sha1, QClipboard.Clipboard)
		QtGui.qApp.clipboard().setText (sha1, QClipboard.Selection)

	def cb_diff_staged (self, model):
		list_widget = self.view.stagedList
		row, selected = self.__get_selected_row (list_widget)

		if not selected:
			self.view.displayText.setText ('')
			return

		filename = model.get_staged()[row]
		diff = cmds.git_diff (filename, staged=True)
		html = utils.ansi_to_html (diff)

		if os.path.exists (filename):
			pre = utils.html_header ('Staged for commit')
		else:
			pre = utils.html_header ('Staged for removal')

		self.view.displayText.setText (pre + html)

	def cb_diff_unstaged (self, model):
		list_widget = self.view.unstagedList
		row, selected = self.__get_selected_row (list_widget)
		if not selected:
			self.view.displayText.setText ('')
			return
		filename = (model.get_unstaged() + model.get_untracked())[row]
		if os.path.isdir (filename):
			pre = utils.html_header ('Untracked directory')
			cmd = 'ls -la %s' % utils.shell_quote (filename)
			html = '<pre>%s</pre>' % commands.getoutput (cmd)
			self.view.displayText.setText ( pre + html )
			return

		if filename in model.get_unstaged():
			diff = cmds.git_diff (filename, staged=False)
			pre = utils.html_header ('Modified, unstaged')
			html = utils.ansi_to_html (diff)
		else:
			# untracked file
			cmd = 'file -b %s' % utils.shell_quote (filename)
			file_type = commands.getoutput (cmd)
			if 'binary' in file_type or 'data' in file_type:
				sq_filename = utils.shell_quote (filename)
				cmd = 'hexdump -C %s' % sq_filename
				contents = commands.getoutput (cmd)
			else:
				file = open (filename, 'r')
				contents = utils.html_encode (file.read())
				file.close()

			header = 'Untracked file: ' + file_type
			pre = utils.html_header (header)
			html = '<pre>%s</pre>' % contents

		self.view.displayText.setText (pre + html)

	def cb_export_patches (self, model, *args):
		'''Launches the commit browser and exports the selected
		patches.'''

		(revs, summaries) = cmds.git_log ()
		selection, idxs = self.__select_commits (revs, summaries)
		if not selection: return

		# now get the selected indices to determine whether
		# a range of consecutive commits were selected
		selected_range = range (idxs[0], idxs[-1] + 1)
		export_range = len (idxs) > 1 and idxs == selected_range

		output = cmds.git_format_patch (selection, export_range)
		self.__show_command_output (output)

	def cb_get_commit_msg (self, model, *args):
		(revs, summaries) = cmds.git_log (oneline=True)
		commit_msg = []
		commit_lines = cmds.git_show (revs[0]).split ('\n')
		for idx, msg in enumerate (commit_lines):
			if idx < 4: continue
			msg = msg.lstrip()
			if msg.startswith ('diff --git'):
				commit_msg.pop()
				break
			commit_msg.append (msg)
		model.set_commitmsg ('\n'.join (commit_msg).rstrip())

	def cb_rescan (self, model, *args):
		'''Populates view widgets with results from "git status."'''

		# This allows us to defer notification until the
		# we finish processing data
		model.set_notify(False)

		# Reset the staged and unstaged model lists
		# NOTE: the model's unstaged list is used to
		# hold both unstaged and untracked files.
		model.staged = []
		model.unstaged = []
		model.untracked = []

		# Read git status items
		( staged_items,
		  unstaged_items,
		  untracked_items ) = cmds.git_status()

		# Gather items to be committed
		for staged in staged_items:
			if staged not in model.get_staged():
				model.add_staged (staged)

		# Gather unindexed items
		for unstaged in unstaged_items:
			if unstaged not in model.get_unstaged():
				model.add_unstaged (unstaged)

		# Gather untracked items
		for untracked in untracked_items:
			if untracked not in model.get_untracked():
				model.add_untracked (untracked)

		# Re-enable notifications and emit changes
		model.set_notify(True)
		model.notify_observers ('staged', 'unstaged')

	def cb_show_diffstat (self, model, *args):
		'''Show the diffstat from the latest commit.'''
		output = utils.ansi_to_html (cmds.git_diff_stat())
		doc = utils.html_document (output)
		self.__show_command_output (doc, rescan=False)

	def cb_signoff (self, model, *args):
		'''Adds a standard Signed-off by: tag to the end
		of the current commit message.'''

		msg = model.get_commitmsg()
		signoff = 'Signed-off by: %s <%s>' % (
				model.get_name(), model.get_email() )

		if signoff not in msg:
			model.set_commitmsg( '%s\n\n%s' % ( msg, signoff ) )

	def cb_stage_changed (self, model, *args):
		'''Stage all changed files for commit.'''
		output = cmds.git_add (model.get_unstaged())
		self.__show_command_output (output, model)

	def cb_stage_selected (self, model, *args):
		'''Use "git add" to add items to the git index.
		This is a thin wrapper around __apply_to_list.'''
		command = cmds.git_add_or_remove
		widget = self.view.unstagedList
		items = model.get_unstaged() + model.get_untracked()
		self.__apply_to_list (command, model, widget, items)

	def cb_stage_untracked (self, model, *args):
		'''Stage all untracked files for commit.'''
		output = cmds.git_add (model.get_untracked())
		self.__show_command_output (output, model)

	def cb_unstage_all (self, model, *args):
		'''Use "git reset" to remove all items from the git index.'''
		output = cmds.git_reset (model.get_staged())
		self.__show_command_output (output, model)

	def cb_unstage_selected (self, model, *args):
		'''Use "git reset" to remove items from the git index.
		This is a thin wrapper around __apply_to_list.'''

		command = cmds.git_reset
		widget = self.view.stagedList
		items = model.get_staged()
		self.__apply_to_list (command, model, widget, items)

	def cb_viz_all (self, model):
		'''Visualizes the entire git history using gitk.'''
		os.system ('gitk --all &')

	def cb_viz_current (self, model):
		'''Visualizes the current branch's history using gitk.'''
		branch = cmds.git_current_branch()
		os.system ('gitk %s &' % utils.shell_quote (branch))

	#####################################################################
	# PRIVATE HELPER METHODS
	#####################################################################

	def __apply_to_list (self, command, model, widget, items):
		'''This is a helper method that retrieves the current
		selection list, applies a command to that list,
		displays a dialog showing the output of that command,
		and calls cb_rescan to pickup changes.'''
		apply_items = self.__get_selection_from_view (widget, items)
		output = command (apply_items)
		self.__show_command_output (output, model)

	def __file_to_widget_item (self, filename, staged, untracked=False):
		'''Given a filename, return a QListWidgetItem suitable
		for adding to a QListWidget.  "staged" controls whether
		to use icons for the staged or unstaged list widget.'''

		if staged:
			icon_file = utils.get_staged_icon (filename)
		elif untracked:
			icon_file = utils.get_untracked_icon()
		else:
			icon_file = utils.get_icon (filename)

		icon = QIcon (QPixmap (icon_file))
		item = QListWidgetItem()
		item.setText (filename)
		item.setIcon (icon)
		return item

	def __get_selected_row (self, list_widget):
		row = list_widget.currentRow()
		item = list_widget.item (row)
		selected = item.isSelected()
		return (row, selected)

	def __get_selection_from_view (self, list_widget, items):
		'''Returns an array of model items that correspond to
		the selected QListWidget indices.'''
		selected = []
		for idx in range (list_widget.count()):
			item = list_widget.item (idx)
			if item.isSelected():
				selected.append (items[idx])
		return selected

	def __select_commits (self, revs, summaries):
		'''Use the GitCommitBrowser to select commits from a list.'''
		if not summaries:
			msg = 'ERROR: No commits exist in this branch.'''
			self.__show_command_output (output=msg)
			return ([],[])

		browser = GitCommitBrowser (self.view)
		QObject.connect ( browser.commitList,
				SIGNAL ('itemSelectionChanged()'),
				lambda: self.cb_commit_sha1_selected(
						browser, revs) )

		for summary in summaries:
			browser.commitList.addItem (summary)

		browser.show()
		result = browser.exec_()
		if result != QDialog.Accepted:
			return ([],[])

		list_widget = browser.commitList
		selection = self.__get_selection_from_view (list_widget, revs)
		if not selection: return ([],[])

		# also return the selected index numbers
		index_nums = range (len (revs))
		idxs = self.__get_selection_from_view (list_widget, index_nums)

		return (selection, idxs)

	def __set_branch_ui_items (self):
		'''Sets up items that mention the current branch name.'''
		current_branch = cmds.git_current_branch()
		menu_text = 'Browse ' + current_branch + ' branch'
		self.view.browseBranch.setText (menu_text)

		status_text = 'Current branch: ' + current_branch
		self.view.statusBar().showMessage (status_text)

	def __show_command_output (self, output, model=None, rescan=True):
		'''Shows output in a GitCommandDialog and optionally
		rescans for changes.'''
		dialog = GitCommandDialog (self.view, output=output)
		dialog.show()
		dialog.exec_()
		if rescan and model: self.cb_rescan (model)

	def __update_list_widget (self, list_widget, items,
			staged, untracked=False, append=False):
		'''A helper method to populate a QListWidget with the
		contents of modelitems.'''
		if not append:
			list_widget.clear()
		for item in items:
			qitem = self.__file_to_widget_item (item,
					staged, untracked)
			list_widget.addItem( qitem )
