#!/usr/bin/env python
import os
import time

from PyQt4 import QtGui
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QMenu

import utils
import qtutils
import defaults
from qobserver import QObserver
from repobrowsercontroller import browse_git_branch
from createbranchcontroller import create_new_branch
from pushcontroller import push_branches
from utilcontroller import choose_branch
from utilcontroller import select_commits
from utilcontroller import update_options

class Controller(QObserver):
	'''The controller is a mediator between the model and view.
	It allows for a clean decoupling between view and model classes.'''

	def __init__(self, model, view):
		QObserver.__init__(self, model, view)

		self.__last_inotify_event = time.time()

		# The diff-display context menu
		self.__menu = None
		self.__staged_diff_in_view = True

		# Diff display context menu
		view.displayText.contextMenuEvent = self.diff_context_menu_event

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
				view.rescan, view.options,
				view.createBranch, view.checkoutBranch,
				view.rebaseBranch, view.deleteBranch,
				view.setCommitMessage, view.commit,
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
		self.add_callbacks(
			# Actions that delegate directly to the model
			signOffButton = model.add_signoff,
			setCommitMessage = model.get_prev_commitmsg,
			stageChanged = self.model.stage_changed,
			stageUntracked = self.model.stage_untracked,
			unstageAll = self.model.unstage_all,

			# Actions that delegate direclty to the view
			cut = view.action_cut,
			copy = view.action_copy,
			paste = view.action_paste,
			delete = view.action_delete,
			selectAll = view.action_select_all,
			undo = view.action_undo,
			redo = view.action_redo,

			# Push Buttons
			stageButton = self.stage_selected,
			commitButton = self.commit,
			pushButton = self.push,

			# List Widgets
			stagedList = self.diff_staged,
			unstagedList = self.diff_unstaged,

			# Checkboxes
			untrackedCheckBox = self.rescan,

			# Menu Actions
			options = self.options,
			rescan = self.rescan,
			createBranch = self.branch_create,
			deleteBranch = self.branch_delete,
			checkoutBranch = self.checkout_branch,
			rebaseBranch = self.rebase,
			commit = self.commit,
			stageSelected = self.stage_selected,
			unstageSelected = self.unstage_selected,
			showDiffstat = self.show_diffstat,
			browseBranch = self.browse_current,
			browseOtherBranch = self.browse_other,
			visualizeCurrent = self.viz_current,
			visualizeAll = self.viz_all,
			exportPatches = self.export_patches,
			cherryPick = self.cherry_pick,
			loadCommitMsg = self.load_commitmsg,

			# Splitters
			splitter_top = self.splitter_top_event,
			splitter_bottom = self.splitter_bottom_event,
			)

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
		self.load_window_settings()
		self.rescan()

		# Setup the inotify watchdog
		self.start_inotify_thread()

	#####################################################################
	# event() is called in response to messages from the inotify thread

	def event(self, msg):
		if msg.type() == defaults.INOTIFY_EVENT:
			self.rescan()
			return True
		else:
			return False

	#####################################################################
	# Actions triggered during model updates

	def action_staged(self, widget):
		qtutils.update_listwidget(widget,
				self.model.get_staged(), staged=True)

	def action_all_unstaged(self, widget):
		qtutils.update_listwidget(widget,
				self.model.get_unstaged(), staged=False)

		if self.view.untrackedCheckBox.isChecked():
			qtutils.update_listwidget(widget,
					self.model.get_untracked(),
					staged=False,
					append=True,
					untracked=True)

	#####################################################################
	# Qt callbacks

	def options(self):
		update_options(self.model, self.view)

	def branch_create(self):
		if create_new_branch(self.model, self.view):
			self.rescan()

	def branch_delete(self):
		branch = choose_branch('Delete Branch',
				self.view, self.model.get_local_branches())
		if not branch: return
		self.show_output(self.model.delete_branch(branch))

	def browse_current(self):
		branch = self.model.get_branch()
		browse_git_branch(self.model, self.view, branch)

	def browse_other(self):
		# Prompt for a branch to browse
		branch = choose_branch('Browse Branch Files',
				self.view, self.model.get_all_branches())
		if not branch: return
		# Launch the repobrowser
		browse_git_branch(self.model, self.view, branch)

	def checkout_branch(self):
		branch = choose_branch('Checkout Branch',
				self.view, self.model.get_local_branches())
		if not branch: return
		self.show_output(self.model.checkout(branch))

	def cherry_pick(self):
		commits = self.select_commits_gui(*self.model.log(all=True))
		if not commits: return
		self.show_output(self.model.cherry_pick(commits))

	def commit(self):
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

			self.show_output(error_msg)
			return

		files = self.model.get_staged()
		if not files:
			errmsg = self.tr(""
				+ "No changes to commit.\n"
				+ "\n"
				+ "You must stage at least 1 file before you can commit.\n")
			self.show_output(errmsg)
			return

		# Perform the commit
		output = self.model.commit(msg, amend=self.view.amendRadio.isChecked())

		# Reset state
		self.view.newCommitRadio.setChecked(True)
		self.view.amendRadio.setChecked(False)
		self.model.set_commitmsg('')
		self.show_output(output)

	def view_diff(self, staged=True):
		self.__staged_diff_in_view = staged
		if self.__staged_diff_in_view:
			widget = self.view.stagedList
		else:
			widget = self.view.unstagedList
		row, selected = qtutils.get_selected_row(widget)
		if not selected:
			self.view.reset_display()
			return
		(diff,
		status) = self.model.get_diff_and_status(row, staged=staged)

		self.view.set_display(diff)
		self.view.set_info(self.tr(status))

	# use *rest to handle being called from different signals
	def diff_staged(self, *rest):
		self.view_diff(staged=True)

	# use *rest to handle being called from different signals
	def diff_unstaged(self,*rest):
		self.view_diff(staged=False)

	def export_patches(self):
		(revs, summaries) = self.model.log()
		commits = self.select_commits_gui(revs, summaries)
		if not commits: return
		self.show_output(self.model.format_patch(commits))

	def last_window_closed(self):
		'''Save config settings and cleanup any inotify threads.'''

		self.model.save_window_geom()

		if not self.inotify_thread: return
		if not self.inotify_thread.isRunning(): return

		self.inotify_thread.abort = True
		self.inotify_thread.terminate()
		self.inotify_thread.wait()

	def load_commitmsg(self):
		file = qtutils.open_dialog(self.view,
				'Load Commit Message...', defaults.DIRECTORY)

		if file:
			defaults.DIRECTORY = os.path.dirname(file)
			slushy = utils.slurp(file)
			if slushy: self.model.set_commitmsg(slushy)

	def rebase(self):
		branch = choose_branch('Rebase Branch',
				self.view, self.model.get_local_branches())
		if not branch: return
		self.show_output(self.model.rebase(branch))

	# use *rest to handle being called from the checkbox signal
	def rescan(self, *rest):
		'''Populates view widgets with results from "git status."'''

		self.view.statusBar().showMessage(
			self.tr('Scanning for modified files ...'))

		self.model.update_status()

		branch = self.model.get_branch()
		status_text = self.tr('Current Branch:') + ' ' + branch
		self.view.statusBar().showMessage(status_text)

		title = '%s [%s]' % (self.model.get_project(), branch)
		self.view.setWindowTitle(title)

		if not self.model.has_squash_msg(): return

		if self.model.get_commitmsg():
			answer = qtutils.question(self.view,
				self.tr('Import Commit Message?'),
				self.tr('A commit message from an in-progress'
				+ ' merge was found.\nImport it?'))

			if not answer: return

		# Set the new commit message
		self.model.set_squash_msg()

	def push(self):
		push_branches(self.model, self.view)

	def show_diffstat(self):
		'''Show the diffstat from the latest commit.'''
		self.show_output(self.model.diff_stat(), rescan=False)

	#####################################################################
	# diff gui

	def process_diff_selection(self, items, widget,
			cached=True, selected=False, reverse=True, noop=False):

		filename = qtutils.get_selected_item(widget, items)
		if not filename: return
		parser = utils.DiffParser(self.model, filename=filename,
				cached=cached)

		offset, selection = self.view.diff_selection()
		parser.process_diff_selection(selected, offset, selection)
		self.rescan()

	def stage_hunk(self):
		self.process_diff_selection(
				self.model.get_unstaged(),
				self.view.unstagedList,
				cached=False)

	def stage_hunks(self):
		self.process_diff_selection(
				self.model.get_unstaged(),
				self.view.unstagedList,
				cached=False,
				selected=True)

	def unstage_hunk(self, cached=True):
		self.process_diff_selection(
				self.model.get_staged(),
				self.view.stagedList,
				cached=True)

	def unstage_hunks(self):
		self.process_diff_selection(
				self.model.get_staged(),
				self.view.stagedList,
				cached=True,
				selected=True)

	# #######################################################################
	# end diff gui

	# use *rest to handle being called from different signals
	def stage_selected(self,*rest):
		'''Use "git add" to add items to the git index.
		This is a thin wrapper around apply_to_list.'''
		command = self.model.add_or_remove
		widget = self.view.unstagedList
		items = self.model.get_all_unstaged()
		self.apply_to_list(command,widget,items)

	# use *rest to handle being called from different signals
	def unstage_selected(self, *rest):
		'''Use "git reset" to remove items from the git index.
		This is a thin wrapper around apply_to_list.'''
		command = self.model.reset
		widget = self.view.stagedList
		items = self.model.get_staged()
		self.apply_to_list(command, widget, items)

	def viz_all(self):
		'''Visualizes the entire git history using gitk.'''
		utils.fork('gitk','--all')

	def viz_current(self):
		'''Visualizes the current branch's history using gitk.'''
		utils.fork('gitk', self.model.get_branch())

	# These actions monitor window resizes, splitter changes, etc.
	def move_event(self, event):
		defaults.X = event.pos().x()
		defaults.Y = event.pos().y()

	def resize_event(self, event):
		defaults.WIDTH = event.size().width()
		defaults.HEIGHT = event.size().height()

	def splitter_top_event(self,*rest):
		sizes = self.view.splitter_top.sizes()
		defaults.SPLITTER_TOP_0 = sizes[0]
		defaults.SPLITTER_TOP_1 = sizes[1]

	def splitter_bottom_event(self,*rest):
		sizes = self.view.splitter_bottom.sizes()
		defaults.SPLITTER_BOTTOM_0 = sizes[0]
		defaults.SPLITTER_BOTTOM_1 = sizes[1]

	def load_window_settings(self):
		(w,h,x,y,
		st0,st1,
		sb0,sb1) = self.model.get_window_geom()
		self.view.resize(w,h)
		self.view.move(x,y)
		self.view.splitter_top.setSizes([st0,st1])
		self.view.splitter_bottom.setSizes([sb0,sb1])

	def show_output(self, output, rescan=True):
		'''Shows output and optionally rescans for changes.'''
		qtutils.show_output(self.view, output)
		self.rescan()

	#####################################################################
	#

	def apply_to_list(self, command, widget, items):
		'''This is a helper method that retrieves the current
		selection list, applies a command to that list,
		displays a dialog showing the output of that command,
		and calls rescan to pickup changes.'''
		apply_items = qtutils.get_selection_list(widget, items)
		output = command(apply_items)
		self.rescan()
		return output

	def diff_context_menu_about_to_show(self):
		unstaged_item = qtutils.get_selected_item(
				self.view.unstagedList,
				self.model.get_all_unstaged())

		is_tracked= unstaged_item not in self.model.get_untracked()

		enable_staged= (
				unstaged_item
				and not self.__staged_diff_in_view
				and is_tracked)

		enable_unstaged= (
				self.__staged_diff_in_view
				and qtutils.get_selected_item(
						self.view.stagedList,
						self.model.get_staged()))

		self.__stage_hunk_action.setEnabled(bool(enable_staged))
		self.__stage_hunks_action.setEnabled(bool(enable_staged))

		self.__unstage_hunk_action.setEnabled(bool(enable_unstaged))
		self.__unstage_hunks_action.setEnabled(bool(enable_unstaged))

	def diff_context_menu_event(self, event):
		self.diff_context_menu_setup()
		textedit = self.view.displayText
		self.__menu.exec_(textedit.mapToGlobal(event.pos()))

	def diff_context_menu_setup(self):
		if self.__menu: return

		menu = self.__menu = QMenu(self.view)
		self.__stage_hunk_action = menu.addAction(
			self.tr('Stage Hunk For Commit'), self.stage_hunk)

		self.__stage_hunks_action = menu.addAction(
			self.tr('Stage Selected Lines'), self.stage_hunks)

		self.__unstage_hunk_action = menu.addAction(
			self.tr('Unstage Hunk From Commit'), self.unstage_hunk)

		self.__unstage_hunks_action = menu.addAction(
			self.tr('Unstage Selected Lines'), self.unstage_hunks)

		self.__copy_action = menu.addAction(
			self.tr('Copy'), self.view.copy_display)

		self.connect(self.__menu, 'aboutToShow()',
			self.diff_context_menu_about_to_show)

	def select_commits_gui(self, revs, summaries):
		return select_commits(self.model, self.view, revs, summaries)

	def start_inotify_thread(self):
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
		# Start the notification thread
		self.inotify_thread = GitNotifier(self, os.getcwd())
		self.inotify_thread.start()
