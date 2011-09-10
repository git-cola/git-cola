"""This view provides the main git-cola user interface.
"""
import os

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

import cola
from cola import core
from cola import gitcmds
from cola import guicmds
from cola import utils
from cola import qtutils
from cola import settings
from cola import signals
from cola.compat import set
from cola.qtutils import SLOT
from cola.views import actions as actionsmod
from cola.views.syntax import DiffSyntaxHighlighter
from cola.views.mainwindow import MainWindow


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

        self.model.add_message_observer(self.model.message_updated,
                                        self._update_view)

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
        menu.addAction('Copy', self.display_text.copy)
        menu.addAction('Select All', self.display_text.selectAll)

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
                'You must stage at least 1 file before you can commit.')
            if self.model.modified:
                informative_text = self.tr('Would you like to stage '
                                           'and commit all modified files?')
                if not qtutils.confirm(self, 'Stage and commit?',
                                       error_msg,
                                       informative_text,
                                       ok_text='Stage and Commit'):
                    return
            else:
                cola.notifier().broadcast(signals.information,
                                          'Nothing to commit',
                                          error_msg)
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
