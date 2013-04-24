import os
import subprocess
import itertools

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import cmds
from cola import qtutils
from cola import utils
from cola.compat import set
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models.selection import State


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

    def set_initial_size(self):
        self.setMaximumWidth(222)
        QtCore.QTimer.singleShot(1, self.restore_size)

    def restore_size(self):
        self.setMaximumWidth(2 ** 13)

    def refresh(self):
        self.tree.show_selection()


class StatusTreeWidget(QtGui.QTreeWidget):
    # Item categories
    idx_header = -1
    idx_staged = 0
    idx_unmerged = 1
    idx_modified = 2
    idx_untracked = 3
    idx_end = 4

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
        self.setIndentation(0)
        self.setAutoScroll(False)

        self.add_item(N_('Staged'), hide=True)
        self.add_item(N_('Unmerged'), hide=True)
        self.add_item(N_('Modified'), hide=True)
        self.add_item(N_('Untracked'), hide=True)

        # Used to restore the selection
        self.old_scroll = None
        self.old_selection = None
        self.old_contents = None
        self.old_current_item = None

        self.expanded_items = set()

        self.process_selection = qtutils.add_action(self,
                N_('Stage / Unstage'), self._process_selection,
                cmds.Stage.SHORTCUT)

        self.launch_difftool = qtutils.add_action(self,
                cmds.LaunchDifftool.name(),
                cmds.run(cmds.LaunchDifftool),
                cmds.LaunchDifftool.SHORTCUT)
        self.launch_difftool.setIcon(qtutils.icon('git.svg'))

        self.launch_editor = qtutils.add_action(self,
                cmds.LaunchEditor.name(),
                cmds.run(cmds.LaunchEditor),
                cmds.LaunchEditor.SHORTCUT,
                'Return', 'Enter')
        self.launch_editor.setIcon(qtutils.options_icon())

        if not utils.is_win32():
            self.open_using_default_app = qtutils.add_action(self,
                    cmds.OpenDefaultApp.name(),
                    self._open_using_default_app,
                    cmds.OpenDefaultApp.SHORTCUT)
            self.open_using_default_app.setIcon(qtutils.file_icon())

            self.open_parent_dir = qtutils.add_action(self,
                    cmds.OpenParentDir.name(),
                    self._open_parent_dir,
                    cmds.OpenParentDir.SHORTCUT)
            self.open_parent_dir.setIcon(qtutils.open_file_icon())

        self.up = qtutils.add_action(self, N_('Move Up'), self.move_up,
                                     Qt.Key_K)

        self.down = qtutils.add_action(self, N_('Move Down'), self.move_down,
                                       Qt.Key_J)

        self.copy_path_action = qtutils.add_action(self,
                N_('Copy Path to Clipboard'),
                self.copy_path, QtGui.QKeySequence.Copy)
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

    def add_item(self, txt, hide=False):
        """Create a new top-level item in the status tree."""
        # TODO no icon
        font = self.font()
        font.setBold(True)
        font.setCapitalization(QtGui.QFont.SmallCaps)

        item = QtGui.QTreeWidgetItem(self)
        item.setFont(0, font)
        item.setText(0, txt)
        if hide:
            self.setItemHidden(item, True)

    def restore_selection(self):
        if not self.old_selection or not self.old_contents:
            return

        old_c = self.old_contents
        old_s = self.old_selection
        new_c = self.contents()

        def mkselect(lst, widget_getter):
            def select(item, current=False):
                idx = lst.index(item)
                widget = widget_getter(idx)
                if current:
                    self.setCurrentItem(widget)
                self.setItemSelected(widget, True)
            return select

        select_staged = mkselect(new_c.staged, self.staged_item)
        select_unmerged = mkselect(new_c.unmerged, self.unmerged_item)
        select_modified = mkselect(new_c.modified, self.modified_item)
        select_untracked = mkselect(new_c.untracked, self.untracked_item)

        saved_selection = [
        (set(new_c.staged), old_c.staged, set(old_s.staged),
            select_staged),

        (set(new_c.unmerged), old_c.unmerged, set(old_s.unmerged),
            select_unmerged),

        (set(new_c.modified), old_c.modified, set(old_s.modified),
            select_modified),

        (set(new_c.untracked), old_c.untracked, set(old_s.untracked),
            select_untracked),
        ]

        # Restore the current item
        if self.old_current_item:
            category, idx = self.old_current_item
            if category == self.idx_header:
                item = self.invisibleRootItem().child(idx)
                self.setCurrentItem(item)
                self.setItemSelected(item, True)
                return
            # Reselect the current item
            selection_info = saved_selection[category]
            new = selection_info[0]
            old = selection_info[1]
            reselect = selection_info[3]
            try:
                item = old[idx]
            except:
                return
            if item in new:
                reselect(item, current=True)

        # Restore selection
        # When reselecting we only care that the items are selected;
        # we do not need to rerun the callbacks which were triggered
        # above.  Block signals to skip the callbacks.
        self.blockSignals(True)
        for (new, old, selection, reselect) in saved_selection:
            for item in selection:
                if item in new:
                    reselect(item, current=False)
        self.blockSignals(False)

        for (new, old, selection, reselect) in saved_selection:
            # When modified is staged, select the next modified item
            # When unmerged is staged, select the next unmerged item
            # When unstaging, select the next staged item
            # When staging untracked files, select the next untracked item
            if len(new) >= len(old):
                # The list did not shrink so it is not one of these cases.
                continue
            for item in selection:
                # The item still exists so ignore it
                if item in new or item not in old:
                    continue
                # The item no longer exists in this list so search for
                # its nearest neighbors and select them instead.
                idx = old.index(item)
                for j in itertools.chain(old[idx+1:], reversed(old[:idx])):
                    if j in new:
                        reselect(j, current=True)
                        return

    def restore_scrollbar(self):
        vscroll = self.verticalScrollBar()
        if vscroll and self.old_scroll is not None:
            vscroll.setValue(self.old_scroll)
            self.old_scroll = None

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
        self.save_selection()
        self.save_scrollbar()

    def save_scrollbar(self):
        vscroll = self.verticalScrollBar()
        if vscroll:
            self.old_scroll = vscroll.value()
        else:
            self.old_scroll = None

    def current_item(self):
        current = self.currentItem()
        if not current:
            return None
        idx = self.indexFromItem(current, 0)
        if idx.parent().isValid():
            parent_idx = idx.parent()
            entry = (parent_idx.row(), idx.row())
        else:
            entry = (self.idx_header, idx.row())
        return entry

    def save_selection(self):
        self.old_contents = self.contents()
        self.old_selection = self.selection()
        self.old_current_item = self.current_item()

    def updated(self):
        """Update display from model data."""
        self.emit(SIGNAL('updated'))

    def _updated(self):
        self.set_staged(self.m.staged)
        self.set_modified(self.m.modified)
        self.set_unmerged(self.m.unmerged)
        self.set_untracked(self.m.untracked)

        self.restore_selection()
        self.restore_scrollbar()
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
                return self._create_header_context_menu(menu, idx)

        if s.staged:
            return self._create_staged_context_menu(menu, s)

        elif s.unmerged:
            return self._create_unmerged_context_menu(menu, s)
        else:
            return self._create_unstaged_context_menu(menu, s)

    def _create_header_context_menu(self, menu, idx):
        if idx == self.idx_staged:
            menu.addAction(qtutils.icon('remove.svg'),
                           N_('Unstage All'),
                           cmds.run(cmds.UnstageAll))
            return menu
        elif idx == self.idx_unmerged:
            action = menu.addAction(qtutils.icon('add.svg'),
                                    cmds.StageUnmerged.name(),
                                    cmds.run(cmds.StageUnmerged))
            action.setShortcut(cmds.StageUnmerged.SHORTCUT)
            return menu
        elif idx == self.idx_modified:
            action = menu.addAction(qtutils.icon('add.svg'),
                                    cmds.StageModified.name(),
                                    cmds.run(cmds.StageModified))
            action.setShortcut(cmds.StageModified.SHORTCUT)
            return menu

        elif idx == self.idx_untracked:
            action = menu.addAction(qtutils.icon('add.svg'),
                                    cmds.StageUntracked.name(),
                                    cmds.run(cmds.StageUntracked))
            action.setShortcut(cmds.StageUntracked.SHORTCUT)
            return menu

    def _create_staged_context_menu(self, menu, s):
        if s.staged[0] in self.m.submodules:
            return self._create_staged_submodule_context_menu(menu, s)

        action = menu.addAction(qtutils.options_icon(),
                                cmds.LaunchEditor.name(),
                                cmds.run(cmds.LaunchEditor))
        action.setShortcut(cmds.LaunchEditor.SHORTCUT)

        action = menu.addAction(qtutils.git_icon(),
                                cmds.LaunchDifftool.name(),
                                cmds.run(cmds.LaunchDifftool))
        action.setShortcut(cmds.LaunchDifftool.SHORTCUT)

        if self.m.unstageable():
            menu.addSeparator()
            action = menu.addAction(qtutils.icon('remove.svg'),
                                    N_('Unstage Selected'),
                                    cmds.run(cmds.Unstage, self.staged()))
            action.setShortcut(cmds.Unstage.SHORTCUT)

        if not utils.is_win32():
            menu.addSeparator()
            action = menu.addAction(qtutils.file_icon(),
                    cmds.OpenDefaultApp.name(),
                    cmds.run(cmds.OpenDefaultApp, self.staged()))
            action.setShortcut(cmds.OpenDefaultApp.SHORTCUT)

            action = menu.addAction(qtutils.open_file_icon(),
                    cmds.OpenParentDir.name(),
                    self._open_parent_dir)
            action.setShortcut(cmds.OpenParentDir.SHORTCUT)

        if self.m.undoable():
            menu.addSeparator()
            menu.addAction(qtutils.icon('undo.svg'),
                           N_('Revert Unstaged Edits...'),
                           lambda: self._revert_unstaged_edits(staged=True))
            menu.addAction(qtutils.icon('undo.svg'),
                           N_('Revert Uncommited Edits...'),
                           lambda: self._revert_uncommitted_edits(
                                        self.staged()))
        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        return menu

    def _create_staged_submodule_context_menu(self, menu, s):
        menu.addAction(qtutils.git_icon(),
                       N_('Launch git-cola'),
                       cmds.run(cmds.OpenRepo,
                                os.path.abspath(s.staged[0])))

        action = menu.addAction(qtutils.options_icon(),
                                cmds.LaunchEditor.name(),
                                cmds.run(cmds.LaunchEditor))
        action.setShortcut(cmds.LaunchEditor.SHORTCUT)

        menu.addSeparator()
        action = menu.addAction(qtutils.icon('remove.svg'),
                                N_('Unstage Selected'),
                                cmds.run(cmds.Unstage, self.staged()))
        action.setShortcut(cmds.Unstage.SHORTCUT)

        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        return menu

    def _create_unmerged_context_menu(self, menu, s):
        menu.addAction(qtutils.git_icon(),
                       N_('Launch Merge Tool'),
                       cmds.run(cmds.Mergetool, self.unmerged()))

        action = menu.addAction(qtutils.icon('add.svg'),
                                N_('Stage Selected'),
                                cmds.run(cmds.Stage, self.unstaged()))
        action.setShortcut(cmds.Stage.SHORTCUT)
        menu.addSeparator()
        action = menu.addAction(qtutils.options_icon(),
                                cmds.LaunchEditor.name(),
                                cmds.run(cmds.LaunchEditor))
        action.setShortcut(cmds.LaunchEditor.SHORTCUT)

        if not utils.is_win32():
            menu.addSeparator()
            action = menu.addAction(qtutils.file_icon(),
                    cmds.OpenDefaultApp.name(),
                    cmds.run(cmds.OpenDefaultApp, self.unmerged()))
            action.setShortcut(cmds.OpenDefaultApp.SHORTCUT)

            action = menu.addAction(qtutils.open_file_icon(),
                    cmds.OpenParentDir.name(),
                    self._open_parent_dir)
            action.setShortcut(cmds.OpenParentDir.SHORTCUT)

        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        return menu

    def _create_unstaged_context_menu(self, menu, s):
        modified_submodule = (s.modified and
                              s.modified[0] in self.m.submodules)
        if modified_submodule:
            return self._create_modified_submodule_context_menu(menu, s)

        if self.unstaged():
            action = menu.addAction(qtutils.options_icon(),
                                    cmds.LaunchEditor.name(),
                                    cmds.run(cmds.LaunchEditor))
            action.setShortcut(cmds.Edit.SHORTCUT)

        if s.modified and self.m.stageable():
            action = menu.addAction(qtutils.git_icon(),
                                    cmds.LaunchDifftool.name(),
                                    cmds.run(cmds.LaunchDifftool))
            action.setShortcut(cmds.LaunchDifftool.SHORTCUT)

        if self.m.stageable():
            menu.addSeparator()
            action = menu.addAction(qtutils.icon('add.svg'),
                                    N_('Stage Selected'),
                                    cmds.run(cmds.Stage, self.unstaged()))
            action.setShortcut(cmds.Stage.SHORTCUT)

        if s.modified and self.m.stageable():
            if self.m.undoable():
                menu.addSeparator()
                menu.addAction(qtutils.icon('undo.svg'),
                               N_('Revert Unstaged Edits...'),
                               self._revert_unstaged_edits)
                menu.addAction(qtutils.icon('undo.svg'),
                               N_('Revert Uncommited Edits...'),
                               lambda: self._revert_uncommitted_edits(
                                            self.modified()))

        if self.unstaged() and not utils.is_win32():
            menu.addSeparator()
            action = menu.addAction(qtutils.file_icon(),
                    cmds.OpenDefaultApp.name(),
                    cmds.run(cmds.OpenDefaultApp, self.unstaged()))
            action.setShortcut(cmds.OpenDefaultApp.SHORTCUT)

            action = menu.addAction(qtutils.open_file_icon(),
                    cmds.OpenParentDir.name(),
                    self._open_parent_dir)
            action.setShortcut(cmds.OpenParentDir.SHORTCUT)

        if s.untracked:
            menu.addSeparator()
            menu.addAction(qtutils.discard_icon(),
                           N_('Delete File(s)...'), self._delete_files)
            menu.addSeparator()
            menu.addAction(qtutils.icon('edit-clear.svg'),
                           N_('Add to .gitignore'),
                           cmds.run(cmds.Ignore,
                                map(lambda x: '/' + x, self.untracked())))
        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        return menu

    def _create_modified_submodule_context_menu(self, menu, s):
        menu.addAction(qtutils.git_icon(),
                       N_('Launch git-cola'),
                       cmds.run(cmds.OpenRepo,
                            os.path.abspath(s.modified[0])))

        action = menu.addAction(qtutils.options_icon(),
                                cmds.LaunchEditor.name(),
                                cmds.run(cmds.LaunchEditor))
        action.setShortcut(cmds.Edit.SHORTCUT)

        if self.m.stageable():
            menu.addSeparator()
            action = menu.addAction(qtutils.icon('add.svg'),
                                    N_('Stage Selected'),
                                    cmds.run(cmds.Stage, self.unstaged()))
            action.setShortcut(cmds.Stage.SHORTCUT)

        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        return menu


    def _delete_files(self):
        files = self.untracked()
        count = len(files)
        if count == 0:
            return

        title = N_('Delete Files?')
        msg = N_('The following files will be deleted:') + '\n\n'

        fileinfo = subprocess.list2cmdline(files)
        if len(fileinfo) > 2048:
            fileinfo = fileinfo[:2048].rstrip() + '...'
        msg += fileinfo

        info_txt = N_('Delete %d file(s)?') % count
        ok_txt = N_('Delete Files')

        if qtutils.confirm(title, msg, info_txt, ok_txt,
                           default=True,
                           icon=qtutils.discard_icon()):
            cmds.do(cmds.Delete, files)

    def _revert_unstaged_edits(self, staged=False):
        if not self.m.undoable():
            return
        if staged:
            items_to_undo = self.staged()
        else:
            items_to_undo = self.modified()

        if items_to_undo:
            if not qtutils.confirm(N_('Revert Unstaged Changes?'),
                                   N_('This operation drops unstaged changes.\n'
                                      'These changes cannot be recovered.'),
                                   N_('Revert the unstaged changes?'),
                                   N_('Revert Unstaged Changes'),
                                   default=True,
                                   icon=qtutils.icon('undo.svg')):
                return
            args = []
            if not staged and self.m.amending():
                args.append(self.m.head)
            cmds.do(cmds.Checkout, args + ['--'] + items_to_undo)
        else:
            msg = N_('No files selected for checkout from HEAD.')
            Interaction.log(msg)

    def _revert_uncommitted_edits(self, items_to_undo):
        if items_to_undo:
            if not qtutils.confirm(
                    N_('Revert Uncommitted Changes?'),
                    N_('This operation drops uncommitted changes.\n'
                       'These changes cannot be recovered.'),
                    N_('Revert the uncommitted changes?'),
                    N_('Revert Uncommitted Changes'),
                    default=True,
                    icon=qtutils.icon('undo.svg')):
                return
            cmds.do(cmds.Checkout, [self.m.head, '--'] + items_to_undo)
        else:
            msg = N_('No files selected for checkout from HEAD.')
            Interaction.log(msg)

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
                entry = (self.idx_header, idx.row())
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
                cmds.do(cmds.SetDiffText, '')
            else:
                cmds.do(cmds.ResetMode)
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
            cmds.do(cmds.Unstage, s.staged)

        unstaged = []
        if s.unmerged:
            unstaged.extend(s.unmerged)
        if s.modified:
            unstaged.extend(s.modified)
        if s.untracked:
            unstaged.extend(s.untracked)
        if unstaged:
            cmds.do(cmds.Stage, unstaged)

    def _open_using_default_app(self):
        selection = self.selected_group()
        cmds.do(cmds.OpenDefaultApp, selection)

    def _open_parent_dir(self):
        selection = self.selected_group()
        cmds.do(cmds.OpenParentDir, selection)

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
            cls = {
                self.idx_staged: cmds.DiffStagedSummary,
                self.idx_modified: cmds.Diffstat,
                # TODO implement UnmergedSummary
                #self.idx_unmerged: cmds.UnmergedSummary,
                self.idx_untracked: cmds.UntrackedSummary,
            }.get(idx, cmds.Diffstat)
            cmds.do(cls)
        # A staged file
        elif category == self.idx_staged:
            cmds.do(cmds.DiffStaged, self.staged())

        # A modified file
        elif category == self.idx_modified:
            cmds.do(cmds.Diff, self.modified())

        elif category == self.idx_unmerged:
            cmds.do(cmds.Diff, self.unmerged())

        elif category == self.idx_untracked:
            cmds.background(self, cmds.ShowUntracked, self.unstaged())

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
