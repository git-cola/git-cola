"""Provides the main application controller."""

import os
import sys
import glob

from PyQt4 import QtGui
from PyQt4 import QtCore

import cola
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
from cola.views import log

# controllers namespace
from cola.controllers.bookmark import save_bookmark
from cola.controllers.bookmark import manage_bookmarks
from cola.controllers.classic import cola_classic
from cola.controllers.compare import compare
from cola.controllers.compare import compare_file
from cola.controllers.compare import branch_compare
from cola.controllers.createbranch import create_new_branch
from cola.controllers.merge import local_merge
from cola.controllers.merge import abort_merge
from cola.controllers.options import update_options
from cola.controllers.repobrowser import browse_git_branch
from cola.controllers import search
from cola.controllers.search import search_commits
from cola.controllers.selectcommits import select_commits
from cola.controllers.stash import stash
from cola.controllers.util import choose_from_list
from cola.controllers.util import choose_from_combo

class MainController(QObserver):
    """Manage interactions between models and views."""

    def __init__(self, model, view):
        """Initializes the MainController's internal data."""
        QObserver.__init__(self, model, view)

        # Binds model params to their equivalent view widget
        self.add_observables('commitmsg')

        # When a model attribute changes, this runs a specific action
        self.add_actions(global_cola_fontdiff = self.update_diff_font)
        self.add_actions(global_cola_tabwidth = self.update_tab_width)

        self.add_callbacks(
            # Push Buttons TODO
            #stage_button = self.stage_selected,
            stash_button = lambda: stash(self.model, self.view),

            # File Menu TODO
            menu_quit = self.quit_app,
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

            # TODO REMOVE
            # Branch Menu
            menu_create_branch = self.branch_create,
            menu_checkout_branch = self.checkout_branch,
            menu_branch_compare = self.branch_compare,

            # Commit Menu
            # TODO
            menu_delete_branch = self.branch_delete,
            menu_rebase_branch = self.rebase,
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

            # Tools Menu
            menu_tools_classic = cola_classic,

            # Help Menu
            menu_help_about = lambda: about.launch_about_dialog(self.view),
            menu_help_docs =
                lambda: self.model.git.web__browse(resources.html_docs()),
            )

        # Route events here
        view.closeEvent = self.quit_app

        # Initializes the log subwindow
        self._init_log_window()

        # Updates the main UI fonts
        self.refresh_view('global_cola_fontdiff')

        self.start_inotify_thread()
        if self.has_inotify():
            self.view.rescan_button.hide()

    #####################################################################
    # handle when the status tree is clicked
    def staged_item(self):
        """Return a single selected staged item."""
        staged = self.view.staged(self.model.staged)
        if staged:
            return staged[0]
        else:
            return None

    def untracked_items(self):
        """Return all selected untracked items."""
        return self.view.untracked(self.model.untracked)

    def unstaged_item(self):
        """Return a single selected unstaged item."""
        unstaged = self.view.unstaged(self.model.unstaged)
        if unstaged:
            return unstaged[0]
        else:
            return None

    #####################################################################
    def event(self, msg):
        """Overrides event() to handle custom inotify events."""
        if not inotify.AVAILABLE:
            return
        if msg.type() == inotify.INOTIFY_EVENT:
            cola.notifier().broadcast(signals.rescan)
            return True
        else:
            return False

    #####################################################################
    # Qt callbacks
    def tr(self, fortr):
        """Translates strings."""
        return qtutils.tr(fortr)

    def gen_search(self, searchtype, browse=False):
        """Return a callback to handle various search actions."""
        def search_handler():
            search_commits(self.model, self.view, searchtype, browse)
        return search_handler

    def options(self):
        """Launch the options dialog"""
        update_options(self.view)

    def branch_create(self):
        """Launch the 'Create Branch' dialog."""
        create_new_branch(self.model, self.view)

    def branch_delete(self):
        """Launch the 'Delete Branch' dialog."""
        branch = choose_from_combo('Delete Branch',
                                   self.view,
                                   self.model.local_branches)
        if not branch:
            return
        self.log(*self.model.delete_branch(branch))

    def browse_current(self):
        """Launch the 'Browse Current Branch' dialog."""
        branch = self.model.currentbranch
        browse_git_branch(self.model, self.view, branch)

    def browse_other(self):
        """Prompt for a branch and inspect content at that point in time."""
        # Prompt for a branch to browse
        branch = choose_from_combo('Browse Branch Files',
                                   self.view,
                                   self.model.all_branches())
        if not branch:
            return
        # Launch the repobrowser
        browse_git_branch(self.model, self.view, branch)

    def checkout_branch(self):
        """Launch the 'Checkout Branch' dialog."""
        branch = choose_from_combo('Checkout Branch',
                                   self.view,
                                   self.model.local_branches)
        if not branch:
            return
        self.log(*self.model.git.checkout(branch,
                                          with_stderr=True,
                                          with_status=True))

    def browse_commits(self):
        """Launch the 'Browse Commits' dialog."""
        self.select_commits_gui('Browse Commits',
                                *self.model.log_helper(all=True))

    def cherry_pick(self):
        """Launch the 'Cherry-Pick' dialog."""
        commits = self.select_commits_gui('Cherry-Pick Commits',
                                          multiselect=False,
                                          *self.model.log_helper(all=True))
        if not commits:
            return
        self.log(*self.model.cherry_pick_list(commits))

    def mergetool(self):
        """Launch git-mergetool on a file path."""
        return#TODO
        filename = self.selected_filename(staged=False)
        if not filename or filename not in self.model.unmerged:
            return
        if version.check('mergetool-no-prompt',
                         self.model.git.version().split()[2]):
            utils.fork(['git', 'mergetool', '--no-prompt', '--', filename])
        else:
            utils.fork(['xterm', '-e', 'git', 'mergetool', '--', filename])

    def edit_file(self, staged=True):
        """Launch $editor on a specific path."""
        return# TODO
        filename = self.selected_filename(staged=staged)
        if filename:
            utils.fork([self.model.editor(), filename])

    def edit_diff(self, staged=True):
        """Launches difftool on the specified paths."""
        return# TODO
        filename = self.selected_filename(staged=staged)
        if filename:
            args = []
            if staged and not self.model.read_only():
                args.append('--cached')
            args.extend([self.model.head, '--', filename])
            difftool.launch(args)

    def delete_files(self):
        """Deletes files when called by an untracked file's context menu."""
        rescan=False
        filenames = self.untracked_items()
        for filename in filenames:
            if filename:
                try:
                    os.remove(filename)
                except Exception:
                    qtutils.log(1, self.tr('Error deleting "%s"') % filename)
                else:
                    rescan=True

    def export_patches(self):
        """Run 'git format-patch' on a list of commits."""
        revs, summaries = self.model.log_helper()
        to_export = self.select_commits_gui('Export Patches', revs, summaries)
        if not to_export:
            return
        to_export.reverse()
        revs.reverse()
        qtutils.log(*self.model.format_patch_helper(to_export, revs,
                                                    output='patches'))

    def clone_repo(self):
        """Clone a git repository."""
        url, ok = qtutils.prompt('Path or URL to clone (Env. $VARS okay)')
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
        """Return True if pyinotify is available."""
        return self.inotify_thread and self.inotify_thread.isRunning()

    def quit_app(self, *args):
        """Save config settings and cleanup inotify threads."""
        if self.model.remember_gui_settings():
            settings.SettingsManager.save_gui_state(self.view)

        # Remove any cola temp files
        pattern = self.model.tmp_file_pattern()
        for filename in glob.glob(pattern):
            os.unlink(filename)

        # Stop inotify threads
        if self.has_inotify():
            self.inotify_thread.set_abort(True)
            self.inotify_thread.quit()
            self.inotify_thread.wait()
        self.view.close()

    def rebase(self):
        """Rebase onto a branch."""
        branch = choose_from_combo('Rebase Branch',
                                   self.view,
                                   self.model.all_branches())
        if not branch:
            return
        self.log(*self.model.git.rebase(branch,
                                        with_stderr=True,
                                        with_status=True))

    # use *rest to handle being called from the checkbox signal
    def rescan(self, *rest):
        """Populate view widgets with results from 'git status'."""
        # TODO
        return
        scrollbar = self.view.display_text.verticalScrollBar()
        scrollvalue = scrollbar.value()

    def branch_compare(self):
        """Launch the Branch -> Compare dialog."""
        # TODO
        #self.reset_mode()
        branch_compare(self.model, self.view)

    def undo_changes(self):
        """Reverts local changes back to whatever's in HEAD."""
        return #TODO
        if not self.undoable():
            return
        items_to_undo = self.view.modified(self.model.modified)
        if items_to_undo:
            if not qtutils.question(self.view,
                                    'Destroy Local Changes?',
                                    'This operation will drop '
                                    'uncommitted changes.\n'
                                    'Continue?',
                                    default=False):
                return

            self.log(*self.model.git.checkout('HEAD', '--',
                                              with_stderr=True,
                                              with_status=True,
                                              *items_to_undo))
        else:
            qtutils.log(1, self.tr('No files selected for '
                                   'checkout from HEAD.'))

    def viz_all(self):
        """Visualizes the entire git history using gitk."""
        browser = self.model.history_browser()
        utils.fork(['sh', '-c', browser, '--all'])

    def viz_current(self):
        """Visualize the current branch's history using gitk."""
        browser = self.model.history_browser()
        utils.fork(['sh', '-c', browser, self.model.currentbranch])

    def log(self, status, output):
        """Log output and optionally rescans for changes."""
        qtutils.log(status, output)

    def select_commits_gui(self, title, revs, summaries, multiselect=True):
        """Launch a gui for selecting commits."""
        return select_commits(self.model, self.view,
                              self.tr(title), revs, summaries,
                              multiselect=multiselect)

    def update_diff_font(self):
        """Updates the diff font based on the configured value."""
        qtutils.set_diff_font(qtutils.logger())
        qtutils.set_diff_font(self.view.display_text)
        qtutils.set_diff_font(self.view.commitmsg)
        self.update_tab_width()

    def update_tab_width(self):
        """Implement the variable-tab-width setting."""
        tab_width = self.model.cola_config('tabwidth')
        display_font = self.view.display_text.font()
        space_width = QtGui.QFontMetrics(display_font).width(' ')
        self.view.display_text.setTabStopWidth(tab_width * space_width)

    def _init_log_window(self):
        """Initialize the logging subwindow."""
        branch = self.model.currentbranch
        qtutils.log(0, self.model.git_version +
                    '\ncola version ' + version.version() +
                    '\nCurrent Branch: ' + branch)

    def start_inotify_thread(self):
        """Start an inotify thread if pyinotify is installed."""
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
