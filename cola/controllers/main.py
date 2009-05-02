"""This module provides access to the application controllers."""

import os
import sys
import glob

from PyQt4 import QtGui

from cola import core
from cola import utils
from cola import qtutils
from cola import version
from cola import inotify
from cola import difftool
from cola import resources
from cola import settings
from cola.qobserver import QObserver
from cola.views import about
from cola.views import drawer

# controllers namespace
from cola.controllers.bookmark import save_bookmark
from cola.controllers.bookmark import manage_bookmarks
from cola.controllers.compare import compare
from cola.controllers.compare import compare_file
from cola.controllers.compare import branch_compare
from cola.controllers.createbranch import create_new_branch
from cola.controllers.log import logger
from cola.controllers.merge import local_merge
from cola.controllers.merge import abort_merge
from cola.controllers.options import update_options
from cola.controllers.remote import remote_action
from cola.controllers.repobrowser import browse_git_branch
from cola.controllers import search
from cola.controllers.search import search_commits
from cola.controllers.selectcommits import select_commits
from cola.controllers.stash import stash
from cola.controllers.util import choose_from_list
from cola.controllers.util import choose_from_combo

class MainController(QObserver):
    """Manages the interaction between models and views."""

    # Default: nothing's happened, do nothing
    MODE_NONE = 0

    # Comparing index to worktree
    MODE_WORKTREE = 1

    # Comparing index to last commit
    MODE_INDEX = 2

    # Amending a commit
    MODE_AMEND = 3

    # Applying changes from a branch
    MODE_BRANCH = 4

    # We ran Search -> Grep
    MODE_GREP = 5

    # Diffing against an arbitrary branch
    MODE_DIFF = 6

    # Reviewing a branch
    MODE_REVIEW = 7

    # Modes where we don't do anything like staging, etc.
    MODES_READ_ONLY = (MODE_BRANCH, MODE_GREP,
                       MODE_DIFF, MODE_REVIEW)

    # Modes where we can checkout files from the $head
    MODES_UNDOABLE = (MODE_NONE, MODE_INDEX, MODE_WORKTREE)

    def __init__(self, model, view):
        """
        Initializes the MainController's internal data
        """
        QObserver.__init__(self, model, view)

        # TODO: subclass model
        model.project = os.path.basename(model.git.get_work_tree())
        model.git_version = model.git.version()

        self.reset_mode()

        # Parent-less log window
        qtutils.LOGGER = logger(model, view)
        view.centralWidget().add_bottom_drawer(qtutils.LOGGER.view)

        # Unstaged changes context menu
        view.status_tree.contextMenuEvent = self.tree_context_menu_event

        # Diff display context menu
        view.display_text.contextMenuEvent = self.diff_context_menu_event

        # What to compare against by default
        self.head = 'HEAD'

        # Binds model params to their equivalent view widget
        self.add_observables('commitmsg')

        # When a model attribute changes, this runs a specific action
        self.add_actions(global_cola_fontdiff = self.update_diff_font)
        self.add_actions(global_cola_fontui = self.update_ui_font)
        self.add_actions(global_cola_tabwidth = self.update_tab_width)

        self.add_callbacks(
            # Push Buttons
            rescan_button = self.rescan,
            signoff_button = self.model.add_signoff,
            stage_button = self.stage_selected,
            stash_button = lambda: stash(self.model, self.view),
            commit_button = self.commit,
            fetch_button = self.fetch,
            push_button = self.push,
            pull_button = self.pull,
            alt_button = self.alt_action,
            # Checkboxes
            amend_radio = self.load_prev_msg_and_rescan,
            new_commit_radio = self.clear_and_rescan,

            # File Menu
            menu_quit = self.quit_app,
            menu_open_repo = self.open_repo,
            menu_clone_repo = self.clone_repo,
            menu_manage_bookmarks = manage_bookmarks,
            menu_save_bookmark = save_bookmark,
            menu_load_commitmsg = self.load_commitmsg,
            menu_get_prev_commitmsg = model.get_prev_commitmsg,
            menu_load_commitmsg_template = model.load_commitmsg_template,

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
            menu_branch_compare = self.branch_compare,
            menu_branch_diff = self.branch_diff,
            menu_branch_review = self.branch_review,

            # Commit Menu
            menu_rescan = self.rescan,
            menu_delete_branch = self.branch_delete,
            menu_rebase_branch = self.rebase,
            menu_stage_selected = self.stage_selected,
            menu_unstage_selected = self.unstage_selected,
            menu_show_diffstat = self.show_diffstat,
            menu_show_index = self.show_index,
            menu_export_patches = self.export_patches,
            menu_cherry_pick = self.cherry_pick,
            menu_stash =
                lambda: stash(self.model, self.view),
            menu_commit_compare =
                lambda: compare(self.model, self.view),
            menu_commit_compare_file =
                lambda: compare_file(self.model, self.view),
            menu_stage_modified =
                lambda: self.log(*self.model.stage_modified()),
            menu_stage_untracked =
                lambda: self.log(*self.model.stage_untracked()),
            menu_unstage_all =
                lambda: self.log(*self.model.unstage_all()),
            menu_view_log = self.view.display_log,

            # Help Menu
            menu_help_about = lambda: about.launch_about_dialog(self.view),
            menu_help_docs =
                lambda: self.model.git.web__browse(resources.html_docs()),
            )

        # Route events here
        view.closeEvent = self.quit_app
        view.status_tree.mousePressEvent = self.click_tree
        self.connect(view.status_tree,
                     'itemDoubleClicked(QTreeWidgetItem*, int)',
                     self.doubleclick_tree)

        # A hash of the merge message so we don't keep prompting to import it
        self.merge_msg_hash = ''

        # Loads the saved gui state from .cola
        self._load_gui_state()

        # Do an initial scan to initialize the repo status tree
        self.rescan()

        # Initializes the log subwindow
        self._init_log_window()

        # Updates the main UI fonts
        self.refresh_view('global_cola_fontdiff', 'global_cola_fontui')

        self.start_inotify_thread()
        if self.has_inotify():
            self.view.rescan_button.hide()

    #####################################################################
    # handle when the status tree is clicked
    def get_staged_item(self):
        """Returns a single selected staged item"""
        staged = self.model.get_staged()
        staged = self.view.get_staged(staged)
        if staged:
            return staged[0]
        else:
            return None

    def get_untracked_items(self):
        """Returns all selected untracked items"""
        items = self.model.get_untracked()
        return self.view.get_untracked(items)

    def get_unstaged_item(self):
        """Returns a single selected unstaged item"""
        unstaged = self.model.get_unstaged()
        unstaged = self.view.get_unstaged(unstaged)
        if unstaged:
            return unstaged[0]
        else:
            return None

    def get_selection(self):
        """Returns the current selection in the repo status tree"""
        staged = self.model.get_staged()
        staged = self.view.get_staged(staged)

        modified = self.model.get_modified()
        modified = self.view.get_modified(modified)

        unmerged = self.model.get_unmerged()
        unmerged = self.view.get_unmerged(unmerged)

        untracked = self.model.get_untracked()
        untracked = self.view.get_untracked(untracked)

        return (staged, modified, unmerged, untracked)

    def get_single_selection(self):
        """Scans across staged, modified, etc. and a single item only
        """
        staged, modified, unmerged, untracked = self.get_selection()
        s = None
        m = None
        um = None
        ut = None
        if staged:
            s = staged[0]
        elif modified:
            m = modified[0]
        elif unmerged:
            um = unmerged[0]
        elif untracked:
            ut = untracked[0]
        return s, m, um, ut

    def doubleclick_tree(self, item, column):
        """Called when an item is double-clicked in the repo status tree"""
        if self.read_only():
            return
        staged, modified, unmerged, untracked = self.get_selection()
        if staged:
            self.log(*self.model.reset_helper(staged))
        elif modified:
            self.log(*self.model.add_or_remove(modified))
        elif untracked:
            self.log(*self.model.add_or_remove(untracked))
        elif unmerged:
            self.log(*self.model.add_or_remove(unmerged))
        else:
            return
        self.rescan()

    def click_tree(self, event):
        """
        Called when a repo status tree item is clicked

        This handles the behavior where clicking on the icon invokes
        the same appropriate action.
        """
        # Get the item that was clicked
        tree = self.view.status_tree
        result = QtGui.QTreeWidget.mousePressEvent(tree, event)
        item = tree.itemAt(event.pos())
        if not item:
            # Nothing was clicked -- reset the display and return
            if not self.read_only():
                self.reset_mode()
            self.view.reset_display()
            items = self.view.status_tree.selectedItems()
            for i in items:
                i.setSelected(False)
            return result
        parent = item.parent()
        if not parent:
            # We clicked on a heading such as 'Staged'
            idx = self.view.status_tree.indexOfTopLevelItem(item)
            diff = 'no diff'
            if (self.mode == self.MODE_REVIEW and idx == self.view.IDX_STAGED):
                # Run diff without --cached when in review mode
                diff = (self.model.git.diff(self.head,
                                            no_color=True, stat=True,
                                            M=True,
                                            with_raw_output=True) +
                        '\n\n' +
                        self.model.git.diff(self.head, no_color=True))
            elif idx == self.view.IDX_STAGED:
                # Show a diffstat when clicking on the 'Staged' heading
                diff = (self.model.git.diff(cached=True, stat=True,
                                            M=True,
                                            no_color=True,
                                            with_raw_output=True) + '\n\n' +
                        self.model.git.diff(cached=True))
            elif idx == self.view.IDX_MODIFIED:
                # Show a diffstat when clicking on the 'Modified' heading
                diff = (self.model.git.diff(stat=True,
                                            M=True,
                                            no_color=True,
                                            with_raw_output=True) + '\n\n' +
                        self.model.git.diff(no_color=True))
            elif idx == self.view.IDX_UNMERGED:
                # List unmerged files when clicking on the 'Unmerged' heading
                diff = '%s unmerged file(s)' % len(self.model.get_unmerged())
            elif idx == self.view.IDX_UNTRACKED:
                # We click on the untracked heading so helpfully list
                # possible .gitignore rules
                untracked = self.model.get_untracked()
                suffix = len(untracked) > 1 and '(s)' or ''
                diff = '# %s untracked file%s\n' % (len(untracked), suffix)
                if untracked:
                    diff += '# possible .gitignore rule%s:\n' % suffix
                    for u in untracked:
                        diff += '/'+ u + '\n'
                    diff + '\n'
            self.view.set_display(diff)
            return result
        # An item was clicked -- show a diff or other information about it
        staged, idx = self.view.get_index_for_item(item)
        if idx == -1:
            return result
        self._view_diff_for_row(idx, staged)
        if self.read_only():
            return result
        # handle when the icons are clicked
        xpos = event.pos().x()
        if xpos > 42 and xpos < 58:
            if staged:
                # A staged item was clicked
                items = self.model.get_staged()
                selected = self.view.get_staged(items)
                self.log(*self.model.reset_helper(selected))
                self.rescan()
            else:
                # An unstaged item was clicked
                items = self.model.get_unstaged()
                selected = self.view.get_unstaged(items)
                if selected:
                    self.log(*self.model.add_or_remove(selected))
                items = self.model.get_unmerged()
                selected = self.view.get_unmerged(items)
                if selected:
                    self.log(*self.model.add_or_remove(selected))
                self.rescan()
        return result

    #####################################################################
    def event(self, msg):
        """Overrides event() to handle custom inotify events"""
        if not inotify.AVAILABLE:
            return
        if msg.type() == inotify.INOTIFY_EVENT:
            self.rescan()
            return True
        else:
            return False

    #####################################################################
    # Actions triggered during model updates
    def action_staged(self, widget):
        """Called when the 'staged' list changes"""
        qtutils.update_file_icons(widget,
                                  self.model.get_staged(),
                                  staged=True)
        self.view.show_editor()

    def action_unstaged(self, widget):
        """Called when the 'unstaged' list changes"""
        modified = self.model.get_modified()
        unmerged = self.model.get_unmerged()
        unstaged = modified + unmerged
        qtutils.update_file_icons(widget,
                                  unstaged,
                                  staged=False)
        if self.model.get_show_untracked():
            qtutils.update_file_icons(widget,
                                      self.model.get_untracked(),
                                      staged=False,
                                      untracked=True,
                                      offset=len(unstaged))

    #####################################################################
    # Qt callbacks
    def tr(self, fortr):
        """Translates strings"""
        return qtutils.tr(fortr)

    def read_only(self):
        """Whether we should inhibit all repo-modifying actions"""
        return self.mode in self.MODES_READ_ONLY

    def undoable(self):
        """Whether we can checkout files from the $head"""
        return self.mode in self.MODES_UNDOABLE

    def goto_grep(self):
        """Called when Search -> Grep's right-click 'goto' action"""
        line = self.view.selected_line()
        filename, lineno, contents = line.split(':', 2)
        if not os.path.exists(filename):
            return
        editor = self.model.get_editor()
        if 'vi' in editor:
            utils.fork([self.model.get_editor(), filename, '+'+lineno])
        else:
            utils.fork([self.model.get_editor(), filename])

    def gen_search(self, searchtype, browse=False):
        """Returns a callback to handle the various search actions"""
        def search_handler():
            search_commits(self.model, self.view, searchtype, browse)
        return search_handler

    def grep(self):
        """Prompts for input and uses 'git grep' to find the content"""
        txt, ok = qtutils.input('grep')
        if not ok:
            return
        self.mode = self.MODE_GREP
        stuff = self.model.git.grep(txt, n=True)
        self.view.display_text.setText(stuff)
        self.view.show_diff()

    def options(self):
        """Launches the options dialog"""
        update_options(self.model, self.view)

    def branch_create(self):
        """Launches the 'Create Branch' dialog"""
        create_new_branch(self.model, self.view)

    def branch_delete(self):
        """Launches the 'Delete Branch' dialog"""
        branch = choose_from_combo('Delete Branch',
                                   self.view,
                                   self.model.get_local_branches())
        if not branch:
            return
        self.log(*self.model.delete_branch(branch))

    def browse_current(self):
        """Launches the 'Browse Current Branch' dialog"""
        branch = self.model.get_currentbranch()
        browse_git_branch(self.model, self.view, branch)

    def browse_other(self):
        """Prompts for a branch and inspects content at that point in time"""
        # Prompt for a branch to browse
        branch = choose_from_combo('Browse Branch Files',
                                   self.view,
                                   self.model.get_all_branches())
        if not branch:
            return
        # Launch the repobrowser
        browse_git_branch(self.model, self.view, branch)

    def checkout_branch(self):
        """Launches the 'Checkout Branch' dialog"""
        branch = choose_from_combo('Checkout Branch',
                                   self.view,
                                   self.model.get_local_branches())
        if not branch:
            return
        self.log(*self.model.git.checkout(branch,
                                          with_stderr=True,
                                          with_status=True))

    def browse_commits(self):
        """Launches the 'Browse Commits' dialog"""
        self.select_commits_gui('Browse Commits',
                                *self.model.log_helper(all=True))

    def cherry_pick(self):
        """Launches the 'Cherry-Pick' dialog"""
        commits = self.select_commits_gui('Cherry-Pick Commits',
                                          *self.model.log_helper(all=True))
        if not commits:
            return
        self.log(*self.model.cherry_pick_list(commits))

    def commit(self):
        """Attempts to create a commit from the index and commit message
        """
        self.reset_mode()
        self.head = 'HEAD'
        msg = self.model.get_commitmsg()
        if not msg:
            # Describe a good commit message
            error_msg = self.tr(''
                'Please supply a commit message.\n\n'
                'A good commit message has the following format:\n\n'
                '- First line: Describe in one sentence what you did.\n'
                '- Second line: Blank\n'
                '- Remaining lines: Describe why this change is good.\n')
            qtutils.log(1, error_msg)
            return
        files = self.model.get_staged()
        if not files and not self.view.amend_is_checked():
            error_msg = self.tr(''
                'No changes to commit.\n\n'
                'You must stage at least 1 file before you can commit.\n')
            qtutils.log(1, error_msg)
            return
        # Warn that amending published commits is generally bad
        amend = self.view.amend_is_checked()
        if (amend and self.model.is_commit_published() and
            not qtutils.question(self.view,
                                 'Rewrite Published Commit?',
                                 'This commit has already been published.\n'
                                 'You are rewriting published history.\n'
                                 'You probably don\'t want to do this.\n\n'
                                 'Continue?',
                                 default=False)):
            return
        # Perform the commit
        umsg = core.encode(msg)
        status, output = self.model.commit_with_msg(umsg, amend=amend)
        if status == 0:
            self.view.reset_checkboxes()
            self.model.set_commitmsg('')
        self.log(status, output)

    def get_selected_filename(self, staged=False):
        """Returns the selected staged or unstaged filename"""
        if staged:
            return self.get_staged_item()
        else:
            return self.get_unstaged_item()

    def set_mode(self, staged):
        """Sets the appropriate mode based on the staged/amending state"""
        if self.read_only():
            return
        if staged:
            if self.view.amend_is_checked():
                self.mode = self.MODE_AMEND
            else:
                self.mode = self.MODE_INDEX
        else:
            self.mode = self.MODE_WORKTREE

    def view_diff(self, staged=True, scrollvalue=None):
        """Views the diff for a clicked-on item"""
        idx, selected = self.view.get_selection()
        if not selected:
            self.reset_mode()
            self.view.reset_display()
            return
        self._view_diff_for_row(idx, staged)
        if scrollvalue is not None:
            scrollbar = self.view.display_text.verticalScrollBar()
            scrollbar.setValue(scrollvalue)

    def _view_diff_for_row(self, idx, staged):
        """Views the diff for a specific row"""
        self.set_mode(staged)
        ref = self.head
        diff, filename = self.model.get_diff_details(idx, ref, staged=staged)
        self.view.set_display(diff)
        self.view.show_diff()
        qtutils.set_clipboard(filename)

    def mergetool(self):
        """Launches git-mergetool on a file path"""
        filename = self.get_selected_filename(staged=False)
        if not filename or filename not in self.model.get_unmerged():
            return
        if version.check('mergetool-no-prompt',
                         self.model.git.version().split()[2]):
            utils.fork(['git', 'mergetool', '--no-prompt', '--', filename])
        else:
            utils.fork(['xterm', '-e', 'git', 'mergetool', '--', filename])

    def edit_file(self, staged=True):
        """Launches $editor on a specific path"""
        filename = self.get_selected_filename(staged=staged)
        if filename:
            utils.fork([self.model.get_editor(), filename])

    def edit_diff(self, staged=True):
        """Launches difftool on the specified paths"""
        filename = self.get_selected_filename(staged=staged)
        if filename:
            args = []
            if staged and not self.read_only():
                args.append('--cached')
            args.extend([self.head, '--', filename])
            difftool.launch(args)

    def delete_files(self, staged=False):
        """Deletes files when called by an untracked file's context menu"""
        rescan=False
        filenames = self.get_untracked_items()
        for filename in filenames:
            if filename:
                try:
                    os.remove(filename)
                except Exception:
                    qtutils.log(1, self.tr('Error deleting "%s"') % filename)
                else:
                    rescan=True
        if rescan:
            self.rescan()

    # use *rest to handle being called from different signals
    def diff_staged(self, *rest):
        """Shows the diff for a staged item"""
        self.view_diff(staged=True)

    # use *rest to handle being called from different signals
    def diff_unstaged(self, *rest):
        """Shows the diff for an unstaged item"""
        self.view_diff(staged=False)

    def export_patches(self):
        """Runs 'git format-patch' on a list of commits"""
        revs, summaries = self.model.log_helper()
        to_export = self.select_commits_gui('Export Patches', revs, summaries)
        if not to_export:
            return
        to_export.reverse()
        revs.reverse()
        qtutils.log(*self.model.format_patch_helper(to_export, revs,
                                                    output='patches'))

    def _quote_repopath(self, repopath):
        """Quotes a path for nt/dos only"""
        if os.name in ('nt', 'dos'):
            repopath = '"%s"' % repopath
        return repopath

    def open_repo(self):
        """Spawns a new cola session"""
        dirname = qtutils.opendir_dialog(self.view,
                                         'Open Git Repository...',
                                         os.getcwd())
        if not dirname:
            return
        utils.fork(['python', sys.argv[0],
                    '--repo', self._quote_repopath(dirname)])

    def clone_repo(self):
        """Clones a git repository"""
        url, ok = qtutils.input('Path or URL to clone (Env. $VARS okay)')
        url = os.path.expandvars(url)
        if not ok or not url:
            return
        try:
            # Pick a suitable basename by parsing the URL
            newurl = url.replace('\\', '/')
            default = newurl.rsplit('/', 1)[-1]
            if default == '.git':
                # The end of the URL is /.git, so assume it's a file path
                default = os.path.basename(os.path.dirname(newurl))
            if default.endswith('.git'):
                # The URL points to a bare repo
                default = default[:-4]
            if url == '.':
                # The URL is the current repo
                default = os.path.basename(os.getcwd())
            if not default:
                raise
        except:
            qtutils.log(1, 'Oops, could not parse git url: "%s"' % url)
            return

        # Prompt the user for a directory to use as the parent directory
        msg = 'Select a parent directory for the new clone'
        dirname = qtutils.opendir_dialog(self.view, msg, os.getcwd())
        if not dirname:
            return
        count = 1
        destdir = os.path.join(dirname, default)
        olddestdir = destdir
        if os.path.exists(destdir):
            # An existing path can be specified
            qtutils.information(destdir + ' already exists, cola will '
                                'create a new directory')

        # Make sure the new destdir doesn't exist
        while os.path.exists(destdir):
            destdir = olddestdir + str(count)
            count += 1

        # Run 'git clone' into the destdir
        qtutils.log(*self.model.git.clone(url, destdir,
                                          with_stderr=True,
                                          with_status=True))
        # Run git-cola on the new repo
        utils.fork(['python', sys.argv[0],
                    '--repo', self._quote_repopath(destdir)])

    def has_inotify(self):
        """Returns True on Linux systems that have pyinotify installed"""
        return self.inotify_thread and self.inotify_thread.isRunning()

    def quit_app(self, *args):
        """Save config settings and cleanup any inotify threads."""
        if self.model.remember_gui_settings():
            settings.SettingsManager.save_gui_state(self.view)

        # Remove any cola temp files
        pattern = self.model.get_tmp_file_pattern()
        for filename in glob.glob(pattern):
            os.unlink(filename)

        # Stop inotify threads
        if self.has_inotify():
            self.inotify_thread.abort = True
            self.inotify_thread.terminate()
            self.inotify_thread.wait()
        self.view.close()

    def load_commitmsg(self):
        """Loads a commit message from a file"""
        filename = qtutils.open_dialog(self.view,
                                       'Load Commit Message...',
                                       self.model.get_directory())
        if filename:
            self.model.set_directory(os.path.dirname(filename))
            slushy = utils.slurp(filename)
            if slushy:
                self.model.set_commitmsg(slushy)

    def rebase(self):
        """Rebases onto a branch"""
        branch = choose_from_combo('Rebase Branch',
                                   self.view,
                                   self.model.get_all_branches())
        if not branch:
            return
        self.log(*self.model.git.rebase(branch,
                                        with_stderr=True,
                                        with_status=True))

    def reset_mode(self):
        """Sets the mode to the default NONE mode."""
        self.mode = self.MODE_NONE

    def clear_and_rescan(self, *rest):
        """Clears the current commit message and rescans.
        This is called when the "new commit" radio button is clicked."""
        self.reset_mode()
        self.head = 'HEAD'
        self.model.set_commitmsg('')
        self.view.alt_button.hide()
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
            self.head = 'HEAD^'
            self.model.get_prev_commitmsg()
            self.rescan()

    # use *rest to handle being called from the checkbox signal
    def rescan(self, *rest):
        """Populates view widgets with results from 'git status.'"""

        # save entire selection
        staged = self.view.get_staged(self.model.get_staged())
        modified = self.view.get_modified(self.model.get_modified())
        unmerged = self.view.get_unmerged(self.model.get_unmerged())
        untracked = self.view.get_untracked(self.model.get_untracked())

        # unstaged is an aggregate
        unstaged = modified + unmerged + untracked

        scrollbar = self.view.display_text.verticalScrollBar()
        scrollvalue = scrollbar.value()
        mode = self.mode

        # get new values
        self.model.update_status(head=self.head, staged_only=self.read_only())

        # Setup initial tree items
        if self.read_only():
            self.view.set_staged(self.model.get_staged(), check=False)
            self.view.set_modified([])
            self.view.set_unmerged([])
            self.view.set_untracked([])
        else:
            self.view.set_staged(self.model.get_staged())
            self.view.set_modified(self.model.get_modified())
            self.view.set_unmerged(self.model.get_unmerged())
            self.view.set_untracked(self.model.get_untracked())

        # restore selection
        updated_staged = self.model.get_staged()
        updated_modified = self.model.get_modified()
        updated_unmerged = self.model.get_unmerged()
        updated_untracked = self.model.get_untracked()
        # unstaged is an aggregate
        updated_unstaged = (updated_modified +
                            updated_unmerged +
                            updated_untracked)

        # Updating the status resets the repo status tree so
        # restore the selected items and re-run the diff
        showdiff = False
        if mode == self.MODE_WORKTREE:
            # Update unstaged items
            if unstaged:
                for item in unstaged:
                    if item in updated_unstaged:
                        idx = updated_unstaged.index(item)
                        item = self.view.get_unstaged_item(idx)
                        if item:
                            showdiff = True
                            item.setSelected(True)
                            self.view.status_tree.setCurrentItem(item)
                            self.view.status_tree.setItemSelected(item, True)
                if showdiff:
                    self.view_diff(staged=False, scrollvalue=scrollvalue)
                else:
                    self.reset_mode()
                    self.view.reset_display()

        elif mode in (self.MODE_INDEX, self.MODE_AMEND):
            # Ditto for staged items
            if staged:
                for item in staged:
                    if item in updated_staged:
                        idx = updated_staged.index(item)
                        item = self.view.get_staged_item(idx)
                        if item:
                            showdiff = True
                            item.setSelected(True)
                            self.view.status_tree.setCurrentItem(item)
                            self.view.status_tree.setItemSelected(item, True)
                if showdiff:
                    self.view_diff(staged=True, scrollvalue=scrollvalue)
                else:
                    self.reset_mode()
                    self.view.reset_display()

        # Update the title with the current branch
        self._update_window_title()

        if not self.view.amend_is_checked():
            # Check if there's a message file in .git/
            merge_msg_path = self.model.get_merge_message_path()
            if merge_msg_path is None:
                return
            merge_msg_hash = self.model.git.hash_object(merge_msg_path)
            if merge_msg_hash == self.merge_msg_hash:
                return
            self.merge_msg_hash = merge_msg_hash
            self.model.load_commitmsg(merge_msg_path)

    def _update_window_title(self):
        """Updates the title with the current branch and other info"""
        title = '%s [%s]' % (self.model.get_project(),
                             self.model.get_currentbranch())
        if self.mode == self.MODE_DIFF:
            title += ' *** diff mode***'
        if self.mode == self.MODE_REVIEW:
            title += ' *** review mode***'
        self.view.setWindowTitle(title)

    def alt_action(self):
        if self.mode in self.MODES_READ_ONLY:
            self.clear_and_rescan()

    def fetch(self):
        remote_action(self.model, self.view, 'fetch')

    def push(self):
        remote_action(self.model, self.view, 'push')

    def pull(self):
        remote_action(self.model, self.view, 'pull')

    def show_diffstat(self):
        """Show the diffstat from the latest commit."""
        self.reset_mode()
        self.view.set_display(self.model.diffstat())

    def show_index(self):
        """Shows a diffstat for the current index state"""
        self.reset_mode()
        self.view.set_display(self.model.diffindex())

    #####################################################################
    def branch_compare(self):
        """Launches the Branch -> Compare dialog"""
        self.reset_mode()
        branch_compare(self.model, self.view)

    #####################################################################
    # diff gui
    def branch_diff(self):
        """Diff against an arbitrary revision, branch, tag, etc"""
        branch = choose_from_combo('Select Branch, Tag, or Commit-ish',
                                   self.view,
                                   ['HEAD^']
                                   + self.model.get_all_branches()
                                   + self.model.get_tags())
        if not branch:
            return
        self.mode = self.MODE_DIFF
        self.head = branch
        self.view.alt_button.setText(self.tr('Exit Diff Mode'))
        self.view.alt_button.show()
        self.rescan()

    def branch_review(self):
        """Diff against an arbitrary revision, branch, tag, etc"""
        branch = choose_from_combo('Select Branch, Tag, or Commit-ish',
                                   self.view,
                                   self.model.get_all_branches()
                                   + self.model.get_tags())
        if not branch:
            return
        self.mode = self.MODE_REVIEW
        self.head = '...'+branch
        self.view.alt_button.setText(self.tr('Exit Review Mode'))
        self.view.alt_button.show()
        self.rescan()

    def diff_branch(self):
        """Launches a diff against a branch"""
        branch = choose_from_combo('Select Branch, Tag, or Commit-ish',
                                   self.view,
                                   ['HEAD^']
                                   + self.model.get_all_branches()
                                   + self.model.get_tags())
        if not branch:
            return
        zfiles_str = self.model.git.diff(branch, name_only=True,
                                         no_color=True,
                                         z=True).rstrip('\0')
        files = zfiles_str.split('\0')
        filename = choose_from_list('Select File', self.view, files)
        if not filename:
            return
        diff = self.model.diff_helper(filename=filename,
                                      cached=False,
                                      reverse=True,
                                      branch=branch)
        self.view.set_display(diff)
        self.view.show_diff()

        # Set state machine to branch mode
        self.mode = self.MODE_BRANCH
        self.branch = branch
        self.filename = filename

    def process_diff_selection(self, selected=False,
                               staged=True, apply_to_worktree=False,
                               reverse=False):
        """Implements un/staging of selected lines or hunks
        """
        if self.mode == self.MODE_BRANCH:
            # We're applying changes from a different branch!
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
            # The normal worktree vs index scenario
            filename = self.get_selected_filename(staged)
            if not filename:
                return
            parser = utils.DiffParser(self.model,
                                      filename=filename,
                                      cached=staged,
                                      reverse=apply_to_worktree)
            offset, selection = self.view.diff_selection()
            parser.process_diff_selection(selected, offset, selection,
                                          apply_to_worktree=apply_to_worktree)
            self.rescan()

    def undo_hunk(self):
        """Destructively removes a hunk from a worktree file"""
        if not qtutils.question(self.view,
                                'Destroy Local Changes?',
                                'This operation will drop '
                                'uncommitted changes.\n'
                                'Continue?',
                                default=False):
            return
        self.process_diff_selection(staged=False, apply_to_worktree=True,
                                    reverse=True)

    def undo_selection(self):
        """Destructively checks out content for the selected file from $head"""
        if not qtutils.question(self.view,
                                'Destroy Local Changes?',
                                'This operation will drop '
                                'uncommitted changes.\n'
                                'Continue?',
                                default=False):
            return
        self.process_diff_selection(staged=False, apply_to_worktree=True,
                                    reverse=True, selected=True)

    def stage_hunk(self):
        """Stages a specific hunk"""
        self.process_diff_selection(staged=False)

    def stage_hunk_selection(self):
        """Stages selected lines"""
        self.process_diff_selection(staged=False, selected=True)

    def unstage_hunk(self, cached=True):
        """Unstages a hunk"""
        self.process_diff_selection(staged=True)

    def unstage_hunk_selection(self):
        """Unstages selected lines"""
        self.process_diff_selection(staged=True, selected=True)

    # #######################################################################
    # end diff gui

    # *rest handles being called from different signals
    def stage_selected(self,*rest):
        """Use 'git add/rm' to add or remove content from the index"""
        if self.read_only():
            return
        unstaged = self.model.get_unstaged()
        selected = self.view.get_unstaged(unstaged)
        if not selected:
            return
        self.log(*self.model.add_or_remove(selected))

    # *rest handles being called from different signals
    def unstage_selected(self, *rest):
        """Use 'git reset/rm' to remove content from the index"""
        if self.read_only():
            return
        staged = self.model.get_staged()
        selected = self.view.get_staged(staged)
        self.log(*self.model.reset_helper(selected))

    def undo_changes(self):
        """Reverts local changes back to whatever's in HEAD."""
        if not self.undoable():
            return
        modified = self.model.get_modified()
        items_to_undo = self.view.get_modified(modified)
        if items_to_undo:
            if not qtutils.question(self.view,
                                    'Destroy Local Changes?',
                                    'This operation will drop '
                                    'uncommitted changes.\n'
                                    'Continue?',
                                    default=False):
                return

            self.log(*self.model.git.checkout(self.head, '--',
                                              with_stderr=True,
                                              with_status=True,
                                              *items_to_undo))
        else:
            qtutils.log(1, self.tr('No files selected for '
                                   'checkout from HEAD.'))

    def viz_all(self):
        """Visualizes the entire git history using gitk."""
        browser = self.model.get_history_browser()
        utils.fork(['sh', '-c', browser, '--all'])

    def viz_current(self):
        """Visualizes the current branch's history using gitk."""
        browser = self.model.get_history_browser()
        utils.fork(['sh', '-c', browser, self.model.get_currentbranch()])

    def _load_gui_state(self):
        """Loads gui state and applies it to our views"""
        state = settings.SettingsManager.get_gui_state(self.view)
        self.view.import_state(state)

    def log(self, status, output, rescan=True):
        """Logs output and optionally rescans for changes."""
        qtutils.log(status, output)
        if rescan:
            self.rescan()

    def tree_context_menu_event(self, event):
        """Creates context menus for the repo status tree"""
        menu = self.tree_context_menu_setup()
        menu.exec_(self.view.status_tree.mapToGlobal(event.pos()))

    def tree_context_menu_setup(self):
        """Sets up the status menu for the repo status tree"""
        staged, modified, unmerged, untracked = self.get_single_selection()

        menu = QtGui.QMenu(self.view)

        if staged:
            menu.addAction(self.tr('Unstage Selected'), self.unstage_selected)
            menu.addSeparator()
            menu.addAction(self.tr('Launch Editor'),
                           lambda: self.edit_file(staged=True))
            menu.addAction(self.tr('Launch Diff Tool'),
                           lambda: self.edit_diff(staged=True))
            return menu

        if unmerged:
            if not utils.is_broken():
                menu.addAction(self.tr('Launch Merge Tool'), self.mergetool)
            menu.addAction(self.tr('Launch Editor'),
                           lambda: self.edit_file(staged=False))
            menu.addSeparator()
            menu.addAction(self.tr('Stage Selected'), self.stage_selected)
            return menu

        enable_staging = self.mode == self.MODE_WORKTREE
        if enable_staging:
            menu.addAction(self.tr('Stage Selected'), self.stage_selected)
            menu.addSeparator()

        menu.addAction(self.tr('Launch Editor'),
                       lambda: self.edit_file(staged=False))

        if modified and enable_staging:
            menu.addAction(self.tr('Launch Diff Tool'),
                           lambda: self.edit_diff(staged=False))
            menu.addSeparator()
            menu.addAction(self.tr('Undo All Changes'), self.undo_changes)

        if untracked:
            menu.addSeparator()
            menu.addAction(self.tr('Delete File(s)'),
                           lambda: self.delete_files(staged=False))

        return menu

    def diff_context_menu_event(self, event):
        """Creates the context menu for the diff display"""
        menu = self.diff_context_menu_setup()
        textedit = self.view.display_text
        menu.exec_(textedit.mapToGlobal(event.pos()))

    def diff_context_menu_setup(self):
        """Sets up the context menu for the diff display"""
        menu = QtGui.QMenu(self.view)
        staged, modified, unmerged, untracked = self.get_single_selection()

        if self.mode == self.MODE_WORKTREE:
            if modified:
                menu.addAction(self.tr('Stage Hunk For Commit'),
                               self.stage_hunk)
                menu.addAction(self.tr('Stage Selected Lines'),
                               self.stage_hunk_selection)
                menu.addSeparator()
                menu.addAction(self.tr('Undo Hunk'), self.undo_hunk)
                menu.addAction(self.tr('Undo Selection'), self.undo_selection)

        elif self.mode == self.MODE_INDEX:
            menu.addAction(self.tr('Unstage Hunk From Commit'), self.unstage_hunk)
            menu.addAction(self.tr('Unstage Selected Lines'), self.unstage_hunk_selection)

        elif self.mode == self.MODE_BRANCH:
            menu.addAction(self.tr('Apply Diff to Work Tree'), self.stage_hunk)
            menu.addAction(self.tr('Apply Diff Selection to Work Tree'), self.stage_hunk_selection)

        elif self.mode == self.MODE_GREP:
            menu.addAction(self.tr('Go Here'), self.goto_grep)

        menu.addSeparator()
        menu.addAction(self.tr('Copy'), self.view.copy_display)
        return menu

    def select_commits_gui(self, title, revs, summaries):
        """Launches a gui for selecting commits"""
        return select_commits(self.model, self.view,
                              self.tr(title), revs, summaries)

    def update_diff_font(self):
        """Updates the diff font based on the configured value"""
        font = self.model.get_cola_config('fontdiff')
        if not font:
            return
        qfont = QtGui.QFont()
        qfont.fromString(font)
        self.view.display_text.setFont(qfont)
        self.view.commitmsg.setFont(qfont)

    def update_ui_font(self):
        """Updates the main UI font based on the configured value"""
        font = self.model.get_cola_config('fontui')
        if not font:
            return
        qfont = QtGui.QFont()
        qfont.fromString(font)
        QtGui.qApp.setFont(qfont)

    def update_tab_width(self):
        """Implements the variable-tab-width setting"""
        tab_width = self.model.get_cola_config('tabwidth')
        display_font = self.view.display_text.font()
        space_width = QtGui.QFontMetrics(display_font).width(' ')
        self.view.display_text.setTabStopWidth(tab_width * space_width)

    def _init_log_window(self):
        """Initializes the logging subwindow"""
        branch = self.model.get_currentbranch()
        qtutils.log(0, self.model.get_git_version()
                       +'\ncola version ' + version.get_version()
                       +'\nCurrent Branch: ' + branch)

    def start_inotify_thread(self):
        """Starts an inotify thread if pyinotify is installed"""
        # Do we have inotify?  If not, return.
        # Recommend installing inotify if we're on Linux.
        self.inotify_thread = None
        if not inotify.AVAILABLE:
            if not utils.is_linux():
                return
            msg = self.tr('inotify: disabled\n'
                          'Note: To enable inotify, '
                          'install python-pyinotify.\n')

            if utils.is_debian():
                msg += self.tr('On Debian systems, '
                               'try: sudo apt-get install '
                               'python-pyinotify')
            qtutils.log(0, msg)
            return

        # Start the notification thread
        qtutils.log(0, self.tr('inotify support: enabled'))
        self.inotify_thread = inotify.GitNotifier(self, self.model.git)
        self.inotify_thread.start()
