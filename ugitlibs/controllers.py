#!/usr/bin/env python
import os
import time

from PyQt4 import QtGui
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QMenu
from PyQt4.QtGui import QFont

import utils
import qtutils
import defaults
from qobserver import QObserver
from repobrowsercontroller import browse_git_branch
from createbranchcontroller import create_new_branch
from pushcontroller import push_branches
from utilcontroller import choose_branch
from utilcontroller import select_commits
from utilcontroller import find_revisions
from utilcontroller import update_options
from utilcontroller import log_window

class Controller(QObserver):
	'''Controller manages the interaction between the model and views.'''

	def __init__(self, model, view):
		QObserver.__init__(self, model, view)

		# parent-less log window
		qtutils.LOGGER = log_window(model, QtGui.qApp.activeWindow())

		self.__last_inotify_event = time.time()

		# The diff-display context menu
		self.__menu = None
		self.__staged_diff_in_view = True

		# Diff display context menu
		view.display_text.contextMenuEvent = self.diff_context_menu_event

		# Binds a specific model attribute to a view widget,
		# and vice versa.
		self.model_to_view('commitmsg', 'commit_text')
		self.model_to_view('staged', 'staged_list')
		self.model_to_view('all_unstaged', 'unstaged_list')

		# When a model attribute changes, this runs a specific action
		self.add_actions('staged', self.action_staged)
		self.add_actions('all_unstaged', self.action_all_unstaged)
		self.add_actions('global.ugit.fontdiff', self.update_diff_font)
		self.add_actions('global.ugit.fontui', self.update_ui_font)

		# These callbacks are called in response to the signals
		# defined above.  One property of the QObserver callback
		# mechanism is that the model is passed in as the first
		# argument to the callback.  This allows for a single
		# controller to manage multiple models, though this
		# isn't used at the moment.
		self.add_callbacks(
			# Actions that delegate directly to the model
			signoff_button = model.add_signoff,
			menu_get_prev_commitmsg = model.get_prev_commitmsg,
			menu_stage_changed =
				lambda: self.log_output(self.model.stage_changed()),
			menu_stage_untracked =
				lambda: self.log_output(self.model.stage_untracked()),
			menu_unstage_all =
				lambda: self.log_output(self.model.unstage_all()),

			# Actions that delegate direclty to the view
			menu_cut = view.action_cut,
			menu_copy = view.action_copy,
			menu_paste = view.action_paste,
			menu_delete = view.action_delete,
			menu_select_all = view.action_select_all,
			menu_undo = view.action_undo,
			menu_redo = view.action_redo,

			# Push Buttons
			stage_button = self.stage_selected,
			commit_button = self.commit,
			push_button = self.push,

			# List Widgets
			staged_list = self.diff_staged,
			unstaged_list = self.diff_unstaged,

			# Checkboxes
			untracked_checkbox = self.rescan,

			# File Menu
			menu_load_commitmsg = self.load_commitmsg,
			menu_quit = self.quit_app,

			# Repository Menu
			menu_visualize_current = self.viz_current,
			menu_visualize_all = self.viz_all,
			menu_show_revision = self.show_revision,
			menu_browse_commits = self.browse_commits,
			menu_browse_branch = self.browse_current,
			menu_browse_other_branch = self.browse_other,

			# Commit Menu
			menu_rescan = self.rescan,
			menu_create_branch = self.branch_create,
			menu_delete_branch = self.branch_delete,
			menu_checkout_branch = self.checkout_branch,
			menu_rebase_branch = self.rebase,
			menu_commit = self.commit,
			menu_stage_selected = self.stage_selected,
			menu_unstage_selected = self.unstage_selected,
			menu_show_diffstat = self.show_diffstat,
			menu_export_patches = self.export_patches,
			menu_cherry_pick = self.cherry_pick,
			menu_load_commitmsg = self.load_commitmsg,
			# Edit Menu
			menu_options = self.options,

			# Splitters
			splitter_top = self.splitter_top_event,
			splitter_bottom = self.splitter_bottom_event)

		# Handle double-clicks in the staged/unstaged lists.
		# These are vanilla signal/slots since the qobserver
		# signal routing is already handling these lists' signals.
		self.connect(view.unstaged_list,
				'itemDoubleClicked(QListWidgetItem*)',
				self.stage_selected)

		self.connect(view.staged_list,
				'itemDoubleClicked(QListWidgetItem*)',
				self.unstage_selected)

		# Toolbar log button
		self.connect(self.view.toolbar_show_log,
				'triggered()', self.show_log)
		# App cleanup
		self.connect(QtGui.qApp, 'lastWindowClosed()',
				self.last_window_closed)

		# Delegate window events here
		view.moveEvent = self.move_event
		view.resizeEvent = self.resize_event
		view.closeEvent = self.quit_app

		# Initialize the GUI
		self.load_window_settings()

		# Initialize the log window
		self.init_log()

		# Setup the inotify watchdog
		self.start_inotify_thread()

		self.rescan()
		self.refresh_view()

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

		if self.view.untracked_checkbox.isChecked():
			qtutils.update_listwidget(widget,
					self.model.get_untracked(),
					staged=False,
					append=True,
					untracked=True)

	#####################################################################
	# Qt callbacks

	def show_log(self, *rest):
		qtutils.toggle_log_window()

	def options(self):
		update_options(self.model, self.view)

	def branch_create(self):
		if create_new_branch(self.model, self.view):
			self.rescan()

	def branch_delete(self):
		branch = choose_branch('Delete Branch',
				self.view, self.model.get_local_branches())
		if not branch: return
		self.log_output(self.model.delete_branch(branch))

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
		self.log_output(self.model.checkout(branch))

	def browse_commits(self):
		self.select_commits_gui(self.tr('Browse Commits'),
				*self.model.log(all=True))

	def show_revision(self):
		find_revisions(self.model, self.view)

	def cherry_pick(self):
		commits = self.select_commits_gui(self.tr('Cherry-Pick Commits'),
				*self.model.log(all=True))
		if not commits: return
		self.log_output(self.model.cherry_pick(commits))

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
			self.log_output(error_msg)
			return

		files = self.model.get_staged()
		if not files:
			error_msg = self.tr(""
				+ "No changes to commit.\n"
				+ "\n"
				+ "You must stage at least 1 file before you can commit.\n")
			self.log_output(error_msg)
			return

		# Perform the commit
		output = self.model.commit(
				msg, amend=self.view.amend_radio.isChecked())

		# Reset state
		self.view.new_commit_radio.setChecked(True)
		self.view.amend_radio.setChecked(False)
		self.model.set_commitmsg('')
		self.log_output(output)

	def view_diff(self, staged=True):
		self.__staged_diff_in_view = staged
		if self.__staged_diff_in_view:
			widget = self.view.staged_list
		else:
			widget = self.view.unstaged_list
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
		commits = self.select_commits_gui(self.tr('Export Patches'),
				revs, summaries)
		if not commits: return
		self.log_output(self.model.format_patch(commits))

	def quit_app(self,*rest):
		'''Save config settings and cleanup any inotify threads.'''

		self.model.save_window_geom()
		qtutils.close_log_window()
		self.view.hide()

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
		self.log_output(self.model.rebase(branch))

	# use *rest to handle being called from the checkbox signal
	def rescan(self, *rest):
		'''Populates view widgets with results from "git status."'''
		self.model.update_status()
		self.view.setWindowTitle('%s [%s]' % (
				self.model.get_project(),
				self.model.get_branch()))

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
		self.log_output(self.model.diff_stat())

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
				self.view.unstaged_list,
				cached=False)
	def stage_hunk_selection(self):
		self.process_diff_selection(
				self.model.get_unstaged(),
				self.view.unstaged_list,
				cached=False,
				selected=True)
	def unstage_hunk(self, cached=True):
		self.process_diff_selection(
				self.model.get_staged(),
				self.view.staged_list,
				cached=True)
	def unstage_hunk_selection(self):
		self.process_diff_selection(
				self.model.get_staged(),
				self.view.staged_list,
				cached=True,
				selected=True)

	# #######################################################################
	# end diff gui

	# use *rest to handle being called from different signals
	def stage_selected(self,*rest):
		'''Use "git add" to add items to the git index.
		This is a thin wrapper around apply_to_list.'''
		command = self.model.add_or_remove
		widget = self.view.unstaged_list
		items = self.model.get_all_unstaged()
		self.apply_to_list(command,widget,items)

	# use *rest to handle being called from different signals
	def unstage_selected(self, *rest):
		'''Use "git reset" to remove items from the git index.
		This is a thin wrapper around apply_to_list.'''
		command = self.model.reset
		widget = self.view.staged_list
		items = self.model.get_staged()
		self.apply_to_list(command, widget, items)

	def viz_all(self):
		'''Visualizes the entire git history using gitk.'''
		browser = self.model.get_history_browser()
		utils.fork(browser,'--all')

	def viz_current(self):
		'''Visualizes the current branch's history using gitk.'''
		browser = self.model.get_history_browser()
		utils.fork(browser, self.model.get_branch())

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

	def load_window_geom(self):
		(w,h,x,y,
		st0,st1,
		sb0,sb1) = self.model.get_window_geom()
		self.view.resize(w,h)
		self.view.move(x,y)
		self.view.splitter_top.setSizes([st0,st1])
		self.view.splitter_bottom.setSizes([sb0,sb1])

	def log_output(self, output, rescan=True, quiet=False):
		'''Logs output and optionally rescans for changes.'''
		qtutils.log(output, quiet=quiet, doraise=False)
		if rescan: self.rescan()

	#####################################################################
	#

	def apply_to_list(self, command, widget, items):
		'''This is a helper method that retrieves the current
		selection list, applies a command to that list,
		displays a dialog showing the output of that command,
		and calls rescan to pickup changes.'''
		apply_items = qtutils.get_selection_list(widget, items)
		output = command(apply_items)
		self.log_output(output, quiet=True)

	def diff_context_menu_about_to_show(self):
		unstaged_item = qtutils.get_selected_item(
				self.view.unstaged_list,
				self.model.get_all_unstaged())

		is_tracked= unstaged_item not in self.model.get_untracked()

		enable_staged= (
				unstaged_item
				and not self.__staged_diff_in_view
				and is_tracked)

		enable_unstaged= (
				self.__staged_diff_in_view
				and qtutils.get_selected_item(
						self.view.staged_list,
						self.model.get_staged()))

		self.__stage_hunk_action.setEnabled(bool(enable_staged))
		self.__stage_hunk_selection_action.setEnabled(bool(enable_staged))

		self.__unstage_hunk_action.setEnabled(bool(enable_unstaged))
		self.__unstage_hunk_selection_action.setEnabled(bool(enable_unstaged))

	def diff_context_menu_event(self, event):
		self.diff_context_menu_setup()
		textedit = self.view.display_text
		self.__menu.exec_(textedit.mapToGlobal(event.pos()))

	def diff_context_menu_setup(self):
		if self.__menu: return

		menu = self.__menu = QMenu(self.view)
		self.__stage_hunk_action = menu.addAction(
			self.tr('Stage Hunk For Commit'), self.stage_hunk)

		self.__stage_hunk_selection_action = menu.addAction(
			self.tr('Stage Selected Lines'),
			self.stage_hunk_selection)

		self.__unstage_hunk_action = menu.addAction(
			self.tr('Unstage Hunk From Commit'),
			self.unstage_hunk)

		self.__unstage_hunk_selection_action = menu.addAction(
			self.tr('Unstage Selected Lines'),
			self.unstage_hunk_selection)

		self.__copy_action = menu.addAction(
			self.tr('Copy'), self.view.copy_display)

		self.connect(self.__menu, 'aboutToShow()',
			self.diff_context_menu_about_to_show)

	def select_commits_gui(self, title, revs, summaries):
		return select_commits(self.model, self.view, title, revs, summaries)

	def update_diff_font(self):
		font = self.model.get_param('global.ugit.fontdiff')
		if not font: return
		qfont = QFont()
		qfont.fromString(font)
		self.view.display_text.setFont(qfont)
		self.view.commit_text.setFont(qfont)

	def update_ui_font(self):
		font = self.model.get_param('global.ugit.fontui')
		if not font: return
		qfont = QFont()
		qfont.fromString(font)
		QtGui.qApp.setFont(qfont)

	def init_log(self):
		branch, version = self.model.get_branch(), defaults.VERSION
		qtutils.log(self.model.get_git_version()
				+ '\nugit version '+ version
				+ '\nCurrent Branch: '+ branch)

	def start_inotify_thread(self):
		# Do we have inotify?  If not, return.
		# Recommend installing inotify if we're on Linux.
		self.inotify_thread = None
		try:
			from inotify import GitNotifier
			qtutils.log('inotify support: enabled')
		except ImportError:
			import platform
			if platform.system() == 'Linux':

				msg = self.tr(
					'inotify: disabled\n'
					'Note: To enable inotify, '
					'install python-pyinotify.\n')

				plat = platform.platform()
				if 'debian' in plat or 'ubuntu' in plat:
					msg += self.tr(
						'On Debian or Ubuntu systems, '
						'try: sudo apt-get install '
						'python-pyinotify')
				qtutils.log(msg)

			return

		# Start the notification thread
		self.inotify_thread = GitNotifier(self, os.getcwd())
		self.inotify_thread.start()
