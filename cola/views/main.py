"""This view provides the main git-cola user interface.
"""
import os

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import core
from cola import utils
from cola import qtutils
from cola import settings
from cola import signals
from cola import resources
from cola.qtutils import SLOT
from cola.views import about
from cola.views import status
from cola.views.syntax import DiffSyntaxHighlighter
from cola.views.mainwindow import MainWindow
from cola.controllers import compare
from cola.controllers import search as smod
from cola.controllers.bookmark import manage_bookmarks
from cola.controllers.bookmark import save_bookmark
from cola.controllers.createbranch import create_new_branch
from cola.controllers.merge import local_merge
from cola.controllers.merge import abort_merge
from cola.controllers.options import update_options
from cola.controllers.util import choose_from_combo
from cola.controllers.util import choose_from_list
from cola.controllers.remote import remote_action
from cola.controllers.repobrowser import browse_git_branch
from cola.controllers.stash import stash
from cola.controllers.selectcommits import select_commits

class MainView(MainWindow):
    """The main cola interface."""
    idx_header = -1
    idx_staged = 0
    idx_modified = 1
    idx_unmerged = 2
    idx_untracked = 3
    idx_end = 4

    # Read-only mode property
    mode = property(lambda self: self.model.mode)

    def __init__(self, parent=None):
        MainWindow.__init__(self, parent)
        self.amend_is_checked = self.amend_checkbox.isChecked

        # Qt does not support noun/verbs
        self.commit_button.setText(qtutils.tr('Commit@@verb'))
        self.commit_menu.setTitle(qtutils.tr('Commit@@verb'))

        # Diff/patch syntax highlighter
        self.syntax = DiffSyntaxHighlighter(self.display_text.document())

        # Display the current column
        self.connect(self.commitmsg,
                     SIGNAL('cursorPositionChanged()'),
                     self.show_cursor_position)

        # Keeps track of merge messages we've seen
        self.merge_message_hash = ''

        # Initialize the seen tree widget indexes
        self._seen_indexes = set()

        # Initialize the GUI to show 'Column: 00'
        self.show_cursor_position()

        # Internal field used by import/export_state().
        # Change this whenever dockwidgets are removed.
        self._widget_version = 1

        self.model = cola.model()
        self.model.add_message_observer(self.model.message_updated,
                                        self._update_view)

        # Listen for text and amend messages
        cola.notifier().listen(signals.diff_text, self.set_display)
        cola.notifier().listen(signals.mode, self._mode_changed)
        cola.notifier().listen(signals.amend, self.amend_checkbox.setChecked)

        # Broadcast the amend mode
        self.connect(self.amend_checkbox, SIGNAL('toggled(bool)'),
                     SLOT(signals.amend_mode))

        # Add button callbacks
        self._relay_button(self.alt_button, signals.reset_mode)
        self._relay_button(self.rescan_button, signals.rescan)
        self._relay_button(self.signoff_button, signals.add_signoff)

        self._connect_button(self.commit_button, self.commit)
        self._connect_button(self.fetch_button, self.fetch)
        self._connect_button(self.push_button, self.push)
        self._connect_button(self.pull_button, self.pull)
        self._connect_button(self.stash_button, stash)

        # Menu actions
        actions = (
            (self.menu_branch_compare, compare.branch_compare),
            (self.menu_branch_diff, self.branch_diff),
            (self.menu_branch_review, self.review_branch),
            (self.menu_browse_branch, self.browse_current),
            (self.menu_browse_other_branch, self.browse_other),
            (self.menu_browse_commits, self.browse_commits),
            (self.menu_create_branch, create_new_branch),
            (self.menu_checkout_branch, self.checkout_branch),
            (self.menu_delete_branch, self.branch_delete),
            (self.menu_rebase_branch, self.rebase),
            (self.menu_clone_repo, self.clone_repo),
            (self.menu_commit_compare, compare.compare),
            (self.menu_commit_compare_file, compare.compare_file),
            (self.menu_cherry_pick, self.cherry_pick),
            (self.menu_diff_expression, self.diff_expression),
            (self.menu_diff_branch, self.diff_branch),
            (self.menu_export_patches, self.export_patches),
            (self.menu_help_about, about.launch_about_dialog),
            (self.menu_help_docs,
                lambda: self.model.git.web__browse(resources.html_docs())),
            (self.menu_load_commitmsg, self.load_commitmsg),
            (self.menu_load_commitmsg_template, self.load_template),
            (self.menu_manage_bookmarks, manage_bookmarks),
            (self.menu_save_bookmark, save_bookmark),
            (self.menu_merge_local, local_merge),
            (self.menu_merge_abort, abort_merge),
            (self.menu_open_repo, self.open_repo),
            (self.menu_options, update_options),
            (self.menu_rescan, SLOT(signals.rescan)),
            (self.menu_search_grep, self.grep),
            (self.menu_search_revision, smod.search(smod.REVISION_ID)),
            (self.menu_search_revision_range, smod.search(smod.REVISION_RANGE)),
            (self.menu_search_message, smod.search(smod.MESSAGE)),
            (self.menu_search_path, smod.search(smod.PATH, True)),
            (self.menu_search_date_range, smod.search(smod.DATE_RANGE)),
            (self.menu_search_diff, smod.search(smod.DIFF)),
            (self.menu_search_author, smod.search(smod.AUTHOR)),
            (self.menu_search_committer, smod.search(smod.COMMITTER)),
            (self.menu_show_diffstat, SLOT(signals.diffstat)),
            (self.menu_stash, stash),
            (self.menu_stage_modified, SLOT(signals.stage_modified)),
            (self.menu_stage_untracked, SLOT(signals.stage_untracked)),
            (self.menu_unstage_all, SLOT(signals.unstage_all)),
            (self.menu_visualize_all, SLOT(signals.visualize_all)),
            (self.menu_visualize_current, SLOT(signals.visualize_current)),
            # TODO This edit menu stuff should/could be command objects
            (self.menu_cut, self.action_cut),
            (self.menu_copy, self.action_copy),
            (self.menu_paste, self.commitmsg.paste),
            (self.menu_delete, self.action_delete),
            (self.menu_select_all, self.commitmsg.selectAll),
            (self.menu_undo, self.commitmsg.undo),
            (self.menu_redo, self.commitmsg.redo),
        )
        for menu, callback in actions:
            self.connect(menu, SIGNAL('triggered()'), callback)

        # Install diff shortcut keys for stage/unstage
        self.display_text.keyPressEvent = self.diff_key_press_event
        self.display_text.contextMenuEvent = self.diff_context_menu_event

        # Restore saved settings
        self._load_gui_state()

    def _relay_button(self, button, signal):
        callback = SLOT(signal)
        self._connect_button(button, callback)

    def _connect_button(self, button, callback):
        self.connect(button, SIGNAL('clicked()'), callback)

    def _update_view(self):
        """Update the title with the current branch and directory name."""
        title = '%s [%s]' % (self.model.project,
                             self.model.currentbranch)
        if self.mode in (self.model.mode_diff, self.model.mode_diff_expr):
            title += ' *** diff mode***'
        elif self.mode == self.model.mode_review:
            title += ' *** review mode***'
        elif self.mode == self.model.mode_amend:
            title += ' *** amending ***'
        self.setWindowTitle(title)

        if not self.model.read_only() and self.mode != self.model.mode_amend:
            # Check if there's a message file in .git/
            merge_msg_path = self.model.merge_message_path()
            if merge_msg_path is None:
                return
            merge_msg_hash = utils.checksum(merge_message_path)
            if merge_msg_hash == self.merge_msg_hash:
                return
            self.merge_msg_hash = merge_msg_hash
            cola.notifier().broadcast(signals.load_commit_message,
                                      merge_msg_path)

    def _mode_changed(self, mode):
        """React to mode changes; hide/show the "Exit Diff Mode" button."""
        if mode in (self.model.mode_review, self.model.mode_diff):
            self.alt_button.setMinimumHeight(40)
            self.alt_button.show()
        else:
            self.alt_button.setMinimumHeight(1)
            self.alt_button.hide()

    def set_display(self, text):
        """Set the diff text display."""
        if text is not None:
            self.display_text.setText(text)

    def selection(self):
        tree = status.widget().tree
        item = tree.currentItem()
        if not item:
            return -1, False
        parent = item.parent()
        if not parent:
            return -1, False

        idx = parent.indexOfChild(item)
        pidx = tree.indexOfTopLevelItem(parent)

        if pidx == self.idx_staged or pidx == self.idx_modified:
            return idx, tree.isItemSelected(item)

        elif pidx == self.idx_unmerged:
            num_modified = tree.topLevelItem(self.idx_modified).childCount()
            return idx + num_modified, tree.isItemSelected(item)

        elif pidx == self.idx_untracked:
            num_modified = tree.topLevelItem(self.idx_modified).childCount()
            num_unmerged = tree.topLevelItem(self.idx_unmerged).childCount()
            return idx + num_modified + num_unmerged, tree.isItemSelected(item)
        return -1, False

    def single_selection(self):
        """Scan across staged, modified, etc. and return a single item."""
        # TODO have selection in the model
        staged, modified, unmerged, untracked = status.widget().selection()
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

    def action_cut(self):
        self.action_copy()
        self.action_delete()

    def action_copy(self):
        cursor = self.commitmsg.textCursor()
        selection = cursor.selection().toPlainText()
        qtutils.set_clipboard(selection)

    def action_delete(self):
        self.commitmsg.textCursor().removeSelectedText()

    def copy_display(self):
        cursor = self.display_text.textCursor()
        selection = cursor.selection().toPlainText()
        qtutils.set_clipboard(selection)

    def diff_selection(self):
        cursor = self.display_text.textCursor()
        offset = cursor.position()
        selection = unicode(cursor.selection().toPlainText())
        return offset, selection

    def selected_line(self):
        cursor = self.display_text.textCursor()
        offset = cursor.position()
        contents = unicode(self.display_text.toPlainText())
        while (offset >= 1
                and contents[offset-1]
                and contents[offset-1] != '\n'):
            offset -= 1
        data = contents[offset:]
        if '\n' in data:
            line, rest = data.split('\n', 1)
        else:
            line = data
        return line

    def show_cursor_position(self):
        """Update the UI with the current row and column."""
        cursor = self.commitmsg.textCursor()
        position = cursor.position()
        txt = unicode(self.commitmsg.toPlainText())
        rows = txt[:position].count('\n') + 1
        cols = cursor.columnNumber()
        display = ' %d,%d ' % (rows, cols)
        if cols > 78:
            display = ('<span style="background-color: red;">%s</span>' %
                       display.replace(' ', '&nbsp;'))
        elif cols > 72:
            display = ('<span style="background-color: orange;">%s</span>' %
                       display.replace(' ', '&nbsp;'))
        elif cols > 64:
            display = ('<span style="background-color: yellow;">%s</span>' %
                       display.replace(' ', '&nbsp;'))
        self.position_label.setText(display)

    def import_state(self, state):
        """Imports data for save/restore"""
        MainWindow.import_state(self, state)
        # Restore the dockwidget, etc. window state
        if 'windowstate' in state:
            windowstate = state['windowstate']
            self.restoreState(QtCore.QByteArray.fromBase64(str(windowstate)),
                              self._widget_version)

    def export_state(self):
        """Exports data for save/restore"""
        state = MainWindow.export_state(self)
        # Save the window state
        windowstate = self.saveState(self._widget_version)
        state['windowstate'] = unicode(windowstate.toBase64().data())
        return state

    def review_branch(self):
        """Diff against an arbitrary revision, branch, tag, etc."""
        branch = choose_from_combo('Select Branch, Tag, or Commit-ish',
                                   self.model.all_branches() +
                                   self.model.tags)
        if not branch:
            return
        cola.notifier().broadcast(signals.review_branch_mode, branch)

    def branch_diff(self):
        """Diff against an arbitrary revision, branch, tag, etc."""
        branch = choose_from_combo('Select Branch, Tag, or Commit-ish',
                                   ['HEAD^'] +
                                   self.model.all_branches() +
                                   self.model.tags)
        if not branch:
            return
        cola.notifier().broadcast(signals.diff_mode, branch)

    def diff_expression(self):
        """Diff using an arbitrary expression."""
        expr = choose_from_combo('Enter Diff Expression',
                                 self.model.all_branches() +
                                 self.model.tags)
        if not expr:
            return
        cola.notifier().broadcast(signals.diff_expr_mode, expr)


    def diff_branch(self):
        """Launches a diff against a branch."""
        branch = choose_from_combo('Select Branch, Tag, or Commit-ish',
                                   ['HEAD^'] +
                                   self.model.all_branches() +
                                   self.model.tags)
        if not branch:
            return
        zfiles_str = self.model.git.diff(branch, name_only=True,
                                         no_color=True,
                                         z=True).rstrip('\0')
        files = zfiles_str.split('\0')
        filename = choose_from_list('Select File', files)
        if not filename:
            return
        cola.notifier().broadcast(signals.branch_mode, branch, filename)

    def _load_gui_state(self):
        """Restores the gui from the preferences file."""
        state = settings.SettingsManager.gui_state(self)
        self.import_state(state)

    def load_commitmsg(self):
        """Load a commit message from a file."""
        filename = qtutils.open_dialog(self,
                                       'Load Commit Message...',
                                       self.model.getcwd())
        if filename:
            cola.notifier().broadcast(signals.load_commit_message, filename)


    def load_template(self):
        """Load the configured commit message template."""
        template = self.model.global_config('commit.template')
        if template:
            cola.notifier().broadcast(signals.load_commit_message, template)


    def diff_key_press_event(self, event):
        """Handle shortcut keys in the diff view."""
        if event.key() != QtCore.Qt.Key_H and event.key() != QtCore.Qt.Key_S:
            event.ignore()
            return
        staged, modified, unmerged, untracked = self.single_selection()
        if event.key() == QtCore.Qt.Key_H:
            if self.mode == self.model.mode_worktree and modified:
                self.stage_hunk()
            elif self.mode == self.model.mode_index:
                self.unstage_hunk()
        elif event.key() == QtCore.Qt.Key_S:
            if self.mode == self.model.mode_worktree and modified:
                self.stage_hunk_selection()
            elif self.mode == self.model.mode_index:
                self.unstage_hunk_selection()

    def process_diff_selection(self, selected=False,
                               staged=True, apply_to_worktree=False,
                               reverse=False):
        """Implement un/staging of selected lines or hunks."""
        offset, selection = self.diff_selection()
        cola.notifier().broadcast(signals.apply_diff_selection,
                                  staged,
                                  selected,
                                  offset,
                                  selection,
                                  apply_to_worktree)

    def undo_hunk(self):
        """Destructively remove a hunk from a worktree file."""
        if not qtutils.question(self,
                                'Destroy Local Changes?',
                                'This operation will drop '
                                'uncommitted changes.\n'
                                'Continue?',
                                default=False):
            return
        self.process_diff_selection(staged=False, apply_to_worktree=True,
                                    reverse=True)

    def undo_selection(self):
        """Destructively check out content for the selected file from $head."""
        if not qtutils.question(self,
                                'Destroy Local Changes?',
                                'This operation will drop '
                                'uncommitted changes.\n'
                                'Continue?',
                                default=False):
            return
        self.process_diff_selection(staged=False, apply_to_worktree=True,
                                    reverse=True, selected=True)

    def stage_hunk(self):
        """Stage a specific hunk."""
        self.process_diff_selection(staged=False)

    def stage_hunk_selection(self):
        """Stage selected lines."""
        self.process_diff_selection(staged=False, selected=True)

    def unstage_hunk(self, cached=True):
        """Unstage a hunk."""
        self.process_diff_selection(staged=True)

    def unstage_hunk_selection(self):
        """Unstage selected lines."""
        self.process_diff_selection(staged=True, selected=True)

    def diff_context_menu_event(self, event):
        """Create the context menu for the diff display."""
        menu = self.diff_context_menu_setup()
        textedit = self.display_text
        menu.exec_(textedit.mapToGlobal(event.pos()))

    def diff_context_menu_setup(self):
        """Set up the context menu for the diff display."""
        menu = QtGui.QMenu(self)
        # TODO selection in the model
        staged, modified, unmerged, untracked = status.widget().selection()

        if self.mode == self.model.mode_worktree:
            if modified:
                menu.addAction(self.tr('Stage &Hunk For Commit'),
                               self.stage_hunk)
                menu.addAction(self.tr('Stage &Selected Lines'),
                               self.stage_hunk_selection)
                menu.addSeparator()
                menu.addAction(self.tr('Undo Hunk'), self.undo_hunk)
                menu.addAction(self.tr('Undo Selection'), self.undo_selection)

        elif self.mode == self.model.mode_index:
            menu.addAction(self.tr('Unstage &Hunk From Commit'), self.unstage_hunk)
            menu.addAction(self.tr('Unstage &Selected Lines'), self.unstage_hunk_selection)

        elif self.mode == self.model.mode_branch:
            menu.addAction(self.tr('Apply Diff to Work Tree'), self.stage_hunk)
            menu.addAction(self.tr('Apply Diff Selection to Work Tree'), self.stage_hunk_selection)

        elif self.mode == self.model.mode_grep:
            menu.addAction(self.tr('Go Here'), self.goto_grep)

        menu.addSeparator()
        menu.addAction(self.tr('Copy'), self.copy_display)
        return menu

    def fetch(self):
        """Launch the 'fetch' remote dialog."""
        remote_action(self, 'fetch')

    def push(self):
        """Launch the 'push' remote dialog."""
        remote_action(self, 'push')

    def pull(self):
        """Launch the 'pull' remote dialog."""
        remote_action(self, 'pull')

    def commit(self):
        """Attempt to create a commit from the index and commit message."""
        #self.reset_mode()
        msg = self.model.commitmsg
        if not msg:
            # Describe a good commit message
            error_msg = self.tr(''
                'Please supply a commit message.\n\n'
                'A good commit message has the following format:\n\n'
                '- First line: Describe in one sentence what you did.\n'
                '- Second line: Blank\n'
                '- Remaining lines: Describe why this change is good.\n')
            qtutils.log(1, error_msg)
            cola.notifier().broadcast(signals.information,
                                      'Missing Commit Message',
                                      error_msg)
            return
        if not self.model.staged:
            error_msg = self.tr(''
                'No changes to commit.\n\n'
                'You must stage at least 1 file before you can commit.\n')
            qtutils.log(1, error_msg)
            cola.notifier().broadcast(signals.information,
                                      'No Staged Changes',
                                      error_msg)
            return
        # Warn that amending published commits is generally bad
        amend = self.amend_is_checked()
        if (amend and self.model.is_commit_published() and
            not qtutils.question(self,
                                 'Rewrite Published Commit?',
                                 'This commit has already been published.\n'
                                 'You are rewriting published history.\n'
                                 'You probably don\'t want to do this.\n\n'
                                 'Continue?',
                                 default=False)):
            return
        # Perform the commit
        cola.notifier().broadcast(signals.commit, amend, msg)

    def grep(self):
        """Prompt and use 'git grep' to find the content."""
        # This should be a command in cola.commands.
        txt, ok = qtutils.prompt('grep')
        if not ok:
            return
        cola.notifier().broadcast(signals.grep, txt)

    def goto_grep(self):
        """Called when Search -> Grep's right-click 'goto' action."""
        line = self.selected_line()
        filename, line_number, contents = line.split(':', 2)
        filename = core.encode(filename)
        cola.notifier().broadcast(signals.edit, [filename], line_number=line_number)

    def open_repo(self):
        """Spawn a new cola session."""
        dirname = qtutils.opendir_dialog(self,
                                         'Open Git Repository...',
                                         self.model.getcwd())
        if not dirname:
            return
        cola.notifier().broadcast(signals.open_repo, dirname)

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
            cola.notifier().broadcast(signals.information,
                                      'Error Cloning',
                                      'Could not parse: "%s"' % url)
            qtutils.log(1, 'Oops, could not parse git url: "%s"' % url)
            return

        # Prompt the user for a directory to use as the parent directory
        msg = 'Select a parent directory for the new clone'
        dirname = qtutils.opendir_dialog(self, msg, self.model.getcwd())
        if not dirname:
            return
        count = 1
        destdir = os.path.join(dirname, default)
        olddestdir = destdir
        if os.path.exists(destdir):
            # An existing path can be specified
            msg = ('"%s" already exists, cola will create a new directory' %
                   destdir)
            cola.notifier().broadcast(signals.information,
                                      'Directory Exists', msg)

        # Make sure the new destdir doesn't exist
        while os.path.exists(destdir):
            destdir = olddestdir + str(count)
            count += 1
        cola.notifier().broadcast(signals.clone, url, destdir)

    def cherry_pick(self):
        """Launch the 'Cherry-Pick' dialog."""
        revs, summaries = self.model.log_helper(all=True)
        commits = select_commits('Cherry-Pick Commit',
                                 revs, summaries, multiselect=False)
        if not commits:
            return
        cola.notifier().broadcast(signals.cherry_pick, commits)

    def browse_commits(self):
        """Launch the 'Browse Commits' dialog."""
        revs, summaries = self.model.log_helper(all=True)
        select_commits('Browse Commits', revs, summaries)

    def export_patches(self):
        """Run 'git format-patch' on a list of commits."""
        revs, summaries = self.model.log_helper()
        to_export = select_commits('Export Patches', revs, summaries)
        if not to_export:
            return
        to_export.reverse()
        revs.reverse()
        cola.notifier().broadcast(signals.format_patch, to_export, revs)

    def browse_current(self):
        """Launch the 'Browse Current Branch' dialog."""
        branch = self.model.currentbranch
        browse_git_branch(branch)

    def browse_other(self):
        """Prompt for a branch and inspect content at that point in time."""
        # Prompt for a branch to browse
        branch = choose_from_combo('Browse Branch Files',
                                   self.view,
                                   self.model.all_branches())
        if not branch:
            return
        # Launch the repobrowser
        browse_git_branch(branch)

    def branch_create(self):
        """Launch the 'Create Branch' dialog."""
        create_new_branch()

    def branch_delete(self):
        """Launch the 'Delete Branch' dialog."""
        branch = choose_from_combo('Delete Branch',
                                   self.model.local_branches)
        if not branch:
            return
        #TODO cmd
        status, output = self.model.delete_branch(branch)
        cola.notifier().broadcast(signals.log_cmd, status, output)

    def checkout_branch(self):
        """Launch the 'Checkout Branch' dialog."""
        branch = choose_from_combo('Checkout Branch',
                                   self.model.local_branches)
        if not branch:
            return
        #TODO cmd
        status, output = self.model.git.checkout(branch,
                                                 with_stderr=True,
                                                 with_status=True)
        cola.notifier().broadcast(signals.log_cmd, status, output)

    def rebase(self):
        """Rebase onto a branch."""
        branch = choose_from_combo('Rebase Branch',
                                   self.model.all_branches())
        if not branch:
            return
        #TODO cmd
        status, output = self.model.git.rebase(branch,
                                               with_stderr=True,
                                               with_status=True)
        cola.notifier().broadcast(signals.log_cmd, status, output)
