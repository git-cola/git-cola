import os
import commands
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QMenu
from qobserver import QObserver
import cmds
import utils
import qtutils
from models import GitRepoBrowserModel
from models import GitCreateBranchModel
from views import GitCommitBrowser
from views import GitBranchDialog
from views import GitCreateBranchDialog
from repobrowsercontroller import GitRepoBrowserController
from createbranchcontroller import GitCreateBranchController

class GitController (QObserver):
	'''The controller is a mediator between the model and view.
	It allows for a clean decoupling between view and model classes.'''

	def __init__ (self, model, view):
		QObserver.__init__ (self, model, view)

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

		self.add_signals ('released()',
				view.stageButton,
				view.commitButton,
				view.pushButton,
				view.signOffButton,)

		self.add_signals ('triggered()',
				view.rescan,
				view.createBranch,
				view.checkoutBranch,
				view.rebaseBranch,
				view.deleteBranch,
				view.commitAll,
				view.commitSelected,
				view.setCommitMessage,
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

		# App cleanup
		self.connect ( qtutils.qapp(),
				'lastWindowClosed()',
				self.cb_last_window_closed )

		# Handle double-clicks in the staged/unstaged lists.
		# These are vanilla signal/slots since the qobserver
		# signal routing is already handling these lists' signals.
		self.connect ( view.unstagedList,
				'itemDoubleClicked(QListWidgetItem*)',
				lambda (x): self.cb_stage_selected (model) )

		self.connect ( view.stagedList,
				'itemDoubleClicked(QListWidgetItem*)',
				lambda (x): self.cb_unstage_selected (model) )

		# These callbacks are called in response to the signals
		# defined above.  One property of the QObserver callback
		# mechanism is that the model is passed in as the first
		# argument to the callback.  This allows for a single
		# controller to manage multiple models, though this
		# isn't used at the moment.
		self.add_callbacks (model, {
				# Push Buttons
				'stageButton': self.cb_stage_selected,
				'signOffButton': lambda(m): m.add_signoff(),
				'commitButton': self.cb_commit,
				# Checkboxes
				'untrackedCheckBox': self.cb_rescan,
				# List Widgets
				'stagedList': self.cb_diff_staged,
				'unstagedList': self.cb_diff_unstaged,
				# Menu Actions
				'rescan': self.cb_rescan,
				'createBranch': self.cb_branch_create,
				'deleteBranch': self.cb_branch_delete,
				'checkoutBranch': self.cb_checkout_branch,
				'rebaseBranch': self.cb_rebase,
				'commitAll': self.cb_commit_all,
				'commitSelected': self.cb_commit_selected,
				'setCommitMessage':
					lambda(m): m.set_latest_commitmsg(),
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

		# The diff-display context menu
		self.__menu = None
		view.displayText.controller = self
		view.displayText.contextMenuEvent = self.__menu_event

		# Default to creating a new commit (i.e. not an amend commit)
		view.newCommitRadio.setChecked (True)

		# Initialize the GUI
		self.cb_rescan (model)

		# Setup the inotify server
		self.__start_inotify_thread (model)

	#####################################################################
	# MODEL ACTIONS
	#####################################################################

	def action_staged (self, model):
		'''This action is called when the model's staged list
		changes.  This is a thin wrapper around update_list_widget.'''
		list_widget = self.view.stagedList
		staged = model.get_staged()
		self.__update_list_widget (list_widget, staged, True)

	def action_unstaged (self, model):
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

	def cb_branch_create (self, ugit_model):
		model = GitCreateBranchModel()
		view = GitCreateBranchDialog (self.view)
		controller = GitCreateBranchController (model, view)
		view.show()
		result = view.exec_()
		if result == QDialog.Accepted:
			self.cb_rescan (ugit_model)

	def cb_branch_delete (self, model):
		dlg = GitBranchDialog(self.view, branches=cmds.git_branch())
		branch = dlg.getSelectedBranch()
		if not branch: return
		qtutils.show_command (self.view,
				cmds.git_branch(name=branch, delete=True))


	def cb_browse_current (self, model):
		self.__browse_branch (cmds.git_current_branch())

	def cb_browse_other (self, model):
		# Prompt for a branch to browse
		branches = (cmds.git_branch (remote=False)
				+ cmds.git_branch (remote=True))

		dialog = GitBranchDialog (self.view, branches=branches)

		# Launch the repobrowser
		self.__browse_branch (dialog.getSelectedBranch())

	def cb_checkout_branch (self, model):
		dlg = GitBranchDialog (self.view, cmds.git_branch())
		branch = dlg.getSelectedBranch()
		if not branch: return
		qtutils.show_command (self.view, cmds.git_checkout(branch))
		self.cb_rescan (model)

	def cb_cherry_pick (self, model):
		'''Starts a cherry-picking session.'''
		(revs, summaries) = cmds.git_log (all=True)
		selection, idxs = self.__select_commits (revs, summaries)
		if not selection: return

		output = cmds.git_cherry_pick (selection)
		self.__show_command (output, model)

	def cb_commit (self, model):
		'''Sets up data and calls cmds.commit.'''

		msg = model.get_commitmsg()
		if not msg:
			error_msg = 'ERROR: No commit message was provided.'
			self.__show_command (error_msg)
			return

		amend = self.view.amendRadio.isChecked()
		commit_all = self.view.commitAllCheckBox.isChecked()

		files = []
		if commit_all:
			files = model.get_staged()
		else:
			wlist = self.view.stagedList
			mlist = model.get_staged()
			files = qtutils.get_selection_from_list (wlist, mlist)
		# Perform the commit
		output = cmds.git_commit (msg, amend, files)

		# Reset commitmsg and rescan
		model.set_commitmsg ('')
		self.__show_command (output, model)

	def cb_commit_all (self, model):
		'''Sets the commit-all checkbox and runs cb_commit.'''
		self.view.commitAllCheckBox.setChecked (True)
		self.cb_commit (model)

	def cb_commit_selected (self, model):
		'''Unsets the commit-all checkbox and runs cb_commit.'''
		self.view.commitAllCheckBox.setChecked (False)
		self.cb_commit (model)

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
		commit_diff = cmds.git_show (sha1)
		browser.commitText.setText (commit_diff)

		# Copy the sha1 into the clipboard
		qtutils.set_clipboard (sha1)

	def cb_copy (self):
		self.view.displayText.copy()

	def cb_diff_staged (self, model):
		list_widget = self.view.stagedList
		row, selected = qtutils.get_selected_row (list_widget)

		if not selected:
			self.view.displayText.setText ('')
			return

		filename = model.get_staged()[row]
		diff = cmds.git_diff (filename, staged=True)

		if os.path.exists (filename):
			pre = utils.header ('Staged for commit')
		else:
			pre = utils.header ('Staged for removal')

		self.view.displayText.setText (pre + diff)

	def cb_diff_unstaged (self, model):
		list_widget = self.view.unstagedList
		row, selected = qtutils.get_selected_row (list_widget)
		if not selected:
			self.view.displayText.setText ('')
			return
		filename = (model.get_unstaged() + model.get_untracked())[row]
		if os.path.isdir (filename):
			pre = utils.header ('Untracked directory')
			cmd = 'ls -la %s' % utils.shell_quote (filename)
			output = commands.getoutput (cmd)
			self.view.displayText.setText ( pre + output )
			return

		if filename in model.get_unstaged():
			diff = cmds.git_diff (filename, staged=False)
			msg = utils.header ('Modified, unstaged') + diff
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
				contents = file.read()
				file.close()

			msg = (utils.header ('Untracked file: ' + file_type)
				+ contents)

		self.view.displayText.setText (msg)

	def cb_export_patches (self, model):
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
		self.__show_command (output)

	def cb_get_commit_msg (self, model):
		model.retrieve_latest_commitmsg()

	def cb_last_window_closed (self):
		'''Cleanup the inotify thread if it exists.'''
		if not self.inotify_thread: return
		if not self.inotify_thread.isRunning(): return
		self.inotify_thread.abort = True
		self.inotify_thread.quit()
		self.inotify_thread.wait()

	def cb_rebase (self, model):
		dlg = GitBranchDialog(self.view, cmds.git_branch())
		dlg.setWindowTitle ("Select the current branch's new root")
		branch = dlg.getSelectedBranch()
		if not branch: return
		qtutils.show_command (self.view, cmds.git_rebase (branch))

	def cb_rescan (self, model, *args):
		'''Populates view widgets with results from "git status."'''

		# Scan for branch changes
		self.__set_branch_ui_items()

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

		squash_msg = os.path.join (os.getcwd(), '.git', 'SQUASH_MSG')
		if not os.path.exists (squash_msg): return

		msg = model.get_commitmsg()

		if msg:
			result = qtutils.question (self.view,
					'Import Commit Message?',
					('A commit message from a '
					+ 'merge-in-progress was found.\n'
					+ 'Do you want to import it?'))
			if not result: return

		file = open (squash_msg)
		msg = file.read()
		file.close()

		# Set the new commit message
		model.set_commitmsg (msg)

	def cb_show_diffstat (self, model):
		'''Show the diffstat from the latest commit.'''
		self.__show_command (cmds.git_diff_stat(), rescan=False)

	def cb_stage_changed (self, model):
		'''Stage all changed files for commit.'''
		output = cmds.git_add (model.get_unstaged())
		self.__show_command (output, model)

	def cb_stage_hunk (self):
		print "STAGING HUNK"

	def cb_stage_selected (self, model):
		'''Use "git add" to add items to the git index.
		This is a thin wrapper around __apply_to_list.'''
		command = cmds.git_add_or_remove
		widget = self.view.unstagedList
		items = model.get_unstaged() + model.get_untracked()
		self.__apply_to_list (command, model, widget, items)

	def cb_stage_untracked (self, model):
		'''Stage all untracked files for commit.'''
		output = cmds.git_add (model.get_untracked())
		self.__show_command (output, model)

	def cb_unstage_all (self, model):
		'''Use "git reset" to remove all items from the git index.'''
		output = cmds.git_reset (model.get_staged())
		self.__show_command (output, model)

	def cb_unstage_selected (self, model):
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
		apply_items = qtutils.get_selection_from_list (widget, items)
		output = command (apply_items)
		self.__show_command (output, model)

	def __browse_branch (self, branch):
		if not branch: return
		model = GitRepoBrowserModel (branch)
		view = GitCommitBrowser()
		controller = GitRepoBrowserController(model, view)
		view.show()
		view.exec_()

	def __menu_about_to_show (self):
		self.__stage_hunk_action.setEnabled (True)

	def __menu_event (self, event):
		self.__menu_setup()
		textedit = self.view.displayText
		self.__menu.exec_ (textedit.mapToGlobal (event.pos()))

	def __menu_setup (self):
		if self.__menu: return

		menu = QMenu (self.view)
		stage = menu.addAction ('Stage Hunk', self.cb_stage_hunk)
		copy = menu.addAction ('Copy', self.cb_copy)

		self.connect (menu, 'aboutToShow()', self.__menu_about_to_show)

		self.__stage_hunk_action = stage
		self.__copy_action = copy
		self.__menu = menu


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

		return qtutils.create_listwidget_item (filename, icon_file)

	def __select_commits (self, revs, summaries):
		'''Use the GitCommitBrowser to select commits from a list.'''
		if not summaries:
			msg = 'ERROR: No commits exist in this branch.'''
			self.__show_command (output=msg)
			return ([],[])

		browser = GitCommitBrowser (self.view)
		self.connect ( browser.commitList,
				'itemSelectionChanged()',
				lambda: self.cb_commit_sha1_selected(
						browser, revs) )

		for summary in summaries:
			browser.commitList.addItem (summary)

		browser.show()
		result = browser.exec_()
		if result != QDialog.Accepted:
			return ([],[])

		list_widget = browser.commitList
		selection = qtutils.get_selection_from_list (list_widget, revs)
		if not selection: return ([],[])

		# also return the selected index numbers
		index_nums = range (len (revs))
		idxs = qtutils.get_selection_from_list (list_widget, index_nums)

		return (selection, idxs)

	def __set_branch_ui_items (self):
		'''Sets up items that mention the current branch name.'''
		current_branch = cmds.git_current_branch()
		menu_text = 'Browse ' + current_branch + ' branch'
		self.view.browseBranch.setText (menu_text)

		status_text = 'Current branch: ' + current_branch
		self.view.statusBar().showMessage (status_text)

	def __start_inotify_thread (self, model):
		# Do we have inotify?  If not, return.
		# Recommend installing inotify if we're on Linux.
		self.inotify_thread = None
		try:
			from inotify import GitNotifier
		except ImportError:
			import platform
			if platform.system() == 'Linux':
				msg = ('ugit could not find python-inotify.'
					+ '\nSupport for inotify is disabled.')

				plat = platform.platform().lower()
				if 'debian' in plat or 'ubuntu' in plat:
					msg += '\n\nHint: sudo apt-get install python-pyinotify'

				qtutils.information (self.view,
					'inotify support disabled',
					msg)
			return

		self.inotify_thread = GitNotifier (os.getcwd())
		self.connect ( self.inotify_thread, 'timeForRescan()',
			lambda: self.cb_rescan (model) )

		# Start the notification thread
		self.inotify_thread.start()

	def __show_command (self, output, model=None, rescan=True):
		'''Shows output and optionally rescans for changes.'''
		qtutils.show_command (self.view, output)
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
