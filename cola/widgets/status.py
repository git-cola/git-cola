from __future__ import division, absolute_import, unicode_literals
import itertools
import os

from qtpy.QtCore import Qt
from qtpy.QtCore import Signal
from qtpy import QtCore
from qtpy import QtWidgets

from ..i18n import N_
from ..models import main
from ..models import prefs
from ..models import selection
from ..widgets import gitignore
from ..widgets import standard
from .. import actions
from .. import cmds
from .. import core
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import settings
from .. import utils
from . import common
from . import completion
from . import defs
from . import text


class StatusWidget(QtWidgets.QWidget):
    """
    Provides a git-status-like repository widget.

    This widget observes the main model and broadcasts
    Qt signals.

    """

    def __init__(self, titlebar, parent, context):
        QtWidgets.QWidget.__init__(self, parent)
        self.context = context

        tooltip = N_('Toggle the paths filter')
        icon = icons.ellipsis()
        self.filter_button = qtutils.create_action_button(tooltip=tooltip,
                                                          icon=icon)
        self.filter_widget = StatusFilterWidget()
        self.filter_widget.hide()
        self.tree = StatusTreeWidget(context, parent=self)
        self.setFocusProxy(self.tree)

        self.main_layout = qtutils.vbox(defs.no_margin, defs.no_spacing,
                                        self.filter_widget, self.tree)
        self.setLayout(self.main_layout)

        self.toggle_action = qtutils.add_action(self, tooltip,
                                                self.toggle_filter,
                                                hotkeys.FILTER)

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


class StatusTreeWidget(QtWidgets.QTreeWidget):
    # Signals
    about_to_update = Signal()
    updated = Signal()

    # Item categories
    idx_header = -1
    idx_staged = 0
    idx_unmerged = 1
    idx_modified = 2
    idx_untracked = 3
    idx_end = 4

    # Read-only access to the mode state
    mode = property(lambda self: self.m.mode)

    def __init__(self, context, parent=None):
        QtWidgets.QTreeWidget.__init__(self, parent)
        self.context = context

        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.headerItem().setHidden(True)
        self.setAllColumnsShowFocus(True)
        self.setSortingEnabled(False)
        self.setUniformRowHeights(True)
        self.setAnimated(True)
        self.setRootIsDecorated(False)
        self.setIndentation(0)
        self.setDragEnabled(True)
        self.setAutoScroll(False)

        ok = icons.ok()
        compare = icons.compare()
        question = icons.question()
        self.add_toplevel_item(N_('Staged'), ok, hide=True)
        self.add_toplevel_item(N_('Unmerged'), compare, hide=True)
        self.add_toplevel_item(N_('Modified'), compare, hide=True)
        self.add_toplevel_item(N_('Untracked'), question, hide=True)

        # Used to restore the selection
        self.old_vscroll = None
        self.old_hscroll = None
        self.old_selection = None
        self.old_contents = None
        self.old_current_item = None
        self.expanded_items = set()

        self.image_formats = qtutils.ImageFormats()

        self.process_selection_action = qtutils.add_action(
            self, cmds.StageOrUnstage.name(), self.stage_selection,
            hotkeys.STAGE_SELECTION)

        self.revert_unstaged_edits_action = qtutils.add_action(
            self, cmds.RevertUnstagedEdits.name(),
            cmds.run(cmds.RevertUnstagedEdits), hotkeys.REVERT)
        self.revert_unstaged_edits_action.setIcon(icons.undo())

        self.launch_difftool_action = qtutils.add_action(
            self, cmds.LaunchDifftool.name(),
            cmds.run(cmds.LaunchDifftool, context=self.context), hotkeys.DIFF)
        self.launch_difftool_action.setIcon(icons.diff())

        self.launch_editor_action = actions.launch_editor(
            self, *hotkeys.ACCEPT)

        if not utils.is_win32():
            self.default_app_action = common.default_app_action(
                    self, self.selected_group)

            self.parent_dir_action = common.parent_dir_action(
                    self, self.selected_group)

            self.terminal_action = common.terminal_action(
                    self, self.selected_group)

        self.up_action = qtutils.add_action(
            self, N_('Move Up'), self.move_up,
            hotkeys.MOVE_UP, hotkeys.MOVE_UP_SECONDARY)

        self.down_action = qtutils.add_action(
            self, N_('Move Down'), self.move_down,
            hotkeys.MOVE_DOWN, hotkeys.MOVE_DOWN_SECONDARY)

        self.copy_path_action = qtutils.add_action(
            self, N_('Copy Path to Clipboard'), copy_path, hotkeys.COPY)
        self.copy_path_action.setIcon(icons.copy())

        self.copy_relpath_action = qtutils.add_action(
            self, N_('Copy Relative Path to Clipboard'),
            copy_relpath, hotkeys.CUT)
        self.copy_relpath_action.setIcon(icons.copy())

        self.copy_leading_path_action = qtutils.add_action(
            self, N_('Copy Leading Path to Clipboard'), copy_leading_path)
        self.copy_leading_path_action.setIcon(icons.copy())

        self.copy_basename_action = qtutils.add_action(
            self, N_('Copy Basename to Clipboard'), copy_basename)
        self.copy_basename_action.setIcon(icons.copy())

        self.copy_customize_action = qtutils.add_action(
                self, N_('Customize...'), lambda: customize_copy_actions(self))
        self.copy_customize_action.setIcon(icons.configure())

        self.view_history_action = qtutils.add_action(
            self, N_('View History...'), view_history, hotkeys.HISTORY)

        self.view_blame_action = qtutils.add_action(
            self, N_('Blame...'), view_blame, hotkeys.BLAME)

        self.annex_add_action = qtutils.add_action(
            self, N_('Add to Git Annex'),
            cmds.run(cmds.AnnexAdd, self.context))

        self.lfs_track_action = qtutils.add_action(
            self, N_('Add to Git LFS'),
            cmds.run(cmds.LFSTrack, self.context))

        # MoveToTrash and Delete use the same shortcut.
        # We will only bind one of them, depending on whether or not the
        # MoveToTrash command is available.  When available, the hotkey
        # is bound to MoveToTrash, otherwise it is bound to Delete.
        if cmds.MoveToTrash.AVAILABLE:
            self.move_to_trash_action = qtutils.add_action(
                self, N_('Move files to trash'),
                self._trash_untracked_files, hotkeys.TRASH)
            self.move_to_trash_action.setIcon(icons.discard())
            delete_shortcut = hotkeys.DELETE_FILE
        else:
            self.move_to_trash_action = None
            delete_shortcut = hotkeys.DELETE_FILE_SECONDARY

        self.delete_untracked_files_action = qtutils.add_action(
            self, N_('Delete Files...'),
            self._delete_untracked_files, delete_shortcut)
        self.delete_untracked_files_action.setIcon(icons.discard())

        about_to_update = self._about_to_update
        self.about_to_update.connect(about_to_update, type=Qt.QueuedConnection)
        self.updated.connect(self.refresh, type=Qt.QueuedConnection)

        self.m = main.model()
        self.m.add_observer(self.m.message_about_to_update,
                            self.about_to_update.emit)
        self.m.add_observer(self.m.message_updated, self.updated.emit)

        self.itemSelectionChanged.connect(self.show_selection)
        self.itemDoubleClicked.connect(self.double_clicked)
        self.itemCollapsed.connect(lambda x: self.update_column_widths())
        self.itemExpanded.connect(lambda x: self.update_column_widths())

    def add_toplevel_item(self, txt, icon, hide=False):
        font = self.font()
        if prefs.bold_headers():
            font.setBold(True)
        else:
            font.setItalic(True)

        item = QtWidgets.QTreeWidgetItem(self)
        item.setFont(0, font)
        item.setText(0, txt)
        item.setIcon(0, icon)
        if prefs.bold_headers():
            item.setBackground(0, self.palette().midlight())
        if hide:
            item.setHidden(True)

    def restore_selection(self):
        if not self.old_selection or not self.old_contents:
            return
        old_c = self.old_contents
        old_s = self.old_selection
        new_c = self.contents()

        def mkselect(lst, widget_getter):
            def select(item, current=False):
                idx = lst.index(item)
                item = widget_getter(idx)
                if current:
                    self.setCurrentItem(item)
                item.setSelected(True)
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
                    self.blockSignals(True)
                    self.setCurrentItem(item)
                    item.setSelected(True)
                    self.blockSignals(False)
                    self.show_selection()
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

    def restore_scrollbars(self):
        vscroll = self.verticalScrollBar()
        if vscroll and self.old_vscroll is not None:
            vscroll.setValue(self.old_vscroll)
            self.old_vscroll = None

        hscroll = self.horizontalScrollBar()
        if hscroll and self.old_hscroll is not None:
            hscroll.setValue(self.old_hscroll)
            self.old_hscroll = None

    def stage_selection(self):
        """Stage or unstage files according to the selection"""
        selected_indexes = self.selected_indexes()
        if selected_indexes:
            category, idx = selected_indexes[0]
            # A header item e.g. 'Staged', 'Modified', etc.
            if category == self.idx_header:
                if idx == self.idx_staged:
                    cmds.do(cmds.UnstageAll)
                elif idx == self.idx_modified:
                    cmds.do(cmds.StageModified)
                elif idx == self.idx_untracked:
                    cmds.do(cmds.StageUntracked)
                else:
                    pass  # Do nothing for unmerged items, by design
                return
        cmds.do(cmds.StageOrUnstage)

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

    def _about_to_update(self):
        self.save_scrollbars()
        self.save_selection()

    def save_scrollbars(self):
        vscroll = self.verticalScrollBar()
        if vscroll:
            self.old_vscroll = vscroll.value()

        hscroll = self.horizontalScrollBar()
        if hscroll:
            self.old_hscroll = hscroll.value()

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

    def refresh(self):
        self.set_staged(self.m.staged)
        self.set_modified(self.m.modified)
        self.set_unmerged(self.m.unmerged)
        self.set_untracked(self.m.untracked)
        self.update_column_widths()
        self.update_actions()
        self.restore_selection()
        self.restore_scrollbars()

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
        deleted_set = set([path for path in items if not core.exists(path)])
        self._set_subtree(items, self.idx_unmerged,
                          deleted_set=deleted_set)

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
        hide = not bool(items)
        parent.setHidden(hide)

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
        menu = qtutils.create_menu('Status', self)
        selected_indexes = self.selected_indexes()
        if selected_indexes:
            category, idx = selected_indexes[0]
            # A header item e.g. 'Staged', 'Modified', etc.
            if category == self.idx_header:
                return self._create_header_context_menu(menu, idx)

        if s.staged:
            self._create_staged_context_menu(menu, s)
        elif s.unmerged:
            self._create_unmerged_context_menu(menu, s)
        else:
            self._create_unstaged_context_menu(menu, s)

        if not utils.is_win32():
            if not menu.isEmpty():
                menu.addSeparator()
            if not selection.selection_model().is_empty():
                menu.addAction(self.default_app_action)
                menu.addAction(self.parent_dir_action)
            menu.addAction(self.terminal_action)

        self._add_copy_actions(menu)

        return menu

    def _add_copy_actions(self, menu):
        """Add the "Copy" sub-menu"""
        enabled = selection.selection_model().filename() is not None
        self.copy_path_action.setEnabled(enabled)
        self.copy_relpath_action.setEnabled(enabled)
        self.copy_leading_path_action.setEnabled(enabled)
        self.copy_basename_action.setEnabled(enabled)
        copy_icon = icons.copy()

        menu.addSeparator()
        copy_menu = QtWidgets.QMenu(N_('Copy...'), menu)
        menu.addMenu(copy_menu)

        copy_menu.setIcon(copy_icon)
        copy_menu.addAction(self.copy_path_action)
        copy_menu.addAction(self.copy_relpath_action)
        copy_menu.addAction(self.copy_leading_path_action)
        copy_menu.addAction(self.copy_basename_action)

        current_settings = settings.Settings()
        current_settings.load()

        copy_formats = current_settings.copy_formats
        if copy_formats:
            copy_menu.addSeparator()

        for entry in copy_formats:
            name = entry.get('name', '')
            fmt = entry.get('format', '')
            if name and fmt:
                action = copy_menu.addAction(name, lambda fmt=fmt: copy_format(fmt))
                action.setIcon(copy_icon)
                action.setEnabled(enabled)

        copy_menu.addSeparator()
        copy_menu.addAction(self.copy_customize_action)


    def _create_header_context_menu(self, menu, idx):
        if idx == self.idx_staged:
            menu.addAction(icons.remove(), N_('Unstage All'),
                           cmds.run(cmds.UnstageAll))
            return menu
        elif idx == self.idx_unmerged:
            action = menu.addAction(icons.add(), cmds.StageUnmerged.name(),
                                    cmds.run(cmds.StageUnmerged))
            action.setShortcut(hotkeys.STAGE_SELECTION)
            return menu
        elif idx == self.idx_modified:
            action = menu.addAction(icons.add(), cmds.StageModified.name(),
                                    cmds.run(cmds.StageModified))
            action.setShortcut(hotkeys.STAGE_SELECTION)
            return menu

        elif idx == self.idx_untracked:
            action = menu.addAction(icons.add(), cmds.StageUntracked.name(),
                                    cmds.run(cmds.StageUntracked))
            action.setShortcut(hotkeys.STAGE_SELECTION)
            return menu

    def _create_staged_context_menu(self, menu, s):
        if s.staged[0] in self.m.submodules:
            return self._create_staged_submodule_context_menu(menu, s)

        if self.m.unstageable():
            action = menu.addAction(icons.remove(), N_('Unstage Selected'),
                                    cmds.run(cmds.Unstage, self.staged()))
            action.setShortcut(hotkeys.STAGE_SELECTION)

        menu.addAction(self.launch_editor_action)

        # Do all of the selected items exist?
        all_exist = all(i not in self.m.staged_deleted and core.exists(i)
                        for i in self.staged())

        if all_exist:
            menu.addAction(self.launch_difftool_action)

        if self.m.undoable():
            menu.addAction(self.revert_unstaged_edits_action)

        menu.addAction(self.view_history_action)
        menu.addAction(self.view_blame_action)
        return menu

    def _create_staged_submodule_context_menu(self, menu, s):
        menu.addAction(icons.cola(), N_('Launch git-cola'),
                       cmds.run(cmds.OpenRepo,
                                core.abspath(s.staged[0])))

        action = menu.addAction(icons.remove(), N_('Unstage Selected'),
                                cmds.run(cmds.Unstage, self.staged()))
        action.setShortcut(hotkeys.STAGE_SELECTION)

        menu.addAction(self.view_history_action)
        return menu

    def _create_unmerged_context_menu(self, menu, s):
        menu.addAction(self.launch_difftool_action)

        action = menu.addAction(icons.add(), N_('Stage Selected'),
                                cmds.run(cmds.Stage, self.unstaged()))
        action.setShortcut(hotkeys.STAGE_SELECTION)

        menu.addAction(self.launch_editor_action)
        menu.addAction(self.view_history_action)
        menu.addAction(self.view_blame_action)
        return menu

    def _create_unstaged_context_menu(self, menu, s):
        modified_submodule = (s.modified and
                              s.modified[0] in self.m.submodules)
        if modified_submodule:
            return self._create_modified_submodule_context_menu(menu, s)

        if self.m.stageable():
            action = menu.addAction(icons.add(), N_('Stage Selected'),
                                    cmds.run(cmds.Stage, self.unstaged()))
            action.setShortcut(hotkeys.STAGE_SELECTION)

        if not selection.selection_model().is_empty():
            menu.addAction(self.launch_editor_action)

        # Do all of the selected items exist?
        all_exist = all(i not in self.m.unstaged_deleted and core.exists(i)
                        for i in self.staged())

        if all_exist and s.modified and self.m.stageable():
            menu.addAction(self.launch_difftool_action)

        if s.modified and self.m.stageable():
            if self.m.undoable():
                menu.addSeparator()
                menu.addAction(self.revert_unstaged_edits_action)

        if all_exist and s.untracked:
            # Git Annex / Git LFS
            annex = self.m.annex
            lfs = core.find_executable('git-lfs')
            if annex or lfs:
                menu.addSeparator()
            if annex:
                menu.addAction(self.annex_add_action)
            if lfs:
                menu.addAction(self.lfs_track_action)

            menu.addSeparator()
            if self.move_to_trash_action is not None:
                menu.addAction(self.move_to_trash_action)
            menu.addAction(self.delete_untracked_files_action)
            menu.addSeparator()
            menu.addAction(icons.edit(), N_('Add to .gitignore'),
                           gitignore.gitignore_view)

        if not selection.selection_model().is_empty():
            menu.addAction(self.view_history_action)
            menu.addAction(self.view_blame_action)
        return menu

    def _create_modified_submodule_context_menu(self, menu, s):
        menu.addAction(icons.cola(), N_('Launch git-cola'),
                       cmds.run(cmds.OpenRepo, core.abspath(s.modified[0])))

        if self.m.stageable():
            menu.addSeparator()
            action = menu.addAction(icons.add(), N_('Stage Selected'),
                                    cmds.run(cmds.Stage, self.unstaged()))
            action.setShortcut(hotkeys.STAGE_SELECTION)

        menu.addAction(self.view_history_action)
        return menu

    def _delete_untracked_files(self):
        cmds.do(cmds.Delete, self.untracked())

    def _trash_untracked_files(self):
        cmds.do(cmds.MoveToTrash, self.untracked())

    def selected_path(self):
        s = self.single_selection()
        return s.staged or s.unmerged or s.modified or s.untracked or None

    def single_selection(self):
        """Scan across staged, modified, etc. and return a single item."""
        staged = None
        unmerged = None
        modified = None
        untracked = None

        s = self.selection()
        if s.staged:
            staged = s.staged[0]
        elif s.unmerged:
            unmerged = s.unmerged[0]
        elif s.modified:
            modified = s.modified[0]
        elif s.untracked:
            untracked = s.untracked[0]

        return selection.State(staged, unmerged, modified, untracked)

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
                if item is not None:
                    self.select_item(item)
                return
            idx -= len(content)

    def scroll_to_item(self, item):
        # First, scroll to the item, but keep the original hscroll
        hscroll = None
        hscrollbar = self.horizontalScrollBar()
        if hscrollbar:
            hscroll = hscrollbar.value()
        self.scrollToItem(item)
        if hscroll is not None:
            hscrollbar.setValue(hscroll)

    def select_item(self, item):
        self.scroll_to_item(item)
        self.setCurrentItem(item)
        item.setSelected(True)

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

    def show_selection(self):
        """Show the selected item."""
        self.scroll_to_item(self.currentItem())
        # Sync the selection model
        selected = self.selection()
        selection_model = selection.selection_model()
        selection_model.set_selection(selected)
        self.update_actions(selected=selected)

        selected_indexes = self.selected_indexes()
        if not selected_indexes:
            if self.m.amending():
                cmds.do(cmds.SetDiffText, '')
            else:
                cmds.do(cmds.ResetMode)
            return

        # A header item e.g. 'Staged', 'Modified', etc.
        category, idx = selected_indexes[0]
        header = category == self.idx_header
        if header:
            cls = {
                self.idx_staged: cmds.DiffStagedSummary,
                self.idx_modified: cmds.Diffstat,
                # TODO implement UnmergedSummary
                # self.idx_unmerged: cmds.UnmergedSummary,
                self.idx_untracked: cmds.UntrackedSummary,
            }.get(idx, cmds.Diffstat)
            cmds.do(cls)
            return

        staged = category == self.idx_staged
        modified = category == self.idx_modified
        unmerged = category == self.idx_unmerged
        untracked = category == self.idx_untracked

        if staged:
            item = self.staged_items()[0]
        elif unmerged:
            item = self.unmerged_items()[0]
        elif modified:
            item = self.modified_items()[0]
        elif untracked:
            item = self.unstaged_items()[0]
        else:
            item = None  # this shouldn't happen
        assert(item is not None)

        path = item.path
        deleted = item.deleted
        image = self.image_formats.ok(path)

        # Images are diffed differently
        if image:
            cmds.do(cmds.DiffImage, path, deleted,
                    staged, modified, unmerged, untracked)
        elif staged:
            cmds.do(cmds.DiffStaged, path, deleted=deleted)
        elif modified:
            cmds.do(cmds.Diff, path, deleted=deleted)
        elif unmerged:
            cmds.do(cmds.Diff, path)
        elif untracked:
            cmds.do(cmds.ShowUntracked, path)

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

    def _item_filter(self, item):
        return not item.deleted and core.exists(item.path)

    def mimeData(self, items):
        """Return a list of absolute-path URLs"""
        paths = qtutils.paths_from_items(items, item_filter=self._item_filter)
        return qtutils.mimedata_from_paths(paths)

    def mimeTypes(self):
        return qtutils.path_mimetypes()


def view_blame():
    """Signal that we should view blame for paths."""
    cmds.do(cmds.BlamePaths, selection.union(selection.selection_model()))


def view_history():
    """Signal that we should view history for paths."""
    cmds.do(cmds.VisualizePaths,
            selection.union(selection.selection_model()))


def copy_path(absolute=True):
    """Copy a selected path to the clipboard"""
    filename = selection.selection_model().filename()
    qtutils.copy_path(filename, absolute=absolute)


def copy_relpath():
    """Copy a selected relative path to the clipboard"""
    copy_path(absolute=False)


def copy_basename():
    filename = os.path.basename(selection.selection_model().filename())
    basename, ext = os.path.splitext(filename)
    qtutils.copy_path(basename, absolute=False)


def copy_leading_path():
    """Copy the selected leading path to the clipboard"""
    filename = selection.selection_model().filename()
    dirname = os.path.dirname(filename)
    qtutils.copy_path(dirname, absolute=False)


def copy_format(fmt):
    values = {}
    values['path'] = path = selection.selection_model().filename()
    values['abspath'] = abspath = os.path.abspath(path)
    values['absdirname'] = os.path.dirname(abspath)
    values['dirname'] = os.path.dirname(path)
    values['filename'] = os.path.basename(path)
    values['basename'], values['ext'] = os.path.splitext(os.path.basename(path))
    qtutils.set_clipboard(fmt % values)


def show_help():
    help_text = N_(r"""
        Format String Variables
        -----------------------
          %(path)s  =  relative file path
       %(abspath)s  =  absolute file path
       %(dirname)s  =  relative directory path
    %(absdirname)s  =  absolute directory path
      %(filename)s  =  file basename
      %(basename)s  =  file basename without extension
           %(ext)s  =  file extension
""")
    title = N_('Help - Custom Copy Actions')
    return text.text_dialog(help_text, title)


class StatusFilterWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.main_model = main.model()

        hint = N_('Filter paths...')
        self.text = completion.GitStatusFilterLineEdit(hint=hint, parent=self)
        self.text.setToolTip(hint)
        self.setFocusProxy(self.text)
        self._filter = None

        self.main_layout = qtutils.hbox(defs.no_margin, defs.spacing, self.text)
        self.setLayout(self.main_layout)

        text = self.text
        text.changed.connect(self.apply_filter)
        text.cleared.connect(self.apply_filter)
        text.enter.connect(self.apply_filter)
        text.editingFinished.connect(self.apply_filter)

    def apply_filter(self):
        text = self.text.value()
        if text == self._filter:
            return
        self._filter = text
        paths = utils.shell_split(text)
        self.main_model.update_path_filter(paths)


def customize_copy_actions(parent):
    """Customize copy actions"""
    dialog = CustomizeCopyActions(parent)
    dialog.show()
    dialog.raise_()
    dialog.exec_()


class CustomizeCopyActions(standard.Dialog):

    def __init__(self, parent):
        standard.Dialog.__init__(self, parent=parent)
        self.setWindowTitle(N_('Custom Copy Actions'))

        self.table = QtWidgets.QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([
            N_('Action Name'),
            N_('Format String'),
        ])
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)

        self.add_button = qtutils.create_button(N_('Add'))
        self.remove_button = qtutils.create_button(N_('Remove'))
        self.remove_button.setEnabled(False)
        self.show_help_button = qtutils.create_button(N_('Show Help'))
        self.show_help_button.setShortcut(hotkeys.QUESTION)

        self.close_button = qtutils.close_button()
        self.save_button = qtutils.ok_button(N_('Save'))

        self.buttons = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                    self.add_button,
                                    self.remove_button,
                                    self.show_help_button,
                                    qtutils.STRETCH,
                                    self.close_button,
                                    self.save_button)

        layout = qtutils.vbox(defs.margin, defs.spacing,
                              self.table, self.buttons)
        self.setLayout(layout)

        qtutils.connect_button(self.add_button, self.add)
        qtutils.connect_button(self.remove_button, self.remove)
        qtutils.connect_button(self.show_help_button, show_help)
        qtutils.connect_button(self.close_button, self.reject)
        qtutils.connect_button(self.save_button, self.save)
        qtutils.add_close_action(self)
        self.table.itemSelectionChanged.connect(self.table_selection_changed)

        self.init_size(parent=parent)

        self.settings = settings.Settings()
        QtCore.QTimer.singleShot(0, self.reload_settings)

    def reload_settings(self):
        # Called once after the GUI is initialized
        self.settings.load()
        table = self.table
        for entry in self.settings.copy_formats:
            name_string = entry.get('name', '')
            format_string = entry.get('format', '')
            if name_string and format_string:
                name = QtWidgets.QTableWidgetItem(name_string)
                fmt = QtWidgets.QTableWidgetItem(format_string)
                rows = table.rowCount()
                table.setRowCount(rows + 1)
                table.setItem(rows, 0, name)
                table.setItem(rows, 1, fmt)

    def export_state(self):
        state = super(CustomizeCopyActions, self).export_state()
        standard.export_header_columns(self.table, state)
        return state

    def apply_state(self, state):
        result = super(CustomizeCopyActions, self).apply_state(state)
        standard.apply_header_columns(self.table, state) and result
        return result

    def add(self):
        self.table.setFocus(True)
        rows = self.table.rowCount()
        self.table.setRowCount(rows + 1)

        name = QtWidgets.QTableWidgetItem(N_('Name'))
        fmt = QtWidgets.QTableWidgetItem(r'%(path)s')
        self.table.setItem(rows, 0, name)
        self.table.setItem(rows, 1, fmt)

        self.table.setCurrentCell(rows, 0)
        self.table.editItem(name)

    def remove(self):
        """Remove selected items"""
        # Gather a unique set of rows and remove them in reverse order
        rows = set()
        items = self.table.selectedItems()
        for item in items:
            rows.add(self.table.row(item))

        for row in reversed(sorted(rows)):
            self.table.removeRow(row)

    def save(self):
        copy_formats = []
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0)
            fmt = self.table.item(row, 1)
            if name and fmt:
                entry = {
                    'name': name.text(),
                    'format': fmt.text(),
                }
                copy_formats.append(entry)

        while self.settings.copy_formats:
            self.settings.copy_formats.pop()

        self.settings.copy_formats.extend(copy_formats)
        self.settings.save()

        self.accept()

    def table_selection_changed(self):
        items = self.table.selectedItems()
        self.remove_button.setEnabled(bool(items))
