import os

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt, SIGNAL

import cola
from cola import guicmds
from cola import qtutils
from cola import signals
from cola.prefs import diff_font
from cola.prefs import tab_width
from cola.qt import DiffSyntaxHighlighter
from cola.qtutils import SLOT


class DiffView(QtGui.QTextEdit):
    def __init__(self, parent):
        QtGui.QTextEdit.__init__(self, parent)
        self.setMinimumSize(QtCore.QSize(1, 1))
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.setAcceptRichText(False)
        self.setCursorWidth(2)
        self.setTextInteractionFlags(Qt.TextSelectableByKeyboard |
                                     Qt.TextSelectableByMouse)
        # Diff/patch syntax highlighter
        self.syntax = DiffSyntaxHighlighter(self.document())
        self.setFont(diff_font())
        self.set_tab_width(tab_width())

    def set_tab_width(self, tab_width):
        display_font = self.font()
        space_width = QtGui.QFontMetrics(display_font).width(' ')
        self.setTabStopWidth(tab_width * space_width)


class DiffTextEdit(DiffView):
    def __init__(self, parent):
        DiffView.__init__(self, parent)
        self.model = model = cola.model()

        # Install diff shortcut keys for stage/unstage
        self.action_process_section = qtutils.add_action(self,
                'Process Section',
                self.apply_section, QtCore.Qt.Key_H)
        self.action_process_selection = qtutils.add_action(self,
                'Process Selection',
                self.apply_selection, QtCore.Qt.Key_S)
        # Context menu actions
        self.action_stage_selection = qtutils.add_action(self,
                self.tr('Stage &Selected Lines'),
                self.stage_selection)
        self.action_stage_selection.setIcon(qtutils.icon('add.svg'))

        self.action_revert_selection = qtutils.add_action(self,
                self.tr('Revert Selected Lines...'),
                self.revert_selection)
        self.action_revert_selection.setIcon(qtutils.icon('undo.svg'))

        self.action_unstage_selection = qtutils.add_action(self,
                self.tr('Unstage &Selected Lines'),
                self.unstage_selection)
        self.action_unstage_selection.setIcon(qtutils.icon('remove.svg'))

        self.action_apply_selection = qtutils.add_action(self,
                self.tr('Apply Diff Selection to Work Tree'),
                self.stage_selection)
        self.action_apply_selection.setIcon(qtutils.apply_icon())

        model.add_message_observer(model.message_diff_text_changed,
                                   self.setPlainText)

        self.connect(self, SIGNAL('copyAvailable(bool)'),
                     self.enable_selection_actions)

    # Qt overrides
    def contextMenuEvent(self, event):
        """Create the context menu for the diff display."""
        menu = QtGui.QMenu(self)
        s = cola.selection()

        if self.mode == self.model.mode_worktree:
            if s.modified and s.modified[0] in cola.model().submodules:
                menu.addAction(qtutils.icon('add.svg'),
                               self.tr('Stage'),
                               SLOT(signals.stage, s.modified))
                menu.addAction(qtutils.git_icon(),
                               self.tr('Launch git-cola'),
                               SLOT(signals.open_repo,
                                    os.path.abspath(s.modified[0])))
            elif s.modified:
                menu.addAction(qtutils.icon('add.svg'),
                               self.tr('Stage Section'),
                               self.stage_section)
                menu.addAction(self.action_stage_selection)
                menu.addSeparator()
                menu.addAction(qtutils.icon('undo.svg'),
                               self.tr('Revert Section...'),
                               self.revert_section)
                menu.addAction(self.action_revert_selection)

        elif self.mode == self.model.mode_index:
            if s.staged and s.staged[0] in cola.model().submodules:
                menu.addAction(qtutils.icon('remove.svg'),
                               self.tr('Unstage'),
                               SLOT(signals.unstage, s.staged))
                menu.addAction(qtutils.git_icon(),
                               self.tr('Launch git-cola'),
                               SLOT(signals.open_repo,
                                    os.path.abspath(s.staged[0])))
            else:
                menu.addAction(qtutils.icon('remove.svg'),
                               self.tr('Unstage Section'),
                               self.unstage_section)
                menu.addAction(self.action_unstage_selection)

        elif self.mode == self.model.mode_grep:
            menu.addAction(qtutils.icon('open.svg'),
                           self.tr('Launch Editor'),
                           lambda: guicmds.goto_grep(self.selected_line()))

        menu.addSeparator()
        menu.addAction(qtutils.icon('edit-copy.svg'),
                       'Copy', self.copy)
        menu.addAction(qtutils.icon('edit-select-all.svg'),
                       'Select All', self.selectAll)
        menu.exec_(self.mapToGlobal(event.pos()))

    def wheelEvent(self, event):
        if event.modifiers() & QtCore.Qt.ControlModifier:
            # Intercept the Control modifier to not resize the text
            # when doing control+mousewheel
            event.accept()
            event = QtGui.QWheelEvent(event.pos(), event.delta(),
                                      QtCore.Qt.NoButton,
                                      QtCore.Qt.NoModifier,
                                      event.orientation())
        return super(DiffTextEdit, self).wheelEvent(event)

    def setPlainText(self, text):
        """setPlainText(str) while retaining scrollbar positions"""
        scrollbar = self.verticalScrollBar()
        if scrollbar:
            scrollvalue = scrollbar.value()
        if text is not None:
            QtGui.QTextEdit.setPlainText(self, text)
            if scrollbar:
                scrollbar.setValue(scrollvalue)

    # Accessors
    mode = property(lambda self: self.model.mode)

    def offset_and_selection(self):
        cursor = self.textCursor()
        offset = cursor.position()
        selection = unicode(cursor.selection().toPlainText())
        return offset, selection

    def selected_line(self):
        cursor = self.textCursor()
        offset = cursor.position()
        contents = unicode(self.toPlainText())
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

    # Mutators
    def enable_selection_actions(self, enabled):
        self.action_apply_selection.setEnabled(enabled)
        self.action_revert_selection.setEnabled(enabled)
        self.action_unstage_selection.setEnabled(enabled)
        self.action_stage_selection.setEnabled(enabled)

    def apply_section(self):
        s = cola.single_selection()
        if self.mode == self.model.mode_worktree and s.modified:
            self.stage_section()
        elif self.mode == self.model.mode_index:
            self.unstage_section()

    def apply_selection(self):
        s = cola.single_selection()
        if self.mode == self.model.mode_worktree and s.modified:
            self.stage_selection()
        elif self.mode == self.model.mode_index:
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
        if not qtutils.confirm('Revert Section?',
                               'This operation drops uncommitted changes.\n'
                               'These changes cannot be recovered.',
                               'Revert the uncommitted changes?',
                               'Revert Section',
                               default=False,
                               icon=qtutils.icon('undo.svg')):
            return
        self.process_diff_selection(staged=False, apply_to_worktree=True,
                                    reverse=True)

    def revert_selection(self):
        """Destructively check out content for the selected file from $head."""
        if not qtutils.confirm('Revert Selected Lines?',
                               'This operation drops uncommitted changes.\n'
                               'These changes cannot be recovered.',
                               'Revert the uncommitted changes?',
                               'Revert Selected Lines',
                               default=False,
                               icon=qtutils.icon('undo.svg')):
            return
        self.process_diff_selection(staged=False, apply_to_worktree=True,
                                    reverse=True, selected=True)

    def process_diff_selection(self, selected=False,
                               staged=True, apply_to_worktree=False,
                               reverse=False):
        """Implement un/staging of selected lines or sections."""
        offset, selection = self.offset_and_selection()
        cola.notifier().broadcast(signals.apply_diff_selection,
                                  staged,
                                  selected,
                                  offset,
                                  selection,
                                  apply_to_worktree)
