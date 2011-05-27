"""This view provides the main git-cola user interface.
"""
import os

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import core
from cola import gitcmds
from cola import guicmds
from cola import utils
from cola import qtutils
from cola import settings
from cola import signals
from cola import resources
from cola.compat import set
from cola.qtutils import SLOT
from cola.views import dag
from cola.views import about
from cola.views import actions as actionsmod
from cola.views.syntax import DiffSyntaxHighlighter
from cola.views.mainwindow import MainWindow
from cola.controllers import classic
from cola.controllers import compare
from cola.controllers import createtag
from cola.controllers import merge
from cola.controllers import search as smod
from cola.controllers import stash
from cola.controllers.bookmark import manage_bookmarks
from cola.controllers.bookmark import save_bookmark
from cola.controllers.createbranch import create_new_branch
from cola.controllers.options import update_options


class MainView(MainWindow):
    """The main cola interface."""

    # Read-only mode property
    mode = property(lambda self: self.model.mode)

    def __init__(self, parent=None):
        MainWindow.__init__(self, parent)
        self.setAcceptDrops(True)

        # Qt does not support noun/verbs
        self.commit_button.setText(qtutils.tr('Commit@@verb'))
        self.commit_menu.setTitle(qtutils.tr('Commit@@verb'))

        self._has_threadpool = hasattr(QtCore, 'QThreadPool')

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
        cola.notifier().connect(signals.diff_text, self.set_display)
        cola.notifier().connect(signals.mode, self._mode_changed)
        cola.notifier().connect(signals.amend, self.amend_checkbox.setChecked)

        # Broadcast the amend mode
        self.connect(self.amend_checkbox, SIGNAL('toggled(bool)'),
                     SLOT(signals.amend_mode))

        # Add button callbacks
        self._relay_button(self.alt_button, signals.reset_mode)
        self._relay_button(self.rescan_button, signals.rescan)

        self._connect_button(self.signoff_button, self.signoff)
        self._connect_button(self.stage_button, self.stage)
        self._connect_button(self.unstage_button, self.unstage)
        self._connect_button(self.commit_button, self.commit)
        self._connect_button(self.fetch_button, guicmds.fetch_slot(self))
        self._connect_button(self.push_button, guicmds.push_slot(self))
        self._connect_button(self.pull_button, guicmds.pull_slot(self))
        self._connect_button(self.stash_button, lambda: stash.stash(parent=self))

        # Menu actions
        actions = [
            (self.menu_quit, self.close),
            (self.menu_branch_compare, compare.branch_compare),
            (self.menu_branch_diff, guicmds.branch_diff),
            (self.menu_branch_review, guicmds.review_branch),
            (self.menu_browse_branch, guicmds.browse_current),
            (self.menu_browse_other_branch, guicmds.browse_other),
            (self.menu_browse_commits, guicmds.browse_commits),
            (self.menu_create_tag, createtag.create_tag),
            (self.menu_create_branch, create_new_branch),
            (self.menu_checkout_branch, guicmds.checkout_branch),
            (self.menu_delete_branch, guicmds.branch_delete),
            (self.menu_rebase_branch, guicmds.rebase),
            (self.menu_clone_repo, guicmds.clone_repo),
            (self.menu_commit_compare, compare.compare),
            (self.menu_commit_compare_file, compare.compare_file),
            (self.menu_cherry_pick, guicmds.cherry_pick),
            (self.menu_diff_expression, guicmds.diff_expression),
            (self.menu_diff_branch, guicmds.diff_branch),
            (self.menu_export_patches, guicmds.export_patches),
            (self.menu_help_about, about.launch_about_dialog),
            (self.menu_help_docs,
                lambda: self.model.git.web__browse(resources.html_docs())),
            (self.menu_load_commitmsg, guicmds.load_commitmsg_slot(self)),
            (self.menu_load_commitmsg_template,
                SLOT(signals.load_commit_template)),
            (self.menu_manage_bookmarks, manage_bookmarks),
            (self.menu_save_bookmark, save_bookmark),
            (self.menu_merge_local, merge.local_merge),
            (self.menu_merge_abort, merge.abort_merge),
            (self.menu_fetch, guicmds.fetch_slot(self)),
            (self.menu_push, guicmds.push_slot(self)),
            (self.menu_pull, guicmds.pull_slot(self)),
            (self.menu_open_repo, guicmds.open_repo_slot(self)),
            (self.menu_options, update_options),
            (self.menu_rescan, SLOT(signals.rescan)),
            (self.menu_grep, guicmds.grep),
            (self.menu_search_commits, smod.search),
            (self.menu_show_diffstat, SLOT(signals.diffstat)),
            (self.menu_stash, lambda: stash.stash(parent=self)),
            (self.menu_stage_modified, SLOT(signals.stage_modified)),
            (self.menu_stage_untracked, SLOT(signals.stage_untracked)),
            (self.menu_unstage_selected, SLOT(signals.unstage_selected)),
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
            (self.menu_classic, classic.cola_classic),
            (self.menu_dag, dag.git_dag),
        ]

        # Diff Actions
        if hasattr(Qt, 'WidgetWithChildrenShortcut'):
            # We can only enable this shortcut on newer versions of Qt
            # that support WidgetWithChildrenShortcut otherwise we get
            # an ambiguous shortcut error.
            self.diff_copy = QtGui.QAction(self.display_text)
            self.diff_copy.setShortcut(QtGui.QKeySequence.Copy)
            self.diff_copy.setShortcutContext(Qt.WidgetWithChildrenShortcut)
            self.display_text.addAction(self.diff_copy)
            actions.append((self.diff_copy, self.copy_display,))

        for menu, callback in actions:
            self.connect(menu, SIGNAL('triggered()'), callback)

        # Install UI wrappers for command objects
        actionsmod.install_command_wrapper(self)
        guicmds.install_command_wrapper(self)

        # Install diff shortcut keys for stage/unstage
        self.display_text.keyPressEvent = self.diff_key_press_event
        self.display_text.contextMenuEvent = self.diff_context_menu_event

        self.connect(self, SIGNAL('update'), self._update_callback)
        self.connect(self, SIGNAL('import_state'), self.import_state)
        self.connect(self, SIGNAL('install_config_actions'),
                     self._install_config_actions)

        # Install .git-config-defined actions
        self._config_task = None
        self.install_config_actions()

        # Restore saved settings
        self._gui_state_task = None
        self._load_gui_state()

    def install_config_actions(self):
        """Install .gitconfig-defined actions"""
        if self._has_threadpool:
            self._config_task = self._start_config_actions_task()
        else:
            names = actionsmod.get_config_actions()
            self._install_config_actions(names)

    def _start_config_actions_task(self):
        """Do the expensive "get_config_actions()" call in the background"""
        class ConfigActionsTask(QtCore.QRunnable):
            def __init__(self, sender):
                QtCore.QRunnable.__init__(self)
                self._sender = sender
            def run(self):
                names = actionsmod.get_config_actions()
                self._sender.emit(SIGNAL('install_config_actions'), names)

        task = ConfigActionsTask(self)
        QtCore.QThreadPool.globalInstance().start(task)
        return task

    def _install_config_actions(self, names):
        """Install .gitconfig-defined actions"""
        if not names:
            return
        menu = self.actions_menu
        menu.addSeparator()
        for name in names:
            menu.addAction(name, SLOT(signals.run_config_action, name))

    def _relay_button(self, button, signal):
        callback = SLOT(signal)
        self._connect_button(button, callback)

    def _connect_button(self, button, callback):
        self.connect(button, SIGNAL('clicked()'), callback)

    def _update_view(self):
        self.emit(SIGNAL('update'))

    def _update_callback(self):
        """Update the title with the current branch and directory name."""
        branch = self.model.currentbranch
        curdir = core.decode(os.getcwd())
        msg = 'Repository: %s\nBranch: %s' % (curdir, branch)
        self.commitdockwidget.setToolTip(msg)

        title = '%s [%s]' % (self.model.project, branch)
        if self.mode in (self.model.mode_diff, self.model.mode_diff_expr):
            title += ' *** diff mode***'
        elif self.mode == self.model.mode_review:
            title += ' *** review mode***'
        elif self.mode == self.model.mode_amend:
            title += ' *** amending ***'
        self.setWindowTitle(title)

        if self.mode != self.model.mode_amend:
            self.amend_checkbox.blockSignals(True)
            self.amend_checkbox.setChecked(False)
            self.amend_checkbox.blockSignals(False)

        if not self.model.read_only() and self.mode != self.model.mode_amend:
            # Check if there's a message file in .git/
            merge_msg_path = gitcmds.merge_message_path()
            if merge_msg_path is None:
                return
            merge_msg_hash = utils.checksum(core.decode(merge_msg_path))
            if merge_msg_hash == self.merge_message_hash:
                return
            self.merge_message_hash = merge_msg_hash
            cola.notifier().broadcast(signals.load_commit_message,
                                      core.decode(merge_msg_path))

    def _mode_changed(self, mode):
        """React to mode changes; hide/show the "Exit Diff Mode" button."""
        if mode in (self.model.mode_review,
                    self.model.mode_diff,
                    self.model.mode_diff_expr):
            self.alt_button.setMinimumHeight(40)
            self.alt_button.show()
        else:
            self.alt_button.setMinimumHeight(1)
            self.alt_button.hide()

    def set_display(self, text):
        """Set the diff text display."""
        scrollbar = self.display_text.verticalScrollBar()
        scrollvalue = scrollbar.value()
        if text is not None:
            self.display_text.setPlainText(text)
            scrollbar.setValue(scrollvalue)

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
            display = ('<span style="color: white; '
                       '             background-color: red;"'
                       '>%s</span>' % display.replace(' ', '&nbsp;'))
        elif cols > 72:
            display = ('<span style="color: black; '
                       '             background-color: orange;"'
                       '>%s</span>' % display.replace(' ', '&nbsp;'))
        elif cols > 64:
            display = ('<span style="color: black; '
                       '             background-color: yellow;"'
                       '>%s</span>' % display.replace(' ', '&nbsp;'))
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

    def _load_gui_state(self):
        """Restores the gui from the preferences file."""
        if self._has_threadpool:
            self._gui_state_task = self._start_gui_state_loading_thread()
        else:
            state = settings.SettingsManager.gui_state(self)
            self.import_state(state)

    def _start_gui_state_loading_thread(self):
        """Do expensive file reading and json decoding in the background"""
        class LoadGUIStateTask(QtCore.QRunnable):
            def __init__(self, sender):
                QtCore.QRunnable.__init__(self)
                self._sender = sender
            def run(self):
                state = settings.SettingsManager.gui_state(self._sender)
                self._sender.emit(SIGNAL('import_state'), state)

        task = LoadGUIStateTask(self)
        QtCore.QThreadPool.globalInstance().start(task)

        return task

    def diff_key_press_event(self, event):
        """Handle shortcut keys in the diff view."""
        result = QtGui.QTextEdit.keyPressEvent(self.display_text, event)
        if event.key() != QtCore.Qt.Key_H and event.key() != QtCore.Qt.Key_S:
            return result

        staged, modified, unmerged, untracked = cola.single_selection()
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
        return result

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

    def stage(self):
        """Stage selected files, or all files if no selection exists."""
        paths = cola.selection_model().unstaged
        if not paths:
            cola.notifier().broadcast(signals.stage_modified)
        else:
            cola.notifier().broadcast(signals.stage, paths)

    def unstage(self):
        """Unstage selected files, or all files if no selection exists."""
        paths = cola.selection_model().staged
        if not paths:
            cola.notifier().broadcast(signals.unstage_all)
        else:
            cola.notifier().broadcast(signals.unstage, paths)

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
        staged, modified, unmerged, untracked = cola.selection()

        if self.mode == self.model.mode_worktree:
            if modified and modified[0] in cola.model().submodules:
                menu.addAction(self.tr('Stage'),
                               SLOT(signals.stage, modified))
                menu.addAction(self.tr('Launch git-cola'),
                               SLOT(signals.open_repo,
                                    os.path.abspath(modified[0])))
            elif modified:
                menu.addAction(self.tr('Stage &Hunk For Commit'),
                               self.stage_hunk)
                menu.addAction(self.tr('Stage &Selected Lines'),
                               self.stage_hunk_selection)
                menu.addSeparator()
                menu.addAction(self.tr('Undo Hunk'),
                               self.undo_hunk)
                menu.addAction(self.tr('Undo Selected Lines'),
                               self.undo_selection)

        elif self.mode == self.model.mode_index:
            if staged and staged[0] in cola.model().submodules:
                menu.addAction(self.tr('Unstage'),
                               SLOT(signals.unstage, staged))
                menu.addAction(self.tr('Launch git-cola'),
                               SLOT(signals.open_repo,
                                    os.path.abspath(staged[0])))
            else:
                menu.addAction(self.tr('Unstage &Hunk From Commit'),
                               self.unstage_hunk)
                menu.addAction(self.tr('Unstage &Selected Lines'),
                               self.unstage_hunk_selection)

        elif self.mode == self.model.mode_branch:
            menu.addAction(self.tr('Apply Diff to Work Tree'),
                           self.stage_hunk)
            menu.addAction(self.tr('Apply Diff Selection to Work Tree'),
                           self.stage_hunk_selection)

        elif self.mode == self.model.mode_grep:
            menu.addAction(self.tr('Go Here'),
                           lambda: guicmds.goto_grep(self.selected_line()))

        menu.addSeparator()
        menu.addAction(self.tr('Copy'), self.copy_display)
        return menu

    def signoff(self):
        """Add standard 'Signed-off-by:' line to the commit message"""
        msg = unicode(self.commitmsg.toPlainText())
        signoff = ('\nSigned-off-by: %s <%s>' %
                    (self.model.local_user_name, self.model.local_user_email))
        if signoff not in msg:
            self.commitmsg.append(signoff)

    def commit(self):
        """Attempt to create a commit from the index and commit message."""
        msg = unicode(self.commitmsg.toPlainText())
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
            if self.model.modified:
                error_msg += '\n'
                error_msg += self.tr('Would you like to stage '
                                     'and commit all modified files?')
                if not qtutils.question(self, 'Stage and commit?', error_msg,
                                        default=False):
                    return
            else:
                return
            cola.notifier().broadcast(signals.stage_modified)
        # Warn that amending published commits is generally bad
        amend = self.amend_checkbox.isChecked()
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

    def dragEnterEvent(self, event):
        """Accepts drops"""
        MainWindow.dragEnterEvent(self, event)
        event.acceptProposedAction()

    def dropEvent(self, event):
        """Apply dropped patches with git-am"""
        event.accept()
        urls = event.mimeData().urls()
        if not urls:
            return
        paths = map(lambda x: unicode(x.path()), urls)
        patches = [p for p in paths if p.endswith('.patch')]
        dirs = [p for p in paths if os.path.isdir(p)]
        dirs.sort()
        for d in dirs:
            patches.extend(self._gather_patches(d))
        # Broadcast the patches to apply
        cola.notifier().broadcast(signals.apply_patches, patches)

    def _gather_patches(self, path):
        """Find patches in a subdirectory"""
        patches = []
        for root, subdirs, files in os.walk(path):
            for name in [f for f in files if f.endswith('.patch')]:
                patches.append(os.path.join(root, name))
        return patches
