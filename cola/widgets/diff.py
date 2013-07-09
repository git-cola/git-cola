import os

from PyQt4 import QtGui
from PyQt4.QtCore import Qt, SIGNAL

import cola
from cola import cmds
from cola import qtutils
from cola.cmds import run
from cola.i18n import N_
from cola.widgets.text import DiffTextEdit


class DiffEditor(DiffTextEdit):

    def __init__(self, parent):
        DiffTextEdit.__init__(self, parent)
        self.model = model = cola.model()
        self.mode = self.model.mode_none

        self.action_process_section = qtutils.add_action(self,
                N_('Process Section'),
                self.apply_section, Qt.Key_H)
        self.action_process_selection = qtutils.add_action(self,
                N_('Process Selection'),
                self.apply_selection, Qt.Key_S)

        self.launch_editor = qtutils.add_action(self,
                cmds.LaunchEditor.name(), run(cmds.LaunchEditor),
                cmds.LaunchEditor.SHORTCUT,
                'Return', 'Enter')
        self.launch_editor.setIcon(qtutils.options_icon())

        self.launch_difftool = qtutils.add_action(self,
                cmds.LaunchDifftool.name(), run(cmds.LaunchDifftool),
                cmds.LaunchDifftool.SHORTCUT)
        self.launch_difftool.setIcon(qtutils.icon('git.svg'))

        self.action_stage_selection = qtutils.add_action(self,
                N_('Stage &Selected Lines'),
                self.stage_selection)
        self.action_stage_selection.setIcon(qtutils.icon('add.svg'))
        self.action_stage_selection.setShortcut(Qt.Key_S)

        self.action_revert_selection = qtutils.add_action(self,
                N_('Revert Selected Lines...'),
                self.revert_selection)
        self.action_revert_selection.setIcon(qtutils.icon('undo.svg'))

        self.action_unstage_selection = qtutils.add_action(self,
                N_('Unstage &Selected Lines'),
                self.unstage_selection)
        self.action_unstage_selection.setIcon(qtutils.icon('remove.svg'))
        self.action_unstage_selection.setShortcut(Qt.Key_S)

        self.action_apply_selection = qtutils.add_action(self,
                N_('Apply Diff Selection to Work Tree'),
                self.stage_selection)
        self.action_apply_selection.setIcon(qtutils.apply_icon())

        model.add_observer(model.message_mode_about_to_change,
                           self._mode_about_to_change)
        model.add_observer(model.message_diff_text_changed, self.setPlainText)

        self.connect(self, SIGNAL('copyAvailable(bool)'),
                     self.enable_selection_actions)

    # Qt overrides
    def contextMenuEvent(self, event):
        """Create the context menu for the diff display."""
        menu = QtGui.QMenu(self)
        s = cola.selection()

        if self.model.stageable():
            if s.modified and s.modified[0] in cola.model().submodules:
                action = menu.addAction(qtutils.icon('add.svg'),
                                        cmds.Stage.name(),
                                        cmds.run(cmds.Stage, s.modified))
                action.setShortcut(cmds.Stage.SHORTCUT)
                menu.addAction(qtutils.git_icon(),
                               N_('Launch git-cola'),
                               cmds.run(cmds.OpenRepo,
                                    os.path.abspath(s.modified[0])))
            elif s.modified:
                action = menu.addAction(qtutils.icon('add.svg'),
                                        N_('Stage Section'),
                                        self.stage_section)
                action.setShortcut(Qt.Key_H)
                menu.addAction(self.action_stage_selection)
                menu.addSeparator()
                menu.addAction(qtutils.icon('undo.svg'),
                               N_('Revert Section...'),
                               self.revert_section)
                menu.addAction(self.action_revert_selection)

        if self.model.unstageable():
            if s.staged and s.staged[0] in cola.model().submodules:
                action = menu.addAction(qtutils.icon('remove.svg'),
                                        cmds.Unstage.name(),
                                        cmds.do(cmds.Unstage, s.staged))
                action.setShortcut(cmds.Unstage.SHORTCUT)
                menu.addAction(qtutils.git_icon(),
                               N_('Launch git-cola'),
                               cmds.do(cmds.OpenRepo,
                                    os.path.abspath(s.staged[0])))
            elif s.staged:
                action = menu.addAction(qtutils.icon('remove.svg'),
                                        N_('Unstage Section'),
                                        self.unstage_section)
                action.setShortcut(Qt.Key_H)
                menu.addAction(self.action_unstage_selection)

        if self.model.stageable() or self.model.unstageable():
            menu.addSeparator()
            menu.addAction(self.launch_editor)
            menu.addAction(self.launch_difftool)

        menu.addSeparator()
        action = menu.addAction(qtutils.icon('edit-copy.svg'),
                                N_('Copy'), self.copy)
        action.setShortcut(QtGui.QKeySequence.Copy)

        action = menu.addAction(qtutils.icon('edit-select-all.svg'),
                                N_('Select All'), self.selectAll)
        action.setShortcut(QtGui.QKeySequence.SelectAll)
        menu.exec_(self.mapToGlobal(event.pos()))

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            # Intercept the Control modifier to not resize the text
            # when doing control+mousewheel
            event.accept()
            event = QtGui.QWheelEvent(event.pos(), event.delta(),
                                      Qt.NoButton,
                                      Qt.NoModifier,
                                      event.orientation())

        return DiffTextEdit.wheelEvent(self, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            # Intercept right-click to move the cursor to the current position.
            # setTextCursor() clears the selection so this is only done when
            # nothing is selected.
            _, selection = self.offset_and_selection()
            if not selection:
                cursor = self.cursorForPosition(event.pos())
                self.setTextCursor(cursor)

        return DiffTextEdit.mousePressEvent(self, event)

    def _mode_about_to_change(self, mode):
        self.mode = mode

    def setPlainText(self, text):
        """setPlainText(str) while retaining scrollbar positions"""
        highlight = (self.mode != self.model.mode_none and
                     self.mode != self.model.mode_untracked)
        self.highlighter.set_enabled(highlight)

        scrollbar = self.verticalScrollBar()
        if scrollbar:
            scrollvalue = scrollbar.value()
        else:
            scrollvalue = None

        if text is None:
            return

        offset, selection = self.offset_and_selection()
        old_text = unicode(self.toPlainText())

        DiffTextEdit.setPlainText(self, text)

        # If the old selection exists in the new text then
        # re-select it.
        if selection and selection in text:
            idx = text.index(selection)
            cursor = self.textCursor()
            cursor.setPosition(idx)
            cursor.setPosition(idx + len(selection),
                               QtGui.QTextCursor.KeepAnchor)
            self.setTextCursor(cursor)

        # Otherwise, if the text is identical and there
        # is no selection then restore the cursor position.
        elif text == old_text:
            cursor = self.textCursor()
            cursor.setPosition(offset)
            self.setTextCursor(cursor)

        if scrollbar and scrollvalue is not None:
            scrollbar.setValue(scrollvalue)

    def offset_and_selection(self):
        cursor = self.textCursor()
        offset = cursor.position()
        selection = unicode(cursor.selection().toPlainText())
        return offset, selection

    # Mutators
    def enable_selection_actions(self, enabled):
        self.action_apply_selection.setEnabled(enabled)
        self.action_revert_selection.setEnabled(enabled)
        self.action_unstage_selection.setEnabled(enabled)
        self.action_stage_selection.setEnabled(enabled)

    def apply_section(self):
        s = cola.single_selection()
        if self.model.stageable() and s.modified:
            self.stage_section()
        elif self.model.unstageable():
            self.unstage_section()

    def apply_selection(self):
        s = cola.single_selection()
        if self.model.stageable() and s.modified:
            self.stage_selection()
        elif self.model.unstageable():
            self.unstage_selection()

    def stage_section(self):
        """Stage a specific section."""
        self.process_diff_selection(staged=False)

    def stage_selection(self):
        """Stage selected lines."""
        self.process_diff_selection(staged=False, selected=True)

    def unstage_section(self, cached=True):
        """Unstage a section."""
        self.process_diff_selection(staged=True)

    def unstage_selection(self):
        """Unstage selected lines."""
        self.process_diff_selection(staged=True, selected=True)

    def revert_section(self):
        """Destructively remove a section from a worktree file."""
        if not qtutils.confirm(N_('Revert Section?'),
                               N_('This operation drops uncommitted changes.\n'
                                  'These changes cannot be recovered.'),
                               N_('Revert the uncommitted changes?'),
                               N_('Revert Section'),
                               default=True,
                               icon=qtutils.icon('undo.svg')):
            return
        self.process_diff_selection(staged=False, apply_to_worktree=True,
                                    reverse=True)

    def revert_selection(self):
        """Destructively check out content for the selected file from $head."""
        if not qtutils.confirm(N_('Revert Selected Lines?'),
                               N_('This operation drops uncommitted changes.\n'
                                  'These changes cannot be recovered.'),
                               N_('Revert the uncommitted changes?'),
                               N_('Revert Selected Lines'),
                               default=True,
                               icon=qtutils.icon('undo.svg')):
            return
        self.process_diff_selection(staged=False, apply_to_worktree=True,
                                    reverse=True, selected=True)

    def process_diff_selection(self, selected=False,
                               staged=True, apply_to_worktree=False,
                               reverse=False):
        """Implement un/staging of selected lines or sections."""
        offset, selection = self.offset_and_selection()
        cmds.do(cmds.ApplyDiffSelection,
                staged, selected, offset, selection, apply_to_worktree)
