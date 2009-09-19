"""This view provides the main git-cola user interface.
"""

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import qtutils
from cola import signals
from cola.qtutils import SLOT
from cola.views.syntax import DiffSyntaxHighlighter
from cola.views.mainwindow import MainWindow

class MainView(MainWindow):
    """The main cola interface."""
    IDX_HEADER = -1
    IDX_STAGED = 0
    IDX_MODIFIED = 1
    IDX_UNMERGED = 2
    IDX_UNTRACKED = 3
    IDX_END = 4

    def __init__(self, parent=None):
        MainWindow.__init__(self, parent)
        self.amend_is_checked = self.amend_checkbox.isChecked
        self.action_undo = self.commitmsg.undo
        self.action_redo = self.commitmsg.redo
        self.action_paste = self.commitmsg.paste
        self.action_select_all = self.commitmsg.selectAll

        # Qt does not support noun/verbs
        self.commit_button.setText(qtutils.tr('Commit@@verb'))
        self.commit_menu.setTitle(qtutils.tr('Commit@@verb'))

        # Diff/patch syntax highlighter
        self.syntax = DiffSyntaxHighlighter(self.display_text.document())

        # Display the current column
        self.connect(self.commitmsg,
                     SIGNAL('cursorPositionChanged()'),
                     self.show_cursor_position)

        # Initialize the seen tree widget indexes
        self._seen_indexes = set()

        # Initialize the GUI to show 'Column: 00'
        self.show_cursor_position()

        # Internal field used by import/export_state().
        # Change this whenever dockwidgets are removed.
        self._widget_version = 1

        # Listen for text messages
        cola.notifier().listen(signals.text, self.set_display)
        cola.notifier().listen(signals.amend, self._amend_listener)
        self.connect(self.amend_checkbox, SIGNAL('toggled(bool)'),
                     SLOT(signals.amend_mode))

    def _amend_listener(self, value):
        self.amend_checkbox.setChecked(value)

    def set_staged(self, items, check=True):
        """Adds items to the 'Staged' subtree."""
        self._set_subtree(items, self.IDX_STAGED, staged=True, check=check)

    def set_modified(self, items):
        """Adds items to the 'Modified' subtree."""
        self._set_subtree(items, self.IDX_MODIFIED)

    def set_unmerged(self, items):
        """Adds items to the 'Unmerged' subtree."""
        self._set_subtree(items, self.IDX_UNMERGED)

    def set_untracked(self, items):
        """Adds items to the 'Untracked' subtree."""
        self._set_subtree(items, self.IDX_UNTRACKED)

    def _set_subtree(self, items, idx,
                     staged=False, untracked=False, check=True):
        parent = self.status_tree.topLevelItem(idx)
        parent.takeChildren()
        for item in items:
            treeitem = qtutils.create_treeitem(item,
                                               staged=staged,
                                               check=check,
                                               untracked=untracked)
            parent.addChild(treeitem)
        if idx not in self._seen_indexes and items:
            self._seen_indexes.add(idx)
            self.expand_status()
        if items:
            self.status_tree.setItemHidden(parent, False)
        else:
            self.status_tree.setItemHidden(parent, True)

    def set_display(self, text):
        """Set the diff text display."""
        if text is not None:
            self.display_text.setText(text)

    def expand_status(self):
        for idx in xrange(0, self.IDX_END):
            item = self.status_tree.topLevelItem(idx)
            if item:
                self.status_tree.expandItem(item)

    def index_for_item(self, item):
        """Given an item, returns the index of the item.
        The indexes for unstaged items are grouped such that
        the index of unmerged[1] = len(modified) + 1, etc.
        """
        if not item:
            return False, -1
        parent = item.parent()
        if not parent:
            return False, -1
        tree = self.status_tree
        pidx = tree.indexOfTopLevelItem(parent)
        if pidx == self.IDX_STAGED:
            return True, parent.indexOfChild(item)
        elif pidx == self.IDX_MODIFIED:
            return False, parent.indexOfChild(item)

        count = tree.topLevelItem(self.IDX_MODIFIED).childCount()
        if pidx == self.IDX_UNMERGED:
            return False, count + parent.indexOfChild(item)

        count += tree.topLevelItem(self.IDX_UNMERGED).childCount()
        if pidx == self.IDX_UNTRACKED:
            return False, count + parent.indexOfChild(item)

        return False, -1

    def selection(self):
        tree = self.status_tree
        item = tree.currentItem()
        if not item:
            return -1, False
        parent = item.parent()
        if not parent:
            return -1, False

        idx = parent.indexOfChild(item)
        pidx = tree.indexOfTopLevelItem(parent)

        if pidx == self.IDX_STAGED or pidx == self.IDX_MODIFIED:
            return idx, tree.isItemSelected(item)

        elif pidx == self.IDX_UNMERGED:
            num_modified = tree.topLevelItem(self.IDX_MODIFIED).childCount()
            return idx + num_modified, tree.isItemSelected(item)

        elif pidx == self.IDX_UNTRACKED:
            num_modified = tree.topLevelItem(self.IDX_MODIFIED).childCount()
            num_unmerged = tree.topLevelItem(self.IDX_UNMERGED).childCount()
            return idx + num_modified + num_unmerged, tree.isItemSelected(item)
        return -1, False

    def staged_item(self, itemidx):
        return self._subtree_item(self.IDX_STAGED, itemidx)

    def modified_item(self, itemidx):
        return self._subtree_item(self.IDX_MODIFIED, itemidx)

    def unstaged_item(self, itemidx):
        tree = self.status_tree
        # is it modified?
        item = tree.topLevelItem(self.IDX_MODIFIED)
        count = item.childCount()
        if itemidx < count:
            return item.child(itemidx)
        # is it unmerged?
        item = tree.topLevelItem(self.IDX_UNMERGED)
        count += item.childCount()
        if itemidx < count:
            return item.child(itemidx)
        # is it untracked?
        item = tree.topLevelItem(self.IDX_UNTRACKED)
        count += item.childCount()
        if itemidx < count:
            return item.child(itemidx)
        # Nope..
        return None

    def _subtree_item(self, idx, itemidx):
        parent = self.status_tree.topLevelItem(idx)
        return parent.child(itemidx)

    def unstaged(self, items):
        tree = self.status_tree
        num_modified = tree.topLevelItem(self.IDX_MODIFIED).childCount()
        num_unmerged = tree.topLevelItem(self.IDX_UNMERGED).childCount()
        modified = self.modified(items)
        unmerged = self.unmerged(items[num_modified:])
        untracked = self.untracked(items[num_modified+num_unmerged:])
        return modified + unmerged + untracked

    def staged(self, items):
        return self._subtree_selection(self.IDX_STAGED, items)

    def modified(self, items):
        return self._subtree_selection(self.IDX_MODIFIED, items)

    def unmerged(self, items):
        return self._subtree_selection(self.IDX_UNMERGED, items)

    def untracked(self, items):
        return self._subtree_selection(self.IDX_UNTRACKED, items)

    def _subtree_selection(self, idx, items):
        item = self.status_tree.topLevelItem(idx)
        return qtutils.tree_selection(item, items)

    def show(self):
        """Override base show to set icons and expand top-level items."""
        result = MainWindow.show(self)
        staged = self.status_tree.topLevelItem(self.IDX_STAGED)
        staged.setIcon(0, qtutils.icon('plus.png'))

        modified = self.status_tree.topLevelItem(self.IDX_MODIFIED)
        modified.setIcon(0, qtutils.icon('modified.png'))

        unmerged = self.status_tree.topLevelItem(self.IDX_UNMERGED)
        unmerged.setIcon(0, qtutils.icon('unmerged.png'))

        untracked = self.status_tree.topLevelItem(self.IDX_UNTRACKED)
        untracked.setIcon(0, qtutils.icon('untracked.png'))

        # Set the diff font
        qtutils.set_diff_font(self.display_text)

        self.status_tree.expandToDepth(0)
        return result

    def enter_diff_mode(self, text):
        """
        Enter diff mode; changes the 'Staged' header to 'Changed'.

        This also enables the 'Exit <Mode> Mode' button.
        `text` is the message displayed on the button.

        """
        staged = self.status_tree.topLevelItem(self.IDX_STAGED)
        staged.setText(0, self.tr('Changed'))
        self.alt_button.setText(self.tr(text))
        self.alt_button.setMinimumHeight(40)
        self.alt_button.show()

    def exit_diff_mode(self):
        """
        Exit diff mode; changes the 'Changed' header to 'Staged'.

        This also hides the 'Exit Diff Mode' button.

        """
        staged = self.status_tree.topLevelItem(self.IDX_STAGED)
        staged.setText(0, self.tr('Staged'))
        self.alt_button.setMinimumHeight(1)
        self.alt_button.hide()
        self.reset_display()

    def action_cut(self):
        self.action_copy()
        self.action_delete()

    def action_copy(self):
        cursor = self.commitmsg.textCursor()
        selection = cursor.selection().toPlainText()
        qtutils.set_clipboard(selection)

    def action_delete(self):
        self.commitmsg.textCursor().removeSelectedText()

    def reset_checkboxes(self):
        self.amend_checkbox.setChecked(False)

    def reset_display(self):
        self.set_display('')

    def copy_display(self):
        cursor = self.display_text.textCursor()
        selection = cursor.selection().toPlainText()
        qtutils.set_clipboard(selection)

    def diff_selection(self):
        cursor = self.display_text.textCursor()
        offset = cursor.position()
        selection = unicode(cursor.selection().toPlainText())
        return offset, selection

    def tree_selection(self):
        """Returns a list of (category, row) representing the tree selection."""
        selected = self.status_tree.selectedIndexes()
        result = []
        for idx in selected:
            if idx.parent().isValid():
                parent_idx = idx.parent()
                entry = (parent_idx.row(), idx.row())
            else:
                entry = (-1, idx.row())
            result.append(entry)
        return result

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

    def display(self, text):
        self.set_display(text)

    def show_cursor_position(self):
        """Update the UI with the current row and column."""
        cursor = self.commitmsg.textCursor()
        position = cursor.position()
        txt = unicode(self.commitmsg.toPlainText())
        rows = txt[:position].count('\n')
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
