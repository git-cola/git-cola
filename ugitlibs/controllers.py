#!/usr/bin/env python
import os
import commands
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QMenu
from qobserver import QObserver
import cmds
import utils
import qtutils
import defaults
from views import GitPushDialog
from views import GitBranchDialog
from views import GitCreateBranchDialog
from views import GitCommitBrowser
from repobrowsercontroller import GitRepoBrowserController
from createbranchcontroller import GitCreateBranchController
from pushcontroller import GitPushController

class GitController(QObserver):
	'''The controller is a mediator between the model and view.
	It allows for a clean decoupling between view and model classes.'''

	def __init__(self, model, view):
		QObserver.__init__(self, model, view)

		# The diff-display context menu
		self.__menu = None
		self.__staged_diff_in_view = True

		# Diff display context menu
		view.displayText.controller = self
		view.displayText.contextMenuEvent = self.__menu_event

		# Default to creating a new commit(i.e. not an amend commit)
		view.newCommitRadio.setChecked(True)

		# Binds a specific model attribute to a view widget,
		# and vice versa.
		self.model_to_view('commitmsg', 'commitText')
		self.model_to_view('staged', 'stagedList')
		self.model_to_view('all_unstaged', 'unstagedList')

		# When a model attribute changes, this runs a specific action
		self.add_actions('staged', self.action_staged)
		self.add_actions('all_unstaged', self.action_all_unstaged)

		# Routes signals for multiple widgets to our callbacks
		# defined below.
		self.add_signals('textChanged()', view.commitText)
		self.add_signals('stateChanged(int)', view.untrackedCheckBox)

		self.add_signals('released()',
				view.stageButton, view.commitButton,
				view.pushButton, view.signOffButton,)

		self.add_signals('triggered()',
				view.rescan,
				view.createBranch, view.checkoutBranch,
				view.rebaseBranch, view.deleteBranch,
				view.commitAll, view.commitSelected,
				view.setCommitMessage,
				view.stageChanged, view.stageUntracked,
				view.stageSelected, view.unstageAll,
				view.unstageSelected,
				view.showDiffstat,
				view.browseBranch, view.browseOtherBranch,
				view.visualizeAll, view.visualizeCurrent,
				view.exportPatches, view.cherryPick,
				view.loadCommitMsg,
				view.cut, view.copy, view.paste, view.delete,
				view.selectAll, view.undo, view.redo,)

		self.add_signals('itemClicked(QListWidgetItem *)',
				view.stagedList, view.unstagedList,)

		self.add_signals('itemSelectionChanged()',
				view.stagedList, view.unstagedList,)

		self.add_signals('splitterMoved(int,int)',
				view.splitter_top, view.splitter_bottom)

		# App cleanup
		self.connect(QtGui.qApp, 'lastWindowClosed()',
				self.last_window_closed)

		# These callbacks are called in response to the signals
		# defined above.  One property of the QObserver callback
		# mechanism is that the model is passed in as the first
		# argument to the callback.  This allows for a single
		# controller to manage multiple models, though this
		# isn't used at the moment.
		self.add_callbacks({
				# Actions that delegate directly to the model
				'signOffButton': model.add_signoff,
				'setCommitMessage': model.get_prev_commitmsg,
				# Push Buttons
				'stageButton': self.stage_selected,
				'commitButton': self.commit,
				'pushButton': self.push,
				# List Widgets
				'stagedList': self.diff_staged,
				'unstagedList': self.diff_unstaged,
				# Checkboxes
				'untrackedCheckBox': self.rescan,
				# Menu Actions
				'rescan': self.rescan,
				'createBranch': self.branch_create,
				'deleteBranch': self.branch_delete,
				'checkoutBranch': self.checkout_branch,
				'rebaseBranch': self.rebase,
				'commitAll': self.commit_all,
				'commitSelected': self.commit_selected,
				'stageChanged': self.stage_changed,
				'stageUntracked': self.stage_untracked,
				'stageSelected': self.stage_selected,
				'unstageAll': self.unstage_all,
				'unstageSelected': self.unstage_selected,
				'showDiffstat': self.show_diffstat,
				'browseBranch': self.browse_current,
				'browseOtherBranch': self.browse_other,
				'visualizeCurrent': self.viz_current,
				'visualizeAll': self.viz_all,
				'exportPatches': self.export_patches,
				'cherryPick': self.cherry_pick,
				'loadCommitMsg': self.load_commitmsg,
				'cut': self.cut,
				'copy': self.copy,
				'paste': self.paste,
				'delete': self.delete,
				'selectAll': self.select_all,
				'undo': self.view.commitText.undo,
				'redo': self.redo,
				# Splitters
				'splitter_top': self.splitter_top_moved,
				'splitter_bottom': self.splitter_bottom_moved,
				})

		# Handle double-clicks in the staged/unstaged lists.
		# These are vanilla signal/slots since the qobserver
		# signal routing is already handling these lists' signals.
		self.connect(view.unstagedList,
				'itemDoubleClicked(QListWidgetItem*)',
				self.stage_selected)

		self.connect(view.stagedList,
				'itemDoubleClicked(QListWidgetItem*)',
				self.unstage_selected )

		# Delegate window move events here
		self.view.moveEvent = self.move_event
		self.view.resizeEvent = self.resize_event

		# Initialize the GUI
		self.__read_config_settings()
		self.rescan()

		# Setup the inotify watchdog
		self.__start_inotify_thread()

	#####################################################################
	# Actions
	# Notify callbacks from the model

	def action_staged(self, widget):
		self.__update_listwidget(widget,
				self.model.get_staged(), staged=True)

	def action_all_unstaged(self, widget):
		self.__update_listwidget(widget,
				self.model.get_unstaged(), staged=False)

		if self.view.untrackedCheckBox.isChecked():
			self.__update_listwidget(widget,
					self.model.get_untracked(),
					append=True,
					staged=False,
					untracked=True)

	#####################################################################
	# Qt callbacks

	def branch_create(self):
		view = GitCreateBranchDialog(self.view)
		controller = GitCreateBranchController(self.model, view)
		view.show()
		result = view.exec_()
		if result == QDialog.Accepted:
			self.rescan()

	def branch_delete(self):
		dlg = GitBranchDialog(self.view, branches=cmds.git_branch())
		branch = dlg.getSelectedBranch()
		if not branch: return
		qtutils.show_command(self.view,
				cmds.git_branch(name=branch, delete=True))

	def browse_current(self):
		self.__browse_branch(cmds.git_current_branch())

	def browse_other(self):
		# Prompt for a branch to browse
		branches = self.model.all_branches()
		dialog = GitBranchDialog(self.view, branches=branches)

		# Launch the repobrowser
		self.__browse_branch(dialog.getSelectedBranch())

	def checkout_branch(self):
		dlg = GitBranchDialog(self.view, cmds.git_branch())
		branch = dlg.getSelectedBranch()
		if not branch: return
		qtutils.show_command(self.view, cmds.git_checkout(branch))
		self.rescan()

	def cherry_pick(self):
		'''Starts a cherry-picking session.'''
		(revs, summaries) = cmds.git_log(all=True)
		selection, idxs = self.__select_commits(revs, summaries)
		output = cmds.git_cherry_pick(selection)
		self.__show_command(self.tr(output))

	def commit(self):
		'''Sets up data and calls cmds.commit.'''
		msg = self.model.get_commitmsg()
		if not msg:
			error_msg = self.tr(""
				+ "Please supply a commit message.\n"
				+ "\n"
				+ "A good commit message has the following format:\n"
				+ "\n"
				+ "- First line: Describe in one sentence what you did.\n"
				+ "- Second line: Blank\n"
				+ "- Remaining lines: Describe why this change is good.\n")

			self.__show_command(error_msg)
			return

		amend = self.view.amendRadio.isChecked()
		commit_all = self.view.commitAllCheckBox.isChecked()

		files = []
		if commit_all:
			files = self.model.get_staged()
			if not files:
				errmsg = self.tr(""
					+ "No changes to commit.\n"
					+ "\n"
					+ "You must stage at least 1 file before you can commit.\n")
				self.__show_command(errmsg)
				return
		else:
			wlist = self.view.stagedList
			mlist = self.model.get_staged()
			files = qtutils.get_selection_list(wlist, mlist)
			if not files:
				errmsg = self.tr('No files selected.')
				self.__show_command(errmsg)
				return
		# Perform the commit
		output = cmds.git_commit(msg, amend, files)

		# Reset state
		self.view.newCommitRadio.setChecked(True)
		self.view.amendRadio.setChecked(False)
		self.model.set_commitmsg('')
		self.__show_command(output)

	def commit_all(self):
		'''Sets the commit-all checkbox and runs commit.'''
		self.view.commitAllCheckBox.setChecked(True)
		self.commit()

	def commit_selected(self):
		'''Unsets the commit-all checkbox and runs commit.'''
		self.view.commitAllCheckBox.setChecked(False)
		self.commit()

	def commit_sha1_selected(self, browser, revs):
		'''This callback is called when a commit browser's
		item is selected.  This callback puts the current
		revision sha1 into the commitText field.
		This callback also puts shows the commit in the
		browser's commit textedit and copies it into
		the global clipboard/selection.'''
		current = browser.commitList.currentRow()
		item = browser.commitList.item(current)
		if not item.isSelected():
			browser.commitText.setText('')
			browser.revisionLine.setText('')
			return

		# Get the commit's sha1 and put it in the revision line
		sha1 = revs[current]
		browser.revisionLine.setText(sha1)
		browser.revisionLine.selectAll()

		# Lookup the info for that sha1 and display it
		commit_diff = cmds.git_show(sha1)
		browser.commitText.setText(commit_diff)

		# Copy the sha1 into the clipboard
		qtutils.set_clipboard(sha1)

	# use *rest to handle being called from different signals
	def diff_staged(self, *rest):
		self.__staged_diff_in_view = True
		widget = self.view.stagedList
		row, selected = qtutils.get_selected_row(widget)

		if not selected:
			self.__reset_display()
			return

		filename = self.model.get_staged()[row]
		diff = cmds.git_diff(filename, staged=True)

		if os.path.exists(filename):
			self.__set_info(self.tr('Staged for commit'))
		else:
			self.__set_info(self.tr('Staged for removal'))

		self.view.displayText.setText(diff)

	# use *rest to handle being called from different signals
	def diff_unstaged(self,*rest):
		self.__staged_diff_in_view = False
		widget = self.view.unstagedList

		row, selected = qtutils.get_selected_row(widget)
		if not selected:
			self.__reset_display()
			return

		filename =(self.model.get_unstaged()
			+ self.model.get_untracked())[row]
		if os.path.isdir(filename):
			self.__set_info(self.tr('Untracked directory'))
			cmd = 'ls -la %s' % utils.shell_quote(filename)
			output = commands.getoutput(cmd)
			self.view.displayText.setText(output )
			return

		if filename in self.model.get_unstaged():
			diff = cmds.git_diff(filename, staged=False)
			msg = diff
			self.__set_info(self.tr('Modified, not staged'))
		else:
			# untracked file
			cmd = 'file -b %s' % utils.shell_quote(filename)
			file_type = commands.getoutput(cmd)

			if 'binary' in file_type or 'data' in file_type:
				sq_filename = utils.shell_quote(filename)
				cmd = 'hexdump -C %s' % sq_filename
				contents = commands.getoutput(cmd)
			else:
				if os.path.exists(filename):
					file = open(filename, 'r')
					contents = file.read()
					file.close()

				else: contents = ''

			self.__set_info(self.tr('Untracked, not staged')
					+ ': ' + file_type)
			msg = contents

		self.view.displayText.setText(msg)

	def display_copy(self):
		cursor = self.view.displayText.textCursor()
		selection = cursor.selection().toPlainText()
		qtutils.set_clipboard(selection)

	def export_patches(self):
		'''Launches the commit browser and exports the selected
		patches.'''

		(revs, summaries) = cmds.git_log()
		selection, idxs = self.__select_commits(revs, summaries)
		if not selection: return

		# now get the selected indices to determine whether
		# a range of consecutive commits were selected
		selected_range = range(idxs[0], idxs[-1] + 1)
		export_range = len(idxs) > 1 and idxs == selected_range

		output = cmds.git_format_patch(selection, export_range)
		self.__show_command(output)

	def get_commit_msg(self):
		self.model.retrieve_latest_commitmsg()

	def last_window_closed(self):
		'''Save config settings and cleanup the any inotify threads.'''

		self.__save_config_settings()

		if not self.inotify_thread: return
		if not self.inotify_thread.isRunning(): return

		self.inotify_thread.abort = True
		self.inotify_thread.quit()
		self.inotify_thread.wait()

	def load_commitmsg(self):
		file = qtutils.open_dialog(self.view,
			self.tr('Load Commit Message...'),
			defaults.DIRECTORY)

		if file:
			defaults.DIRECTORY = os.path.dirname(file)
			slushy = utils.slurp(file)
			self.model.set_commitmsg(slushy)


	def rebase(self):
		dlg = GitBranchDialog(self.view, cmds.git_branch())
		dlg.setWindowTitle("Select the current branch's new root")
		branch = dlg.getSelectedBranch()
		if not branch: return
		qtutils.show_command(self.view, cmds.git_rebase(branch))

	# use *rest to handle being called from the checkbox signal
	def rescan(self, *rest):
		'''Populates view widgets with results from "git status."'''

		self.view.statusBar().showMessage(
			self.tr('Scanning for modified files ...'))

		# Rescan for repo updates
		self.model.update_status()

		# Scan for branch changes
		self.__set_branch_ui_items()

		if not self.model.has_squash_msg(): return

		if self.model.get_commitmsg():
			answer = qtutils.question(self.view,
				self.tr('Import Commit Message?'),
				self.tr('A commit message from an in-progress'
				+ ' merge was found.\nImport it?'))

			if not answer: return

		# Set the new commit message
		self.model.set_commitmsg(self.model.get_squash_msg())

	def push(self):
		model = self.model.clone()
		view = GitPushDialog(self.view)
		controller = GitPushController(model,view)
		view.show()
		view.exec_()

	def cut(self):
		self.copy()
		self.delete()

	def copy(self):
		cursor = self.view.commitText.textCursor()
		selection = cursor.selection().toPlainText()
		qtutils.set_clipboard(selection)

	def paste(self): self.view.commitText.paste()
	def undo(self): self.view.commitText.undo()
	def redo(self): self.view.commitText.redo()
	def select_all(self): self.view.commitText.selectAll()
	def delete(self):
		self.view.commitText.textCursor().removeSelectedText()

	def show_diffstat(self):
		'''Show the diffstat from the latest commit.'''
		self.__show_command(cmds.git_diff_stat(), rescan=False)

	def stage_changed(self):
		'''Stage all changed files for commit.'''
		output = cmds.git_add(self.model.get_unstaged())
		self.__show_command(output)

	def stage_hunk(self):

		list_widget = self.view.unstagedList
		row, selected = qtutils.get_selected_row(list_widget)
		if not selected: return

		filename = self.model.get_uncommitted_item(row)

		if not os.path.exists(filename): return
		if os.path.isdir(filename): return

		cursor = self.view.displayText.textCursor()
		offset = cursor.position()

		selection = cursor.selection().toPlainText()
		header, diff = cmds.git_diff(filename,
					with_diff_header=True,
					staged=False)
		parser = utils.DiffParser(diff)

		num_selected_lines = selection.count(os.linesep)
		has_selection =(selection
				and selection.count(os.linesep) > 0)

		if has_selection:
			start = diff.index(selection)
			end = start + len(selection)
			diffs = parser.get_diffs_for_range(start, end)
		else:
			diffs = [ parser.get_diff_for_offset(offset) ]

		if not diffs: return

		for diff in diffs:
			tmpfile = utils.get_tmp_filename()
			file = open(tmpfile, 'w')
			file.write(header + os.linesep + diff + os.linesep)
			file.close()
			self.model.apply_diff(tmpfile)
			os.unlink(tmpfile)

		self.rescan()

	def stage_untracked(self):
		'''Stage all untracked files for commit.'''
		output = cmds.git_add(self.model.get_untracked())
		self.__show_command(output)

	# use *rest to handle being called from different signals
	def stage_selected(self,*rest):
		'''Use "git add" to add items to the git index.
		This is a thin wrapper around __apply_to_list.'''
		command = cmds.git_add_or_remove
		widget = self.view.unstagedList
		items = self.model.get_unstaged() + self.model.get_untracked()
		self.__show_command(
			self.__apply_to_list(command, widget, items))

	# use *rest to handle being called from different signals
	def unstage_selected(self, *rest):
		'''Use "git reset" to remove items from the git index.
		This is a thin wrapper around __apply_to_list.'''
		command = cmds.git_reset
		widget = self.view.stagedList
		items = self.model.get_staged()
		self.__show_command(self.__apply_to_list(command, widget, items))

	def unstage_all(self):
		'''Use "git reset" to remove all items from the git index.'''
		output = cmds.git_reset(self.model.get_staged())
		self.__show_command(output)

	def viz_all(self):
		'''Visualizes the entire git history using gitk.'''
		os.system('gitk --all &')

	def viz_current(self):
		'''Visualizes the current branch's history using gitk.'''
		branch = cmds.git_current_branch()
		os.system('gitk %s &' % utils.shell_quote(branch))

	# These actions monitor window resizes, splitter changes, etc.
	def move_event(self, event):
		defaults.X = event.pos().x()
		defaults.Y = event.pos().y()

	def resize_event(self, event):
		defaults.WIDTH = event.size().width()
		defaults.HEIGHT = event.size().height()

	def splitter_top_moved(self,*rest):
		sizes = self.view.splitter_top.sizes()
		defaults.SPLITTER_TOP_0 = sizes[0]
		defaults.SPLITTER_TOP_1 = sizes[1]

	def splitter_bottom_moved(self,*rest):
		sizes = self.view.splitter_bottom.sizes()
		defaults.SPLITTER_BOTTOM_0 = sizes[0]
		defaults.SPLITTER_BOTTOM_1 = sizes[1]

	#####################################################################
	#

	def __apply_to_list(self, command, widget, items):
		'''This is a helper method that retrieves the current
		selection list, applies a command to that list,
		displays a dialog showing the output of that command,
		and calls rescan to pickup changes.'''
		apply_items = qtutils.get_selection_list(widget, items)
		output = command(apply_items)
		self.rescan()
		return output

	def __browse_branch(self, branch):
		if not branch: return
		# Clone the model to allow opening multiple browsers
		# with different sets of data
		model = self.model.clone()
		model.set_branch(branch)
		view = GitCommitBrowser()
		controller = GitRepoBrowserController(model, view)
		view.show()
		view.exec_()

	def __menu_about_to_show(self):
		cursor = self.view.displayText.textCursor()
		allow_hunk_staging = not self.__staged_diff_in_view
		self.__stage_hunk_action.setEnabled(allow_hunk_staging)

	def __menu_event(self, event):
		self.__menu_setup()
		textedit = self.view.displayText
		self.__menu.exec_(textedit.mapToGlobal(event.pos()))

	def __menu_setup(self):
		if self.__menu: return

		menu = QMenu(self.view)
		stage = menu.addAction(self.tr('Stage Hunk For Commit'),
				self.stage_hunk)
		copy = menu.addAction(self.tr('Copy'), self.display_copy)

		self.connect(menu, 'aboutToShow()', self.__menu_about_to_show)

		self.__stage_hunk_action = stage
		self.__copy_action = copy
		self.__menu = menu


	def __file_to_widget_item(self, filename, staged, untracked=False):
		'''Given a filename, return a QListWidgetItem suitable
		for adding to a QListWidget.  "staged" controls whether
		to use icons for the staged or unstaged list widget.'''

		if staged:
			icon_file = utils.get_staged_icon(filename)
		elif untracked:
			icon_file = utils.get_untracked_icon()
		else:
			icon_file = utils.get_icon(filename)

		return qtutils.create_listwidget_item(filename, icon_file)

	def __read_config_settings(self):
		(w,h,x,y,
		st0,st1,
		sb0,sb1) = utils.parse_geom(cmds.git_config('ugit.geometry'))
		self.view.resize(w,h)
		self.view.move(x,y)
		self.view.splitter_top.setSizes([st0,st1])
		self.view.splitter_bottom.setSizes([sb0,sb1])

	def __save_config_settings(self):
		cmds.git_config('ugit.geometry', utils.get_geom())

	def __select_commits(self, revs, summaries):
		'''Use the GitCommitBrowser to select commits from a list.'''
		if not summaries:
			msg = self.tr('ERROR: No commits exist in this branch.')
			self.__show_command(msg)
			return([],[])

		browser = GitCommitBrowser(self.view)
		self.connect(browser.commitList,
				'itemSelectionChanged()',
				lambda: self.commit_sha1_selected(
						browser, revs) )

		for summary in summaries:
			browser.commitList.addItem(summary)

		browser.show()
		result = browser.exec_()
		if result != QDialog.Accepted:
			return([],[])

		list_widget = browser.commitList
		selection = qtutils.get_selection_list(list_widget, revs)
		if not selection: return([],[])

		# also return the selected index numbers
		index_nums = range(len(revs))
		idxs = qtutils.get_selection_list(list_widget, index_nums)

		return(selection, idxs)

	def __set_branch_ui_items(self):
		'''Sets up items that mention the current branch name.'''
		branch = cmds.git_current_branch()

		status_text = self.tr('Current Branch:') + ' ' + branch
		self.view.statusBar().showMessage(status_text)

		project = self.model.get_project()
		title = '%s [%s]' % ( project, branch )

		self.view.setWindowTitle(title)

	def __reset_display(self):
		self.view.displayText.setText('')
		self.__set_info('')

	def __set_info(self,text):
		self.view.displayLabel.setText(text)

	def __start_inotify_thread(self):
		# Do we have inotify?  If not, return.
		# Recommend installing inotify if we're on Linux.
		self.inotify_thread = None
		try:
			from inotify import GitNotifier
		except ImportError:
			import platform
			if platform.system() == 'Linux':
				msg =(self.tr('Unable import pyinotify.\n'
						+ 'inotify support has been'
						+ 'disabled.')
					+ '\n\n')

				plat = platform.platform().lower()
				if 'debian' in plat or 'ubuntu' in plat:
					msg += (self.tr('Hint:')
						+ 'sudo apt-get install'
						+ ' python-pyinotify')

				qtutils.information(self.view,
					self.tr('inotify disabled'), msg)
			return

		self.inotify_thread = GitNotifier(os.getcwd())
		self.connect(self.inotify_thread,
				'timeForRescan()', self.rescan)

		# Start the notification thread
		self.inotify_thread.start()

	def __show_command(self, output, rescan=True):
		'''Shows output and optionally rescans for changes.'''
		qtutils.show_command(self.view, output)
		if rescan: self.rescan()

	def __update_listwidget(self, widget, items,
			staged, untracked=False, append=False):
		'''A helper method to populate a QListWidget with the
		contents of modelitems.'''
		if not append:
			widget.clear()
		for item in items:
			qitem = self.__file_to_widget_item(item,
					staged, untracked)
			widget.addItem(qitem)
