#!/usr/bin/env python
import os
import sys
import time
import glob
import platform

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QMenu
from PyQt4.QtGui import QFont

from cola import utils
from cola import qtutils
from cola import defaults
from cola import version
from cola.qobserver import QObserver

# controllers namespace
import search
from util import logger
from remote import remote_action
from util import choose_from_list
from util import choose_from_combo
from util import select_commits
from util import update_options
from repobrowser import browse_git_branch
from createbranch import create_new_branch
from search import search_commits
from merge import local_merge
from merge import abort_merge
from bookmark import save_bookmark
from bookmark import manage_bookmarks
from stash import stash


class Controller(QObserver):
    """Manages the interaction between models and views."""

    MODE_NONE = 0
    MODE_WORKTREE = 1
    MODE_INDEX = 2
    MODE_AMEND = 3
    MODE_BRANCH = 4
    MODE_GREP = 5

    def init(self, model, view):
        """
        State machine:
        Modes are:
            none -> do nothing, disables most context menus
            branch -> diff against another branch and selectively choose changes
            worktree -> selectively add working changes to the index
            index  -> selectively remove changes from the index
        """
        self.reset_mode()

        # parent-less log window
        qtutils.LOGGER = logger()

        # Unstaged changes context menu
        view.unstaged.contextMenuEvent = self.unstaged_context_menu_event
        view.staged.contextMenuEvent = self.staged_context_menu_event

        # Diff display context menu
        view.display_text.contextMenuEvent = self.diff_context_menu_event

        # Binds model params to their equivalent view widget
        self.add_observables('commitmsg', 'staged', 'unstaged')

        # When a model attribute changes, this runs a specific action
        self.add_actions(staged = self.action_staged)
        self.add_actions(unstaged = self.action_unstaged)
        self.add_actions(global_cola_fontdiff = self.update_diff_font)
        self.add_actions(global_cola_fontui = self.update_ui_font)

        self.add_callbacks(
            # Push Buttons
            signoff_button = self.model.add_signoff,
            stage_button = self.stage_selected,
            commit_button = self.commit,
            fetch_button = self.fetch,
            push_button = self.push,
            pull_button = self.pull,
            # List Widgets
            staged = self.diff_staged,
            unstaged = self.diff_unstaged,
            # Checkboxes
            untracked_checkbox = self.rescan,
            amend_radio = self.load_prev_msg_and_rescan,
            new_commit_radio = self.clear_and_rescan,

            # File Menu
            menu_quit = self.quit_app,
            menu_open_repo = self.open_repo,
            menu_clone_repo = self.clone_repo,
            menu_manage_bookmarks = manage_bookmarks,
            menu_save_bookmark = save_bookmark,

            # Edit Menu
            menu_options = self.options,
            menu_cut = self.view.action_cut,
            menu_copy = self.view.action_copy,
            menu_paste = self.view.action_paste,
            menu_delete = self.view.action_delete,
            menu_select_all = self.view.action_select_all,
            menu_undo = self.view.action_undo,
            menu_redo = self.view.action_redo,

            # Search Menu
            menu_search_grep = self.grep,
            menu_search_revision =
                self.gen_search(search.REVISION_ID),
            menu_search_revision_range =
                self.gen_search(search.REVISION_RANGE),
            menu_search_message =
                self.gen_search(search.MESSAGE),
            menu_search_path =
                self.gen_search(search.PATH, True),
            menu_search_date_range =
                self.gen_search(search.DATE_RANGE),
            menu_search_diff =
                self.gen_search(search.DIFF),
            menu_search_author =
                self.gen_search(search.AUTHOR),
            menu_search_committer =
                self.gen_search(search.COMMITTER),

            # Merge Menu
            menu_merge_local =
                lambda: local_merge(self.model, self.view),
            menu_merge_abort =
                lambda: abort_merge(self.model, self.view),

            # Repository Menu
            menu_visualize_current = self.viz_current,
            menu_visualize_all = self.viz_all,
            menu_browse_commits = self.browse_commits,
            menu_browse_branch = self.browse_current,
            menu_browse_other_branch = self.browse_other,

            # Branch Menu
            menu_create_branch = self.branch_create,
            menu_checkout_branch = self.checkout_branch,
            menu_diff_branch = self.diff_branch,
            menu_difftool_branch = self.difftool_branch,

            # Commit Menu
            menu_rescan = self.rescan,
            menu_delete_branch = self.branch_delete,
            menu_rebase_branch = self.rebase,
            menu_commit = self.commit,
            menu_stage_selected = self.stage_selected,
            menu_unstage_selected = self.unstage_selected,
            menu_show_diffstat = self.show_diffstat,
            menu_show_index = self.show_index,
            menu_export_patches = self.export_patches,
            menu_stash =
                lambda: stash(self.model, self.view),
            menu_load_commitmsg = self.load_commitmsg,
            menu_cherry_pick = self.cherry_pick,
            menu_get_prev_commitmsg = model.get_prev_commitmsg,
            menu_stage_modified =
                lambda: self.log(self.model.stage_modified()),
            menu_stage_untracked =
                lambda: self.log(self.model.stage_untracked()),
            menu_unstage_all =
                lambda: self.log(self.model.unstage_all()),

            # Help Menu
            menu_help_docs =
                lambda: self.model.git.web__browse(utils.get_htmldocs()),
            )

        # Delegate window events here
        view.moveEvent = self.move_event
        view.resizeEvent = self.resize_event
        view.closeEvent = self.quit_app
        view.staged.mousePressEvent = self.click_staged
        view.unstaged.mousePressEvent = self.click_unstaged

        # These are vanilla signal/slots since QObserver
        # is already handling these signals.
        self.connect(view.unstaged,
                     'itemDoubleClicked(QListWidgetItem*)',
                     self.stage_selected)
        self.connect(view.staged,
                     'itemDoubleClicked(QListWidgetItem*)',
                     self.unstage_selected)

        # Toolbar log button
        self.connect(view.toolbar_show_log,
                     'triggered()', self.show_log)

        self.merge_msg_imported = False
        self.load_gui_settings()
        self.rescan()
        self.init_log_window()
        self.refresh_view('global_cola_fontdiff', 'global_cola_fontui')
        self.start_inotify_thread()

    #####################################################################
    # handle when the listitem icons are clicked
    def click_event(self, widget, action_callback, event):
        result = QtGui.QListWidget.mousePressEvent(widget, event)
        xpos = event.pos().x()
        if xpos > 5 and xpos < 20:
            action_callback()
        return result

    def click_staged(self, event):
        return self.click_event(self.view.staged,
                                self.unstage_selected, event)

    def click_unstaged(self, event):
        return self.click_event(self.view.unstaged,
                                self.stage_selected, event)

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
                                  self.model.get_staged(),
                                  staged=True)
        self.view.show_editor()

    def action_unstaged(self, widget):
        qtutils.update_listwidget(widget,
                                  self.model.get_modified(),
                                  staged=False)
        if self.view.untracked_checkbox.isChecked():
            qtutils.update_listwidget(widget,
                                      self.model.get_untracked(),
                                      staged=False,
                                      append=True,
                                      untracked=True)

    #####################################################################
    # Qt callbacks
    def goto_grep(self):
        line = self.view.selected_line()
        filename, lineno, contents = line.split(':', 2)
        if not os.path.exists(filename):
            return
        editor = self.model.get_editor()
        if 'vi' in editor:
            utils.fork(self.model.get_editor(), filename, '+'+lineno)
        else:
            utils.fork(self.model.get_editor(), filename)

    def gen_search(self, searchtype, browse=False):
        def search_handler():
            search_commits(self.model, searchtype, browse)
        return search_handler

    def grep(self):
        txt, ok = qtutils.input('grep')
        if not ok:
            return
        self.mode = Controller.MODE_GREP
        stuff = self.model.git.grep(txt, n=True)
        self.view.display_text.setText(stuff)
        self.view.show_diff()

    def show_log(self, *rest):
        qtutils.toggle_log_window()

    def options(self):
        update_options(self.model, self.view)

    def branch_create(self):
        if create_new_branch(self.model, self.view):
            self.rescan()

    def branch_delete(self):
        branch = choose_from_combo('Delete Branch',
                                   self.view,
                                   self.model.get_local_branches())
        if not branch:
            return
        self.log(self.model.delete_branch(branch))

    def browse_current(self):
        branch = self.model.get_currentbranch()
        browse_git_branch(self.model, self.view, branch)

    def browse_other(self):
        # Prompt for a branch to browse
        branch = choose_from_combo('Browse Branch Files',
                                   self.view,
                                   self.model.get_all_branches())
        if not branch:
            return
        # Launch the repobrowser
        browse_git_branch(self.model, self.view, branch)

    def checkout_branch(self):
        branch = choose_from_combo('Checkout Branch',
                                   self.view,
                                   self.model.get_local_branches())
        if not branch:
            return
        self.log(self.model.git.checkout(branch))

    def browse_commits(self):
        self.select_commits_gui('Browse Commits',
                                *self.model.log_helper(all=True))

    def cherry_pick(self):
        commits = self.select_commits_gui('Cherry-Pick Commits',
                                          *self.model.log_helper(all=True))
        if not commits:
            return
        self.log(self.model.cherry_pick_list(commits))

    def commit(self):
        self.reset_mode()
        msg = self.model.get_commitmsg()
        if not msg:
            error_msg = self.tr(''
                'Please supply a commit message.\n\n'
                'A good commit message has the following format:\n\n'
                '- First line: Describe in one sentence what you did.\n'
                '- Second line: Blank\n'
                '- Remaining lines: Describe why this change is good.\n')
            self.log(error_msg)
            return

        files = self.model.get_staged()
        if not files and not self.view.amend_is_checked():
            error_msg = self.tr(''
                'No changes to commit.\n\n'
                'You must stage at least 1 file before you can commit.\n')
            self.log(error_msg)
            return

        # Perform the commit
        amend = self.view.amend_is_checked()
        status, output = self.model.commit_with_msg(msg, amend=amend)
        if status == 0:
            self.view.reset_checkboxes()
            self.model.set_commitmsg('')
        self.log(output)

    def get_diff_ref(self):
        if self.view.amend_is_checked():
            return 'HEAD^'
        else:
            return 'HEAD'

    def get_selected_filename(self, staged=False):
        if staged:
            widget = self.view.staged
        else:
            widget = self.view.unstaged
        idx, selected = qtutils.get_selected_row(widget)
        if not selected:
            return None
        return self.model.get_filename(idx, staged=staged)

    def view_diff(self, staged=True):
        if staged:
            if self.view.amend_is_checked():
                self.mode = Controller.MODE_AMEND
            else:
                self.mode = Controller.MODE_INDEX
            widget = self.view.staged
        else:
            self.mode = Controller.MODE_WORKTREE
            widget = self.view.unstaged
        row, selected = qtutils.get_selected_row(widget)
        if not selected:
            self.reset_mode()
            self.view.reset_display()
            return
        ref = self.get_diff_ref()
        diff, status, filename = self.model.get_diff_details(row, ref,
                                                             staged=staged)
        self.view.set_display(diff)
        self.view.set_info(status)
        self.view.show_diff()
        qtutils.set_clipboard(filename)

    def mergetool(self):
        filename = self.get_selected_filename(staged=False)
        if not filename or filename not in self.model.get_unmerged():
            return
        utils.fork('xterm', '-e',
                   'git', 'mergetool',
                   '-t', self.model.get_mergetool(),
                   '--', filename)

    def edit_file(self, staged=True):
        filename = self.get_selected_filename(staged=staged)
        if filename:
            utils.fork(self.model.get_editor(), filename)

    def edit_diff(self, staged=True):
        filename = self.get_selected_filename(staged=staged)
        if filename:
            utils.fork('git', 'difftool', '--no-prompt',
                       '-t', self.model.get_mergetool(),
                       '--', filename)

    # use *rest to handle being called from different signals
    def diff_staged(self, *rest):
        self.view_diff(staged=True)

    # use *rest to handle being called from different signals
    def diff_unstaged(self, *rest):
        self.view_diff(staged=False)

    def export_patches(self):
        (revs, summaries) = self.model.log_helper()
        to_export = self.select_commits_gui('Export Patches', revs, summaries)
        if not to_export:
            return
        to_export.reverse()
        revs.reverse()
        self.log(self.model.format_patch_helper(to_export,
                                                revs,
                                                output='patches'))

    def open_repo(self):
        """Spawns a new cola session"""
        dirname = qtutils.opendir_dialog(self.view,
                                         'Open Git Repository...',
                                         os.getcwd())
        if dirname:
            utils.fork(sys.argv[0], dirname)

    def clone_repo(self):
        """Clones a git repository"""
        url, ok = qtutils.input('Path or URL to clone (Env. $VARS okay)')
        if not ok or not url:
            return
        url = os.path.expandvars(url)
        msg = 'Enter a directory name for the new repository'
        dirname = qtutils.new_dir_dialog(self.view, msg)
        while dirname and os.path.exists(dirname):
            qtutils.information('Directory Exists',
                                'Please enter a non-existent path name.')
            dirname = qtutils.new_dir_dialog(self.view, msg)
        if not dirname:
            return
        self.log(self.model.git.clone(url, dirname))
        utils.fork(sys.argv[0], dirname)

    def quit_app(self, *args):
        """Save config settings and cleanup any inotify threads."""

        if self.model.remember_gui_settings():
            self.model.save_gui_settings()
        qtutils.close_log_window()
        pattern = self.model.get_tmp_file_pattern()
        for filename in glob.glob(pattern):
            os.unlink(filename)
        if self.inotify_thread and self.inotify_thread.isRunning():
            self.inotify_thread.abort = True
            self.inotify_thread.wait()
        self.view.close()

    def load_commitmsg(self):
        file = qtutils.open_dialog(self.view,
                                   'Load Commit Message...',
                                   defaults.DIRECTORY)
        if file:
            defaults.DIRECTORY = os.path.dirname(file)
            slushy = utils.slurp(file)
            if slushy:
                self.model.set_commitmsg(slushy)

    def rebase(self):
        branch = choose_from_combo('Rebase Branch',
                                   self.view,
                                   self.model.get_local_branches())
        if not branch:
            return
        self.log(self.model.git.rebase(branch))

    def reset_mode(self):
        """Sets the mode to the default NONE mode."""
        self.mode = Controller.MODE_NONE

    def clear_and_rescan(self, *rest):
        """Clears the current commit message and rescans.
        This is called when the "new commit" radio button is clicked."""
        self.reset_mode()
        self.model.set_commitmsg('')
        self.rescan()

    def load_prev_msg_and_rescan(self, *rest):
        """Gets the previous commit message and rescans.
        This is called when the "amend commit" radio button is clicked."""
        # You can't do this in the middle of a merge
        if os.path.exists(self.model.git_repo_path('MERGE_HEAD')):
            self.view.reset_checkboxes()
            qtutils.information('Oops! Unmerged',
                                'You are in the middle of a merge.\n'
                                'You cannot amend while merging.')
        else:
            self.reset_mode()
            self.model.get_prev_commitmsg()
            self.rescan()

    # use *rest to handle being called from the checkbox signal
    def rescan(self, *rest):
        """Populates view widgets with results from 'git status.'"""

        # save entire selection
        unstaged = qtutils.get_selection_list(self.view.unstaged,
                                              self.model.get_unstaged())
        staged = qtutils.get_selection_list(self.view.staged,
                                            self.model.get_staged())

        scrollbar = self.view.display_text.verticalScrollBar()
        scrollvalue = scrollbar.value()
        mode = self.mode

        # get new values
        self.model.update_status(amend=self.view.amend_is_checked())

        # restore selection
        updated_unstaged = self.model.get_unstaged()
        updated_staged = self.model.get_staged()

        if mode == Controller.MODE_WORKTREE:
            for item in unstaged:
                if item in updated_unstaged:
                    idx = updated_unstaged.index(item)
                    item = self.view.unstaged.item(idx)
                    if item:
                        item.setSelected(True)
                        self.view.unstaged.setItemSelected(item, True)
                        self.view.unstaged.setCurrentItem(item)
                        self.view_diff(False)
                        scrollbar.setValue(scrollvalue)

        elif mode in (Controller.MODE_INDEX, Controller.MODE_AMEND):
            for item in staged:
                if item in updated_staged:
                    idx = updated_staged.index(item)
                    item = self.view.staged.item(idx)
                    if item:
                        item.setSelected(True)
                        self.view.staged.setItemSelected(item, True)
                        self.view.staged.setCurrentItem(item)
                        self.view_diff(True)
                        scrollbar.setValue(scrollvalue)

        # Update the title with the current branch
        self.view.setWindowTitle('%s [%s]' % (
                self.model.get_project(),
                self.model.get_currentbranch()))

        if not self.view.amend_is_checked():
            # Check if there's a message file in .git/
            if self.merge_msg_imported:
                return
            self.merge_msg_imported = True
            merge_msg_path = self.model.get_merge_message_path()
            if merge_msg_path is None:
                return
            self.model.load_commitmsg(merge_msg_path)

    def fetch(self):
        remote_action(self.model, self.view, 'Fetch')

    def push(self):
        remote_action(self.model, self.view, 'Push')

    def pull(self):
        remote_action(self.model, self.view, 'Pull')

    def show_diffstat(self):
        """Show the diffstat from the latest commit."""
        self.reset_mode()
        self.view.set_info('Diffstat')
        self.view.set_display(self.model.diffstat())

    def show_index(self):
        self.reset_mode()
        self.view.set_info('Index')
        self.view.set_display(self.model.diffindex())

    #####################################################################
    def difftool_branch(self):
        self.reset_mode()
        branch = choose_from_combo('Select Branch, Tag, or Commit-ish',
                                   self.view,
                                   ['HEAD^']
                                   + self.model.get_all_branches()
                                   + self.model.get_tags())
        if not branch:
            return
        zfiles_str = self.model.git.diff(branch, name_only=True, z=True)
        if not zfiles_str:
            qtutils.information('Nothing to do',
                                'git-cola did not find any changes.')
        files = zfiles_str.split('\0')
        filename = choose_from_list('Select File', self.view, files)
        if not filename:
            return
        utils.fork('git', 'difftool', '--no-prompt',
                   '-t', self.model.get_mergetool(),
                   '-c', branch,
                   '--', filename)

    #####################################################################
    # diff gui
    def diff_branch(self):
        branch = choose_from_combo('Select Branch, Tag, or Commit-ish',
                                   self.view,
                                   ['HEAD^']
                                   + self.model.get_all_branches()
                                   + self.model.get_tags())
        if not branch:
            return
        zfiles_str = self.model.git.diff(branch, name_only=True, z=True)
        files = zfiles_str.split('\0')
        filename = choose_from_list('Select File', self.view, files)
        if not filename:
            return
        status = ('Diff of "%s" between the work tree and %s'
                  % (filename, branch))

        diff = self.model.diff_helper(filename=filename,
                                      cached=False,
                                      reverse=True,
                                      branch=branch)
        self.view.set_display(diff)
        self.view.set_info(status)
        self.view.show_diff()

        # Set state machine to branch mode
        self.mode = Controller.MODE_BRANCH
        self.branch = branch
        self.filename = filename

    def process_diff_selection(self, items, widget,
                               cached=True, selected=False,
                               apply_to_worktree=False,
                               reverse=False):

        if self.mode == Controller.MODE_BRANCH:
            branch = self.branch
            filename = self.filename
            parser = utils.DiffParser(self.model,
                                      filename=filename,
                                      cached=False,
                                      branch=branch)
            offset, selection = self.view.diff_selection()
            parser.process_diff_selection(selected, offset, selection,
                                          apply_to_worktree=True)
            self.rescan()
        else:
            filename = qtutils.get_selected_item(widget, items)
            if not filename:
                return
            parser = utils.DiffParser(self.model,
                                      filename=filename,
                                      cached=cached,
                                      reverse=apply_to_worktree)
            offset, selection = self.view.diff_selection()
            parser.process_diff_selection(selected, offset, selection,
                                          apply_to_worktree=apply_to_worktree)
            self.rescan()

    def undo_hunk(self):
        if not qtutils.question(self.view,
                                'Destroy Local Changes?',
                                'This operation will drop '
                                'uncommitted changes.\n'
                                'Continue?',
                                default=False):
            return
        self.process_diff_selection(self.model.get_unstaged(),
                                    self.view.unstaged,
                                    apply_to_worktree=True,
                                    cached=False,
                                    reverse=True)

    def undo_selection(self):
        if not qtutils.question(self.view,
                                'Destroy Local Changes?',
                                'This operation will drop '
                                'uncommitted changes.\n'
                                'Continue?',
                                default=False):
            return
        self.process_diff_selection(self.model.get_unstaged(),
                                    self.view.unstaged,
                                    apply_to_worktree=True,
                                    cached=False,
                                    reverse=True,
                                    selected=True)

    def stage_hunk(self):
        self.process_diff_selection(self.model.get_unstaged(),
                                    self.view.unstaged,
                                    cached=False)

    def stage_hunk_selection(self):
        self.process_diff_selection(self.model.get_unstaged(),
                                    self.view.unstaged,
                                    cached=False,
                                    selected=True)

    def unstage_hunk(self, cached=True):
        self.process_diff_selection(self.model.get_staged(),
                                    self.view.staged,
                                    cached=True)

    def unstage_hunk_selection(self):
        self.process_diff_selection(self.model.get_staged(),
                                    self.view.staged,
                                    cached=True,
                                    selected=True)

    # #######################################################################
    # end diff gui

    # *rest handles being called from different signals
    def stage_selected(self,*rest):
        """Use "git add" to add items to the git index.
        This is a thin wrapper around map_to_listwidget."""
        command = self.model.add_or_remove
        widget = self.view.unstaged
        items = self.model.get_unstaged()
        self.map_to_listwidget(command, widget, items)

    # *rest handles being called from different signals
    def unstage_selected(self, *rest):
        """Use "git reset" to remove items from the git index.
        This is a thin wrapper around map_to_listwidget."""
        command = self.model.reset_helper
        widget = self.view.staged
        items = self.model.get_staged()
        self.map_to_listwidget(command, widget, items)

    def undo_changes(self):
        """Reverts local changes back to whatever's in HEAD."""
        widget = self.view.unstaged
        items = self.model.get_unstaged()
        potential_items = qtutils.get_selection_list(widget, items)
        items_to_undo = []
        untracked = self.model.get_untracked()
        for item in potential_items:
            if item not in untracked:
                items_to_undo.append(item)
        if items_to_undo:
            if not qtutils.question(self.view,
                                    'Destroy Local Changes?',
                                    'This operation will drop '
                                    'uncommitted changes.\n'
                                    'Continue?',
                                    default=False):
                return

            output = self.model.git.checkout('HEAD', '--', *items_to_undo)
            self.log('git checkout HEAD -- '
                    +' '.join(items_to_undo)
                    +'\n' + output)
        else:
            msg = 'No files selected for checkout from HEAD.'
            self.log(self.tr(msg))

    def viz_all(self):
        """Visualizes the entire git history using gitk."""
        browser = self.model.get_history_browser()
        utils.fork(browser, '--all')

    def viz_current(self):
        """Visualizes the current branch's history using gitk."""
        browser = self.model.get_history_browser()
        utils.fork(browser, self.model.get_currentbranch())

    def move_event(self, event):
        defaults.X = event.pos().x()
        defaults.Y = event.pos().y()

    def resize_event(self, event):
        defaults.WIDTH = event.size().width()
        defaults.HEIGHT = event.size().height()

    def load_gui_settings(self):
        try:
            (w,h,x,y) = self.model.get_window_geom()
            self.view.resize(w,h)
            self.view.move(x,y)
        except:
            pass

    def log(self, output, rescan=True, quiet=False):
        """Logs output and optionally rescans for changes."""
        qtutils.log(output, quiet=quiet, doraise=False)
        if rescan:
            self.rescan()

    def map_to_listwidget(self, command, widget, items):
        """This is a helper method that retrieves the current
        selection list, applies a command to that list,
        displays a dialog showing the output of that command,
        and calls rescan to pickup changes."""
        apply_items = qtutils.get_selection_list(widget, items)
        output = command(*apply_items)
        self.log(output, quiet=True)

    def staged_context_menu_event(self, event):
        menu = self.staged_context_menu_setup()
        staged = self.view.staged
        menu.exec_(staged.mapToGlobal(event.pos()))

    def staged_context_menu_setup(self):
        staged_item = qtutils.get_selected_item(self.view.staged,
                                                self.model.get_staged())
        menu = QMenu(self.view)
        menu.addAction(self.tr('Unstage Selected'), self.unstage_selected)
        menu.addSeparator()
        menu.addAction(self.tr('Launch Editor'),
                       lambda: self.edit_file(staged=True))
        menu.addAction(self.tr('Launch Merge Tool'),
                       lambda: self.edit_diff(staged=True))
        return menu

    def unstaged_context_menu_event(self, event):
        menu = self.unstaged_context_menu_setup()
        unstaged = self.view.unstaged
        menu.exec_(unstaged.mapToGlobal(event.pos()))

    def unstaged_context_menu_setup(self):
        unstaged_item = qtutils.get_selected_item(self.view.unstaged,
                                                  self.model.get_unstaged())
        is_tracked = unstaged_item not in self.model.get_untracked()
        is_unmerged = unstaged_item in self.model.get_unmerged()
        enable_staging = self.mode == Controller.MODE_WORKTREE
        enable_undo = enable_staging and is_tracked

        menu = QMenu(self.view)
        if enable_staging:
            menu.addAction(self.tr('Stage Selected'), self.stage_selected)
            menu.addSeparator()
        if is_unmerged and not utils.is_broken():
            menu.addAction(self.tr('Resolve Merge'), self.mergetool)

        menu.addAction(self.tr('Launch Editor'),
                       lambda: self.edit_file(staged=False))
        if enable_staging:
            menu.addAction(self.tr('Launch Merge Tool'),
                           lambda: self.edit_diff(staged=False))
        if enable_undo:
            menu.addSeparator()
            menu.addAction(self.tr('Undo All Changes'), self.undo_changes)
        return menu

    def diff_context_menu_event(self, event):
        menu = self.diff_context_menu_setup()
        textedit = self.view.display_text
        menu.exec_(textedit.mapToGlobal(event.pos()))

    def diff_context_menu_setup(self):
        menu = QMenu(self.view)

        if self.mode == Controller.MODE_WORKTREE:
            unstaged_item =\
                qtutils.get_selected_item(self.view.unstaged,
                                          self.model.get_unstaged())
            is_tracked= (unstaged_item
                         and unstaged_item not in self.model.get_untracked())
            is_unmerged = (unstaged_item
                           and unstaged_item in self.model.get_unmerged())
            if is_tracked and not is_unmerged:
                menu.addAction(self.tr('Stage Hunk For Commit'),
                               self.stage_hunk)
                menu.addAction(self.tr('Stage Selected Lines'),
                               self.stage_hunk_selection)
                menu.addSeparator()
                menu.addAction(self.tr('Undo Hunk'), self.undo_hunk)
                menu.addAction(self.tr('Undo Selection'), self.undo_selection)

        elif self.mode == Controller.MODE_INDEX:
            menu.addAction(self.tr('Unstage Hunk From Commit'), self.unstage_hunk)
            menu.addAction(self.tr('Unstage Selected Lines'), self.unstage_hunk_selection)

        elif self.mode == Controller.MODE_BRANCH:
            menu.addAction(self.tr('Apply Diff to Work Tree'), self.stage_hunk)
            menu.addAction(self.tr('Apply Diff Selection to Work Tree'), self.stage_hunk_selection)

        elif self.mode == Controller.MODE_GREP:
            menu.addAction(self.tr('Go Here'), self.goto_grep)

        menu.addSeparator()
        menu.addAction(self.tr('Copy'), self.view.copy_display)
        return menu

    def select_commits_gui(self, title, revs, summaries):
        return select_commits(self.model, self.view,
                              self.tr(title), revs, summaries)

    def update_diff_font(self):
        font = self.model.get_cola_config('fontdiff')
        if not font:
            return
        qfont = QFont()
        qfont.fromString(font)
        self.view.display_text.setFont(qfont)
        self.view.commitmsg.setFont(qfont)

    def update_ui_font(self):
        font = self.model.get_cola_config('fontui')
        if not font:
            return
        qfont = QFont()
        qfont.fromString(font)
        QtGui.qApp.setFont(qfont)

    def init_log_window(self):
        branch = self.model.get_currentbranch()
        qtutils.log(self.model.get_git_version()
                   +'\ncola version '+ version.version
                   +'\nCurrent Branch: '+ branch)

    def start_inotify_thread(self):
        # Do we have inotify?  If not, return.
        # Recommend installing inotify if we're on Linux.
        self.inotify_thread = None
        try:
            from cola.inotify import GitNotifier
            qtutils.log(self.tr('inotify support: enabled'))
        except ImportError:
            if utils.is_linux():
                msg = self.tr('inotify: disabled\n'
                              'Note: To enable inotify, '
                              'install python-pyinotify.\n')

                if utils.is_debian():
                    msg += self.tr('On Debian systems, '
                                   'try: sudo apt-get install '
                                   'python-pyinotify')
                qtutils.log(msg)
            return

        # Start the notification thread
        self.inotify_thread = GitNotifier(self, os.getcwd())
        self.inotify_thread.start()
