from __future__ import division, absolute_import, unicode_literals

import itertools

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import qtutils
from cola import utils
from cola.i18n import N_
from cola.models import main
from cola.models import selection
from cola.widgets import completion
from cola.widgets import defs


class StatusWidget(QtGui.QWidget):
    """
    Provides a git-status-like repository widget.

    This widget observes the main model and broadcasts
    Qt signals.

    """
    def __init__(self, titlebar, parent=None):
        QtGui.QWidget.__init__(self, parent)

        tooltip = N_('Toggle the paths filter')
        self.filter_button = qtutils.create_action_button(
                tooltip=tooltip,
                icon=qtutils.filter_icon())

        self.filter_widget = StatusFilterWidget()
        self.filter_widget.hide()
        self.tree = StatusTreeWidget()
        self.setFocusProxy(self.tree)

        self.main_layout = qtutils.vbox(defs.no_margin, defs.no_spacing,
                                        self.filter_widget, self.tree)
        self.setLayout(self.main_layout)

        self.toggle_action = qtutils.add_action(self, tooltip,
                self.toggle_filter, 'Ctrl+Shift+F')

        titlebar.add_corner_widget(self.filter_button)
        qtutils.connect_button(self.filter_button, self.toggle_filter)

    def toggle_filter(self):
        shown = not self.filter_widget.isVisible()
        self.filter_widget.setVisible(shown)
        if shown:
            self.filter_widget.setFocus(True)
        else:
            self.tree.setFocus(True)

    def set_initial_size(self):
        self.setMaximumWidth(222)
        QtCore.QTimer.singleShot(1, self.restore_size)

    def restore_size(self):
        self.setMaximumWidth(2 ** 13)

    def refresh(self):
        self.tree.show_selection()

    def set_filter(self, txt):
        self.filter_widget.setVisible(True)
        self.filter_widget.text.set_value(txt)
        self.filter_widget.apply_filter()

    def move_up(self):
        self.tree.move_up()

    def move_down(self):
        self.tree.move_down()


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

    def __init__(self, parent=None):
        QtGui.QTreeWidget.__init__(self, parent)

        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.headerItem().setHidden(True)
        self.setAllColumnsShowFocus(True)
        self.setSortingEnabled(False)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setRootIsDecorated(False)
        self.setIndentation(0)
        self.setDragEnabled(True)

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

        self.process_selection_action = qtutils.add_action(self,
                cmds.StageOrUnstage.name(),
                cmds.run(cmds.StageOrUnstage),
                cmds.StageOrUnstage.SHORTCUT)

        self.revert_unstaged_edits_action = qtutils.add_action(self,
                cmds.RevertUnstagedEdits.name(),
                cmds.run(cmds.RevertUnstagedEdits),
                cmds.RevertUnstagedEdits.SHORTCUT)
        self.revert_unstaged_edits_action.setIcon(qtutils.theme_icon('edit-undo.svg'))

        self.launch_difftool_action = qtutils.add_action(self,
                cmds.LaunchDifftool.name(),
                cmds.run(cmds.LaunchDifftool),
                cmds.LaunchDifftool.SHORTCUT)
        self.launch_difftool_action.setIcon(qtutils.git_icon())

        self.launch_editor_action = qtutils.add_action(self,
                cmds.LaunchEditor.name(),
                cmds.run(cmds.LaunchEditor),
                cmds.LaunchEditor.SHORTCUT,
                'Return', 'Enter')
        self.launch_editor_action.setIcon(qtutils.options_icon())

        if not utils.is_win32():
            self.open_using_default_app = qtutils.add_action(self,
                    cmds.OpenDefaultApp.name(),
                    self._open_using_default_app,
                    cmds.OpenDefaultApp.SHORTCUT)
            self.open_using_default_app.setIcon(qtutils.file_icon())

            self.open_parent_dir_action = qtutils.add_action(self,
                    cmds.OpenParentDir.name(),
                    self._open_parent_dir,
                    cmds.OpenParentDir.SHORTCUT)
            self.open_parent_dir_action.setIcon(qtutils.open_file_icon())

        self.up_action = qtutils.add_action(self,
                N_('Move Up'), self.move_up,
                Qt.Key_K, Qt.AltModifier + Qt.Key_K)

        self.down_action = qtutils.add_action(self,
                N_('Move Down'), self.move_down,
                Qt.Key_J, Qt.AltModifier + Qt.Key_J)

        self.copy_path_action = qtutils.add_action(self,
                N_('Copy Path to Clipboard'),
                self.copy_path, QtGui.QKeySequence.Copy)
        self.copy_path_action.setIcon(qtutils.theme_icon('edit-copy.svg'))

        self.copy_relpath_action = qtutils.add_action(self,
                N_('Copy Relative Path to Clipboard'),
                self.copy_relpath, QtGui.QKeySequence.Cut)
        self.copy_relpath_action.setIcon(qtutils.theme_icon('edit-copy.svg'))

        # MoveToTrash and Delete use the same shortcut.
        # We will only bind one of them, depending on whether or not the
        # MoveToTrash command is avaialble.  When available, the hotkey
        # is bound to MoveToTrash, otherwise it is bound to Delete.
        if cmds.MoveToTrash.AVAILABLE:
            self.move_to_trash_action = qtutils.add_action(self,
                    N_('Move file(s) to trash'),
                    self._trash_untracked_files, cmds.MoveToTrash.SHORTCUT)
            self.move_to_trash_action.setIcon(qtutils.discard_icon())
            delete_shortcut = cmds.Delete.SHORTCUT
        else:
            self.move_to_trash_action = None
            delete_shortcut = cmds.Delete.ALT_SHORTCUT

        self.delete_untracked_files_action = qtutils.add_action(self,
                N_('Delete File(s)...'),
                self._delete_untracked_files, delete_shortcut)
        self.delete_untracked_files_action.setIcon(qtutils.discard_icon())

        self.connect(self, SIGNAL('about_to_update()'),
                     self._about_to_update, Qt.QueuedConnection)
        self.connect(self, SIGNAL('updated()'),
                     self._updated, Qt.QueuedConnection)

        self.m = main.model()
        self.m.add_observer(self.m.message_about_to_update,
                            self.about_to_update)
        self.m.add_observer(self.m.message_updated, self.updated)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self.show_selection)

        self.connect(self, SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self.double_clicked)

        self.connect(self, SIGNAL('itemCollapsed(QTreeWidgetItem*)'),
                     lambda x: self.update_column_widths())

        self.connect(self, SIGNAL('itemExpanded(QTreeWidgetItem*)'),
                     lambda x: self.update_column_widths())

    def add_item(self, txt, hide=False):
        """Create a new top-level item in the status tree."""
        # TODO no icon
        font = self.font()
        font.setBold(True)

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
                if item is not None:
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
        for (new, old, sel, reselect) in saved_selection:
            for item in sel:
                if item in new:
                    reselect(item, current=False)
        self.blockSignals(False)

        for (new, old, sel, reselect) in saved_selection:
            # When modified is staged, select the next modified item
            # When unmerged is staged, select the next unmerged item
            # When unstaging, select the next staged item
            # When staging untracked files, select the next untracked item
            if len(new) >= len(old):
                # The list did not shrink so it is not one of these cases.
                continue
            for item in sel:
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
        self.emit(SIGNAL('about_to_update()'))

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
        s = self.selected_indexes()
        if not s:
            return None
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
        self.emit(SIGNAL('updated()'))

    def _updated(self):
        self.set_staged(self.m.staged)
        self.set_modified(self.m.modified)
        self.set_unmerged(self.m.unmerged)
        self.set_untracked(self.m.untracked)
        self.restore_selection()
        self.restore_scrollbar()
        self.update_column_widths()
        self.update_actions()

    def update_actions(self, selected=None):
        if selected is None:
            selected = selection.selection()
        can_revert_edits = bool(selected.staged or selected.modified)
        self.revert_unstaged_edits_action.setEnabled(can_revert_edits)

    def set_staged(self, items):
        """Adds items to the 'Staged' subtree."""
        self._set_subtree(items, self.idx_staged, staged=True,
                          deleted_set=self.m.staged_deleted)

    def set_modified(self, items):
        """Adds items to the 'Modified' subtree."""
        self._set_subtree(items, self.idx_modified,
                          deleted_set=self.m.unstaged_deleted)

    def set_unmerged(self, items):
        """Adds items to the 'Unmerged' subtree."""
        self._set_subtree(items, self.idx_unmerged)

    def set_untracked(self, items):
        """Adds items to the 'Untracked' subtree."""
        self._set_subtree(items, self.idx_untracked, untracked=True)

    def _set_subtree(self, items, idx,
                     staged=False,
                     untracked=False,
                     deleted_set=None):
        """Add a list of items to a treewidget item."""
        self.blockSignals(True)
        parent = self.topLevelItem(idx)
        if items:
            self.setItemHidden(parent, False)
        else:
            self.setItemHidden(parent, True)

        # sip v4.14.7 and below leak memory in parent.takeChildren()
        # so we use this backwards-compatible construct instead
        while parent.takeChild(0) is not None:
            pass

        for item in items:
            deleted = (deleted_set is not None and item in deleted_set)
            treeitem = qtutils.create_treeitem(item,
                                               staged=staged,
                                               deleted=deleted,
                                               untracked=untracked)
            parent.addChild(treeitem)
        self.expand_items(idx, items)
        self.blockSignals(False)

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

        selected_indexes = self.selected_indexes()
        if selected_indexes:
            category, idx = selected_indexes[0]
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
            menu.addAction(qtutils.remove_icon(),
                           N_('Unstage All'),
                           cmds.run(cmds.UnstageAll))
            return menu
        elif idx == self.idx_unmerged:
            action = menu.addAction(qtutils.add_icon(),
                                    cmds.StageUnmerged.name(),
                                    cmds.run(cmds.StageUnmerged))
            action.setShortcut(cmds.StageUnmerged.SHORTCUT)
            return menu
        elif idx == self.idx_modified:
            action = menu.addAction(qtutils.add_icon(),
                                    cmds.StageModified.name(),
                                    cmds.run(cmds.StageModified))
            action.setShortcut(cmds.StageModified.SHORTCUT)
            return menu

        elif idx == self.idx_untracked:
            action = menu.addAction(qtutils.add_icon(),
                                    cmds.StageUntracked.name(),
                                    cmds.run(cmds.StageUntracked))
            action.setShortcut(cmds.StageUntracked.SHORTCUT)
            return menu

    def _create_staged_context_menu(self, menu, s):
        if s.staged[0] in self.m.submodules:
            return self._create_staged_submodule_context_menu(menu, s)

        if self.m.unstageable():
            action = menu.addAction(qtutils.remove_icon(),
                                    N_('Unstage Selected'),
                                    cmds.run(cmds.Unstage, self.staged()))
            action.setShortcut(cmds.Unstage.SHORTCUT)

        # Do all of the selected items exist?
        all_exist = all(not i in self.m.staged_deleted and core.exists(i)
                        for i in self.staged())

        if all_exist:
            menu.addAction(self.launch_editor_action)
            menu.addAction(self.launch_difftool_action)

        if all_exist and not utils.is_win32():
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
            menu.addAction(self.revert_unstaged_edits_action)

        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        menu.addAction(self.copy_relpath_action)
        return menu

    def _create_staged_submodule_context_menu(self, menu, s):
        menu.addAction(qtutils.git_icon(),
                       N_('Launch git-cola'),
                       cmds.run(cmds.OpenRepo,
                                core.abspath(s.staged[0])))

        menu.addAction(self.launch_editor_action)
        menu.addSeparator()

        action = menu.addAction(qtutils.remove_icon(),
                                N_('Unstage Selected'),
                                cmds.run(cmds.Unstage, self.staged()))
        action.setShortcut(cmds.Unstage.SHORTCUT)
        menu.addSeparator()

        menu.addAction(self.copy_path_action)
        menu.addAction(self.copy_relpath_action)
        return menu

    def _create_unmerged_context_menu(self, menu, s):
        menu.addAction(self.launch_difftool_action)

        action = menu.addAction(qtutils.add_icon(),
                                N_('Stage Selected'),
                                cmds.run(cmds.Stage, self.unstaged()))
        action.setShortcut(cmds.Stage.SHORTCUT)
        menu.addSeparator()
        menu.addAction(self.launch_editor_action)

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
        menu.addAction(self.copy_relpath_action)
        return menu

    def _create_unstaged_context_menu(self, menu, s):
        modified_submodule = (s.modified and
                              s.modified[0] in self.m.submodules)
        if modified_submodule:
            return self._create_modified_submodule_context_menu(menu, s)

        if self.m.stageable():
            action = menu.addAction(qtutils.add_icon(),
                                    N_('Stage Selected'),
                                    cmds.run(cmds.Stage, self.unstaged()))
            action.setShortcut(cmds.Stage.SHORTCUT)

        # Do all of the selected items exist?
        all_exist = all(not i in self.m.unstaged_deleted and core.exists(i)
                        for i in self.staged())

        if all_exist and self.unstaged():
            menu.addAction(self.launch_editor_action)

        if all_exist and s.modified and self.m.stageable():
            menu.addAction(self.launch_difftool_action)

        if s.modified and self.m.stageable():
            if self.m.undoable():
                menu.addSeparator()
                menu.addAction(self.revert_unstaged_edits_action)

        if all_exist and self.unstaged() and not utils.is_win32():
            menu.addSeparator()
            action = menu.addAction(qtutils.file_icon(),
                    cmds.OpenDefaultApp.name(),
                    cmds.run(cmds.OpenDefaultApp, self.unstaged()))
            action.setShortcut(cmds.OpenDefaultApp.SHORTCUT)

            action = menu.addAction(qtutils.open_file_icon(),
                    cmds.OpenParentDir.name(),
                    self._open_parent_dir)
            action.setShortcut(cmds.OpenParentDir.SHORTCUT)

        if all_exist and s.untracked:
            menu.addSeparator()
            if self.move_to_trash_action is not None:
                menu.addAction(self.move_to_trash_action)
            menu.addAction(self.delete_untracked_files_action)
            menu.addSeparator()
            menu.addAction(qtutils.theme_icon('edit-clear.svg'),
                           N_('Add to .gitignore'),
                           cmds.run(cmds.Ignore,
                                map(lambda x: '/' + x, self.untracked())))
        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        menu.addAction(self.copy_relpath_action)
        return menu

    def _create_modified_submodule_context_menu(self, menu, s):
        menu.addAction(qtutils.git_icon(),
                       N_('Launch git-cola'),
                       cmds.run(cmds.OpenRepo, core.abspath(s.modified[0])))

        menu.addAction(self.launch_editor_action)

        if self.m.stageable():
            menu.addSeparator()
            action = menu.addAction(qtutils.add_icon(),
                                    N_('Stage Selected'),
                                    cmds.run(cmds.Stage, self.unstaged()))
            action.setShortcut(cmds.Stage.SHORTCUT)

        menu.addSeparator()
        menu.addAction(self.copy_path_action)
        menu.addAction(self.copy_relpath_action)
        return menu


    def _delete_untracked_files(self):
        cmds.do(cmds.Delete, self.untracked())

    def _trash_untracked_files(self):
        cmds.do(cmds.MoveToTrash, self.untracked())

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

        return selection.State(st, um, m, ut)

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
        return selection.State(self.staged(), self.unmerged(),
                               self.modified(), self.untracked())

    def contents(self):
        return selection.State(self.m.staged, self.m.unmerged,
                               self.m.modified, self.m.untracked)

    def all_files(self):
        c = self.contents()
        return c.staged + c.unmerged + c.modified + c.untracked

    def selected_group(self):
        """A list of selected files in various states of being"""
        return selection.pick(self.selection())

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

    def staged_items(self):
        return self._subtree_selection_items(self.idx_staged)

    def unstaged_items(self):
        return (self.unmerged_items() + self.modified_items() +
                self.untracked_items())

    def modified_items(self):
        return self._subtree_selection_items(self.idx_modified)

    def unmerged_items(self):
        return self._subtree_selection_items(self.idx_unmerged)

    def untracked_items(self):
        return self._subtree_selection_items(self.idx_untracked)

    def _subtree_selection(self, idx, items):
        item = self.topLevelItem(idx)
        return qtutils.tree_selection(item, items)

    def _subtree_selection_items(self, idx):
        item = self.topLevelItem(idx)
        return qtutils.tree_selection_items(item)

    def double_clicked(self, item, idx):
        """Called when an item is double-clicked in the repo status tree."""
        cmds.do(cmds.StageOrUnstage)

    def _open_using_default_app(self):
        cmds.do(cmds.OpenDefaultApp, self.selected_group())

    def _open_parent_dir(self):
        cmds.do(cmds.OpenParentDir, self.selected_group())

    def show_selection(self):
        """Show the selected item."""
        # Sync the selection model
        selected = self.selection()
        selection.selection_model().set_selection(selected)
        self.update_actions(selected=selected)

        selected_indexes = self.selected_indexes()
        if not selected_indexes:
            if self.m.amending():
                cmds.do(cmds.SetDiffText, '')
            else:
                cmds.do(cmds.ResetMode)
            return
        category, idx = selected_indexes[0]
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
            item = self.staged_items()[0]
            cmds.do(cmds.DiffStaged, item.path, deleted=item.deleted)

        # A modified file
        elif category == self.idx_modified:
            item = self.modified_items()[0]
            cmds.do(cmds.Diff, item.path, deleted=item.deleted)

        elif category == self.idx_unmerged:
            item = self.unmerged_items()[0]
            cmds.do(cmds.Diff, item.path)

        elif category == self.idx_untracked:
            item = self.unstaged_items()[0]
            cmds.do(cmds.ShowUntracked, item.path)

    def move_up(self):
        idx = self.selected_idx()
        all_files = self.all_files()
        if idx is None:
            selected_indexes = self.selected_indexes()
            if selected_indexes:
                category, toplevel_idx = selected_indexes[0]
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
            selected_indexes = self.selected_indexes()
            if selected_indexes:
                category, toplevel_idx = selected_indexes[0]
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

    def copy_path(self, absolute=True):
        """Copy a selected path to the clipboard"""
        filename = selection.selection_model().filename()
        qtutils.copy_path(filename, absolute=absolute)

    def copy_relpath(self):
        """Copy a selected relative path to the clipboard"""
        self.copy_path(absolute=False)

    def mimeData(self, items):
        """Return a list of absolute-path URLs"""
        paths = qtutils.paths_from_items(items, item_filter=lambda item:
                                                    not item.deleted
                                                    and core.exists(item.path))
        return qtutils.mimedata_from_paths(paths)

    def mimeTypes(self):
        return qtutils.path_mimetypes()


class StatusFilterWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.main_model = main.model()

        hint = N_('Filter paths...')
        self.text = completion.GitStatusFilterLineEdit(hint=hint, parent=self)
        self.text.setToolTip(hint)
        self.text.hint.enable(True)
        self.setFocusProxy(self.text)
        self._filter = None

        self.main_layout = qtutils.hbox(defs.no_margin, defs.spacing, self.text)
        self.setLayout(self.main_layout)

        self.connect(self.text, SIGNAL('changed()'), self.apply_filter)
        self.connect(self.text, SIGNAL('cleared()'), self.apply_filter)
        self.connect(self.text, SIGNAL('return()'), self.apply_filter)
        self.connect(self.text, SIGNAL('editingFinished()'), self.apply_filter)

    def apply_filter(self):
        text = self.text.value()
        if text == self._filter:
            return
        self._filter = text
        paths = utils.shell_split(text)
        self.main_model.update_path_filter(paths)
