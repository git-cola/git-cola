import os
import subprocess
import itertools

from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import signals
from cola import qtutils
from cola import utils
from cola.compat import set
from cola.qtutils import SLOT
from cola.widgets import defs
from cola.models.selection import State


def select_item(tree, item):
    if not item:
        return
    tree.setItemSelected(item, True)
    parent = item.parent()
    if parent:
        tree.scrollToItem(parent)
    tree.scrollToItem(item)


class StatusWidget(QtGui.QWidget):
    """
    Provides a git-status-like repository widget.

    This widget observes the main model and broadcasts
    Qt signals.

    """
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.layout = QtGui.QVBoxLayout(self)
        self.setLayout(self.layout)

        self.tree = StatusTreeWidget(self)
        self.layout.addWidget(self.tree)
        self.layout.setContentsMargins(0, 0, 0, 0)


class StatusTreeWidget(QtGui.QTreeWidget):
    # Item categories
    idx_header = -1
    idx_staged = 0
    idx_unmerged = 1
    idx_modified = 2
    idx_untracked = 3
    idx_end = 4

    txt_default_app = 'Open Using Default Application'

    # Read-only access to the mode state
    mode = property(lambda self: self.m.mode)

    def __init__(self, parent):
        QtGui.QTreeWidget.__init__(self, parent)

        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.headerItem().setHidden(True)
        self.setAllColumnsShowFocus(True)
        self.setSortingEnabled(False)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setRootIsDecorated(False)

        self.add_item('Staged', 'plus.png', hide=True)
        self.add_item('Unmerged', 'unmerged.png', hide=True)
        self.add_item('Modified', 'modified.png', hide=True)
        self.add_item('Untracked', 'untracked.png', hide=True)

        # Used to restore the selection
        self.old_scroll = None
        self.old_selection = None
        self.old_contents = None

        self.expanded_items = set()

        self.process_selection = qtutils.add_action(self,
                'Process Selection', self._process_selection,
                defs.stage_shortcut)

        self.launch_difftool = qtutils.add_action(self,
                'Launch Diff Tool', self._launch_difftool,
                defs.difftool_shortcut)
        self.launch_difftool.setIcon(qtutils.icon('git.svg'))

        self.launch_editor = qtutils.add_action(self,
                'Launch Editor', self._launch_editor,
                defs.editor_shortcut)
        self.launch_editor.setIcon(qtutils.options_icon())

        if not utils.is_win32():
            self.open_using_default_app = qtutils.add_action(self,
                    self.txt_default_app,
                    self._open_using_default_app,
                    defs.default_app_shortcut)
            self.open_using_default_app.setIcon(qtutils.file_icon())

        self.up = qtutils.add_action(self,
                'Move Up', self.move_up, Qt.Key_K)
        self.down = qtutils.add_action(self,
                'Move Down', self.move_down, Qt.Key_J)

        self.copy_path_action = qtutils.add_action(self,
                                                   'Copy Path to Clipboard',
                                                   self.copy_path,
                                                   QtGui.QKeySequence.Copy)
        self.copy_path_action.setIcon(qtutils.theme_icon('edit-copy.svg'))

        self.connect(self, SIGNAL('about_to_update'), self._about_to_update)
        self.connect(self, SIGNAL('updated'), self._updated)

        self.m = cola.model()
        self.m.add_observer(self.m.message_about_to_update,
                            self.about_to_update)
        self.m.add_observer(self.m.message_updated, self.updated)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self.show_selection)

        self.connect(self,
                     SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self.double_clicked)

        self.connect(self,
                     SIGNAL('itemCollapsed(QTreeWidgetItem*)'),
                     lambda x: self.update_column_widths())

        self.connect(self,
                     SIGNAL('itemExpanded(QTreeWidgetItem*)'),
                     lambda x: self.update_column_widths())

    def add_item(self, txt, path, hide=False):
        """Create a new top-level item in the status tree."""
        item = QtGui.QTreeWidgetItem(self)
        item.setText(0, self.tr(txt))
        item.setIcon(0, qtutils.icon(path))
        if hide:
            self.setItemHidden(item, True)

    def restore_selection(self):
        if not self.old_selection or not self.old_contents:
            return

        old_c = self.old_contents
        old_s = self.old_selection
        new_c = self.contents()

        def select_modified(item):
            idx = new_c.modified.index(item)
            select_item(self, self.modified_item(idx))

        def select_unmerged(item):
            idx = new_c.unmerged.index(item)
            select_item(self, self.unmerged_item(idx))

        def select_untracked(item):
            idx = new_c.untracked.index(item)
            select_item(self, self.untracked_item(idx))

        def select_staged(item):
            idx = new_c.staged.index(item)
            select_item(self, self.staged_item(idx))

        restore_selection_actions = (
            (new_c.modified, old_c.modified, old_s.modified, select_modified),
            (new_c.unmerged, old_c.unmerged, old_s.unmerged, select_unmerged),
            (new_c.untracked, old_c.untracked, old_s.untracked, select_untracked),
            (new_c.staged, old_c.staged, old_s.staged, select_staged),
        )

        for (new, old, selection, action) in restore_selection_actions:
            # When modified is staged, select the next modified item
            # When unmerged is staged, select the next unmerged item
            # When untracked is staged, select the next untracked item
            # When something is unstaged we should select the next staged item
            new_set = set(new)
            if len(new) < len(old) and old:
                for idx, i in enumerate(old):
                    if i not in new_set:
                        for j in itertools.chain(old[idx+1:],
                                                 reversed(old[:idx])):
                            if j in new_set:
                                action(j)
                                return

        for (new, old, selection, action) in restore_selection_actions:
            # Reselect items when doing partial-staging
            new_set = set(new)
            for item in selection:
                if item in new_set:
                    action(item)

    def staged_item(self, itemidx):
        return self._subtree_item(self.idx_staged, itemidx)

    def modified_item(self, itemidx):
        return self._subtree_item(self.idx_modified, itemidx)

    def unmerged_item(self, itemidx):
        return self._subtree_item(self.idx_unmerged, itemidx)

    def untracked_item(self, itemidx):
        return self._subtree_item(self.idx_untracked, itemidx)

    def unstaged_item(self, itemidx):
        # is it modified?
        item = self.topLevelItem(self.idx_modified)
        count = item.childCount()
        if itemidx < count:
            return item.child(itemidx)
        # is it unmerged?
        item = self.topLevelItem(self.idx_unmerged)
        count += item.childCount()
        if itemidx < count:
            return item.child(itemidx)
        # is it untracked?
        item = self.topLevelItem(self.idx_untracked)
        count += item.childCount()
        if itemidx < count:
            return item.child(itemidx)
        # Nope..
        return None

    def _subtree_item(self, idx, itemidx):
        parent = self.topLevelItem(idx)
        return parent.child(itemidx)

    def about_to_update(self):
        self.emit(SIGNAL('about_to_update'))

    def _about_to_update(self):
        self.old_selection = self.selection()
        self.old_contents = self.contents()

        self.old_scroll = None
        vscroll = self.verticalScrollBar()
        if vscroll:
            self.old_scroll = vscroll.value()

    def updated(self):
        """Update display from model data."""
        self.emit(SIGNAL('updated'))

    def _updated(self):
        self.set_staged(self.m.staged)
        self.set_modified(self.m.modified)
        self.set_unmerged(self.m.unmerged)
        self.set_untracked(self.m.untracked)

        vscroll = self.verticalScrollBar()
        if vscroll and self.old_scroll is not None:
            vscroll.setValue(self.old_scroll)
            self.old_scroll = None

        self.restore_selection()
        self.update_column_widths()

    def set_staged(self, items):
        """Adds items to the 'Staged' subtree."""
        self._set_subtree(items, self.idx_staged, staged=True,
                          check=not self.m.amending())

    def set_modified(self, items):
        """Adds items to the 'Modified' subtree."""
        self._set_subtree(items, self.idx_modified)

    def set_unmerged(self, items):
        """Adds items to the 'Unmerged' subtree."""
        self._set_subtree(items, self.idx_unmerged)

    def set_untracked(self, items):
        """Adds items to the 'Untracked' subtree."""
        self._set_subtree(items, self.idx_untracked)

    def _set_subtree(self, items, idx,
                     staged=False,
                     untracked=False,
                     check=True):
        """Add a list of items to a treewidget item."""
        parent = self.topLevelItem(idx)
        if items:
            self.setItemHidden(parent, False)
        else:
            self.setItemHidden(parent, True)
        parent.takeChildren()
        for item in items:
            treeitem = qtutils.create_treeitem(item,
                                               staged=staged,
                                               check=check,
                                               untracked=untracked)
            parent.addChild(treeitem)
        self.expand_items(idx, items)

    def update_column_widths(self):
        self.resizeColumnToContents(0)

    def expand_items(self, idx, items):
        """Expand the top-level category "folder" once and only once."""
        # Don't do this if items is empty; this makes it so that we
        # don't add the top-level index into the expanded_items set
        # until an item appears in a particular category.
        if not items:
            return
        # Only run this once; we don't want to re-expand items that
        # we've clicked on to re-collapse on updated().
        if idx in self.expanded_items:
            return
        self.expanded_items.add(idx)
        item = self.topLevelItem(idx)
        if item:
            self.expandItem(item)

    def contextMenuEvent(self, event):
        """Create context menus for the repo status tree."""
        menu = self.create_context_menu()
        menu.exec_(self.mapToGlobal(event.pos()))

    def create_context_menu(self):
        """Set up the status menu for the repo status tree."""
        s = self.selection()
        menu = QtGui.QMenu(self)

        selection = self.selected_indexes()
        if selection:
            category, idx = selection[0]
            # A header item e.g. 'Staged', 'Modified', etc.
            if category == self.idx_header:
                if idx == self.idx_staged:
                    menu.addAction(qtutils.icon('remove.svg'),
                                   self.tr('Unstage All'),
                                   SLOT(signals.unstage_all))
                    return menu
                elif idx == self.idx_unmerged:
                    action = menu.addAction(qtutils.icon('add.svg'),
                                            self.tr('Stage Merged'),
                                            SLOT(signals.stage_unmerged))
                    action.setShortcut(defs.stage_shortcut)
                    return menu
                elif idx == self.idx_modified:
                    action = menu.addAction(qtutils.icon('add.svg'),
                                            self.tr('Stage Modified'),
                                            SLOT(signals.stage_modified))
                    action.setShortcut(defs.stage_shortcut)
                    return menu

                elif idx == self.idx_untracked:
                    action = menu.addAction(qtutils.icon('add.svg'),
                                            self.tr('Stage Untracked'),
                                            SLOT(signals.stage_untracked))
                    action.setShortcut(defs.stage_shortcut)
                    return menu

        if s.staged and self.m.unstageable():
            action = menu.addAction(qtutils.icon('remove.svg'),
                                    self.tr('Unstage Selected'),
                                    SLOT(signals.unstage, self.staged()))
            action.setShortcut(defs.stage_shortcut)

        if s.staged and s.staged[0] in self.m.submodules:
            menu.addAction(qtutils.git_icon(),
                           self.tr('Launch git-cola'),
                           SLOT(signals.open_repo,
                                os.path.abspath(s.staged[0])))
            menu.addSeparator()
            menu.addAction(self.copy_path_action)
            return menu
        elif s.staged:
            menu.addSeparator()
            action = menu.addAction(qtutils.git_icon(),
                                    self.tr('Launch Diff Tool'),
                                    SLOT(signals.difftool, True,
                                         self.staged()))
            action.setShortcut(defs.difftool_shortcut)

            action = menu.addAction(qtutils.options_icon(),
                                    self.tr('Launch Editor'),
                                    SLOT(signals.edit, self.staged()))
            action.setShortcut(defs.editor_shortcut)

            if not utils.is_win32():
                action = menu.addAction(qtutils.file_icon(),
                        self.tr(self.txt_default_app),
                        SLOT(signals.open_default_app, self.staged()))
                action.setShortcut(defs.default_app_shortcut)

            if self.m.undoable():
                menu.addSeparator()
                menu.addAction(qtutils.icon('undo.svg'),
                               self.tr('Revert Unstaged Edits...'),
                               lambda: self._revert_unstaged_edits(staged=True))
            menu.addSeparator()
            menu.addAction(self.copy_path_action)
            return menu

        if s.unmerged:
            menu.addAction(qtutils.git_icon(),
                           self.tr('Launch Merge Tool'),
                           SLOT(signals.mergetool, self.unmerged()))

            action = menu.addAction(qtutils.icon('add.svg'),
                                    self.tr('Stage Selected'),
                                    SLOT(signals.stage, self.unstaged()))
            action.setShortcut(defs.stage_shortcut)
            menu.addSeparator()
            action = menu.addAction(qtutils.options_icon(),
                                    self.tr('Launch Editor'),
                                    SLOT(signals.edit, self.unmerged()))
            action.setShortcut(defs.editor_shortcut)
            if not utils.is_win32():
                action = menu.addAction(qtutils.file_icon(),
                        self.tr(self.txt_default_app),
                        SLOT(signals.open_default_app, self.unmerged()))
                action.setShortcut(defs.default_app_shortcut)
            menu.addSeparator()
            menu.addAction(self.copy_path_action)
            return menu

        modified_submodule = (s.modified and
                              s.modified[0] in self.m.submodules)
        if self.m.stageable():
            action = menu.addAction(qtutils.icon('add.svg'),
                                    self.tr('Stage Selected'),
                                    SLOT(signals.stage, self.unstaged()))
            action.setShortcut(defs.stage_shortcut)
            menu.addSeparator()

        if s.modified and self.m.stageable() and not modified_submodule:
            action = menu.addAction(qtutils.git_icon(),
                                    self.tr('Launch Diff Tool'),
                                    SLOT(signals.difftool, False,
                                         self.modified()))
            action.setShortcut(defs.difftool_shortcut)

        if modified_submodule:
            menu.addAction(qtutils.git_icon(),
                           self.tr('Launch git-cola'),
                           SLOT(signals.open_repo,
                                os.path.abspath(s.modified[0])))
        elif self.unstaged():
            action = menu.addAction(qtutils.options_icon(),
                                    self.tr('Launch Editor'),
                                    SLOT(signals.edit, self.unstaged()))
            action.setShortcut(defs.editor_shortcut)
            if not utils.is_win32():
                action = menu.addAction(qtutils.file_icon(),
                        self.tr(self.txt_default_app),
                        SLOT(signals.open_default_app, self.unstaged()))
                action.setShortcut(defs.default_app_shortcut)

        menu.addSeparator()

        if s.modified and self.m.stageable() and not modified_submodule:
            if self.m.undoable():
                menu.addAction(qtutils.icon('undo.svg'),
                               self.tr('Revert Unstaged Edits...'),
                               self._revert_unstaged_edits)
                menu.addAction(qtutils.icon('undo.svg'),
                               self.tr('Revert Uncommited Edits...'),
                               self._revert_uncommitted_edits)

        if s.untracked:
            menu.addSeparator()
            menu.addAction(qtutils.discard_icon(),
                           self.tr('Delete File(s)...'), self._delete_files)
            menu.addSeparator()
            menu.addAction(qtutils.icon('edit-clear.svg'),
                           self.tr('Add to .gitignore'),
                           SLOT(signals.ignore,
                                map(lambda x: '/' + x, self.untracked())))
        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        return menu

    def _delete_files(self):
        files = self.untracked()
        count = len(files)
        if count == 0:
            return

        title = 'Delete Files?'
        msg = self.tr('The following files will be deleted:\n\n')

        fileinfo = subprocess.list2cmdline(files)
        if len(fileinfo) > 2048:
            fileinfo = fileinfo[:2048].rstrip() + '...'
        msg += fileinfo

        info_txt = unicode(self.tr('Delete %d file(s)?')) % count
        ok_txt = 'Delete Files'

        if qtutils.confirm(title, msg, info_txt, ok_txt,
                           default=False,
                           icon=qtutils.discard_icon()):
            cola.notifier().broadcast(signals.delete, files)

    def _revert_unstaged_edits(self, staged=False):
        if not self.m.undoable():
            return
        if staged:
            items_to_undo = self.staged()
        else:
            items_to_undo = self.modified()

        if items_to_undo:
            if not qtutils.confirm('Revert Unstaged Changes?',
                                   'This operation drops unstaged changes.'
                                   '\nThese changes cannot be recovered.',
                                   'Revert the unstaged changes?',
                                   'Revert Unstaged Changes',
                                   default=False,
                                   icon=qtutils.icon('undo.svg')):
                return
            args = []
            if not staged and self.m.amending():
                args.append(self.m.head)
            cola.notifier().broadcast(signals.checkout,
                                      args + ['--'] + items_to_undo)
        else:
            qtutils.log(1, self.tr('No files selected for '
                                   'checkout from HEAD.'))

    def _revert_uncommitted_edits(self):
        items_to_undo = self.modified()
        if items_to_undo:
            if not qtutils.confirm('Revert Uncommitted Changes?',
                                   'This operation drops uncommitted changes.'
                                   '\nThese changes cannot be recovered.',
                                   'Revert the uncommitted changes?',
                                   'Revert Uncommitted Changes',
                                   default=False,
                                   icon=qtutils.icon('undo.svg')):
                return
            cola.notifier().broadcast(signals.checkout,
                                      [self.m.head, '--'] + items_to_undo)
        else:
            qtutils.log(1, self.tr('No files selected for '
                                   'checkout from HEAD.'))

    def single_selection(self):
        """Scan across staged, modified, etc. and return a single item."""
        st = None
        um = None
        m = None
        ut = None

        s = self.selection()
        if s.staged:
            st = s.staged[0]
        elif s.modified:
            m = s.modified[0]
        elif s.unmerged:
            um = s.unmerged[0]
        elif s.untracked:
            ut = s.untracked[0]

        return State(st, um, m, ut)

    def selected_indexes(self):
        """Returns a list of (category, row) representing the tree selection."""
        selected = self.selectedIndexes()
        result = []
        for idx in selected:
            if idx.parent().isValid():
                parent_idx = idx.parent()
                entry = (parent_idx.row(), idx.row())
            else:
                entry = (-1, idx.row())
            result.append(entry)
        return result

    def selection(self):
        """Return the current selection in the repo status tree."""
        return State(self.staged(), self.unmerged(),
                     self.modified(), self.untracked())

    def contents(self):
        return State(self.m.staged, self.m.unmerged,
                     self.m.modified, self.m.untracked)

    def all_files(self):
        c = self.contents()
        return c.staged + c.unmerged + c.modified + c.untracked

    def selected_group(self):
        """A list of selected files in various states of being"""
        selection = []
        s = self.selection()
        if s.staged:
            selection = s.staged
        elif s.unmerged:
            selection = s.unmerged
        elif s.modified:
            selection = s.modified
        elif s.untracked:
            selection = s.untracked
        return selection

    def selected_idx(self):
        c = self.contents()
        s = self.single_selection()
        offset = 0
        for content, selection in zip(c, s):
            if len(content) == 0:
                continue
            if selection is not None:
                return offset + content.index(selection)
            offset += len(content)
        return None

    def select_by_index(self, idx):
        c = self.contents()
        to_try = [
            (c.staged, self.idx_staged),
            (c.unmerged, self.idx_unmerged),
            (c.modified, self.idx_modified),
            (c.untracked, self.idx_untracked),
        ]
        for content, toplevel_idx in to_try:
            if len(content) == 0:
                continue
            if idx < len(content):
                parent = self.topLevelItem(toplevel_idx)
                item = parent.child(idx)
                self.select_item(item)
                return
            idx -= len(content)

    def select_item(self, item):
        self.scrollToItem(item)
        self.setCurrentItem(item)
        self.setItemSelected(item, True)

    def staged(self):
        return self._subtree_selection(self.idx_staged, self.m.staged)

    def unstaged(self):
        return self.unmerged() + self.modified() + self.untracked()

    def modified(self):
        return self._subtree_selection(self.idx_modified, self.m.modified)

    def unmerged(self):
        return self._subtree_selection(self.idx_unmerged, self.m.unmerged)

    def untracked(self):
        return self._subtree_selection(self.idx_untracked, self.m.untracked)

    def _subtree_selection(self, idx, items):
        item = self.topLevelItem(idx)
        return qtutils.tree_selection(item, items)

    def mouseReleaseEvent(self, event):
        result = QtGui.QTreeWidget.mouseReleaseEvent(self, event)
        self.clicked()
        return result

    def clicked(self, item=None, idx=None):
        """Called when a repo status tree item is clicked.

        This handles the behavior where clicking on the icon invokes
        the a context-specific action.

        """
        # Sync the selection model
        s = self.selection()
        cola.selection_model().set_selection(s)

        # Clear the selection if an empty area was clicked
        selection = self.selected_indexes()
        if not selection:
            if self.m.amending():
                cola.notifier().broadcast(signals.set_diff_text, '')
            else:
                cola.notifier().broadcast(signals.reset_mode)
            self.blockSignals(True)
            self.clearSelection()
            self.blockSignals(False)
            return

    def double_clicked(self, item, idx):
        """Called when an item is double-clicked in the repo status tree."""
        self._process_selection()

    def _process_selection(self):
        s = self.selection()
        if s.staged:
            cola.notifier().broadcast(signals.unstage, s.staged)

        unstaged = []
        if s.unmerged:
            unstaged.extend(s.unmerged)
        if s.modified:
            unstaged.extend(s.modified)
        if s.untracked:
            unstaged.extend(s.untracked)
        if unstaged:
            cola.notifier().broadcast(signals.stage, unstaged)

    def _launch_difftool(self):
        staged, modified, unmerged, untracked = self.selection()
        if staged:
            selection = staged
        elif unmerged:
            selection = unmerged
        elif modified:
            selection = modified
        else:
            return
        cola.notifier().broadcast(signals.difftool, bool(staged), selection)

    def _launch_editor(self):
        selection = self.selected_group()
        if not selection:
            return
        cola.notifier().broadcast(signals.edit, selection)

    def _open_using_default_app(self):
        selection = self.selected_group()
        if not selection:
            return
        cola.notifier().broadcast(signals.open_default_app, selection)

    def show_selection(self):
        """Show the selected item."""
        # Sync the selection model
        cola.selection_model().set_selection(self.selection())

        selection = self.selected_indexes()
        if not selection:
            return
        category, idx = selection[0]
        # A header item e.g. 'Staged', 'Modified', etc.
        if category == self.idx_header:
            signal = {
                self.idx_staged: signals.staged_summary,
                self.idx_modified: signals.modified_summary,
                self.idx_unmerged: signals.unmerged_summary,
                self.idx_untracked: signals.untracked_summary,
            }.get(idx, signals.diffstat)
            cola.notifier().broadcast(signal)
        # A staged file
        elif category == self.idx_staged:
            cola.notifier().broadcast(signals.diff_staged, self.staged())

        # A modified file
        elif category == self.idx_modified:
            cola.notifier().broadcast(signals.diff, self.modified())

        elif category == self.idx_unmerged:
            cola.notifier().broadcast(signals.diff, self.unmerged())

        elif category == self.idx_untracked:
            cola.notifier().broadcast(signals.show_untracked, self.unstaged())

    def move_up(self):
        idx = self.selected_idx()
        all_files = self.all_files()
        if idx is None:
            selection = self.selected_indexes()
            if selection:
                category, toplevel_idx = selection[0]
                if category == self.idx_header:
                    item = self.itemAbove(self.topLevelItem(toplevel_idx))
                    if item is not None:
                        self.select_item(item)
                        return
            if all_files:
                self.select_by_index(len(all_files) - 1)
            return
        if idx - 1 >= 0:
            self.select_by_index(idx - 1)
        else:
            self.select_by_index(len(all_files) - 1)

    def move_down(self):
        idx = self.selected_idx()
        all_files = self.all_files()
        if idx is None:
            selection = self.selected_indexes()
            if selection:
                category, toplevel_idx = selection[0]
                if category == self.idx_header:
                    item = self.itemBelow(self.topLevelItem(toplevel_idx))
                    if item is not None:
                        self.select_item(item)
                        return
            if all_files:
                self.select_by_index(0)
            return
        if idx + 1 < len(all_files):
            self.select_by_index(idx + 1)
        else:
            self.select_by_index(0)

    def copy_path(self):
        """Copy a selected path to the clipboard"""
        filename = cola.selection_model().filename()
        if filename is not None:
            curdir = os.getcwdu()
            qtutils.set_clipboard(os.path.join(curdir, filename))
