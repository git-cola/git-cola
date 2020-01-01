from __future__ import division, absolute_import, unicode_literals
import os
import typing
from collections import defaultdict
from enum import IntEnum
from functools import partial

from qtpy.QtCore import Qt
from qtpy.QtCore import Signal
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import QtGui

from . import completion
from . import defs
from . import text
from .. import cmds
from .. import core
from .. import gitcmds
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import settings
from .. import utils
from ..enums.file_nodes import Node, Folder, Untracked, Modified, Deleted, File, Unmerged
from ..i18n import N_
from ..models import prefs
from ..models import selection
from ..models.main import MainModel
from ..qtutils import get
from ..widgets import gitignore
from ..widgets import standard

UNSTAGED = 'Unstaged'
STAGED = 'Staged'
FIRST = 0
COLLAPSE_CHILDREN = 15

class NotSet:
    pass


_git_status_node_type_map = {
    gitcmds.StatusMarkers.added: Untracked, # staged new file
    gitcmds.StatusMarkers.copied: Untracked, # staged copy of another file
    gitcmds.StatusMarkers.deleted: Deleted,
    gitcmds.StatusMarkers.modified: Modified,
    gitcmds.StatusMarkers.renamed: Modified,
    gitcmds.StatusMarkers.type_changed: Modified,
    gitcmds.StatusMarkers.unknown: Untracked,
    gitcmds.StatusMarkers.unmerged: Unmerged,
    gitcmds.StatusMarkers.untracked: Untracked, # never staged
}


class StatusWidget(QtWidgets.QFrame):
    """
    Provides a git-status-like repository widget.

    This widget observes the main model and broadcasts
    Qt signals.

    """

    def __init__(self, context, parent):
        QtWidgets.QFrame.__init__(self, parent)
        self.context = context
        self.tree = StatusTreeWidget(context, parent=self)
        self.setFocusProxy(self.tree)

        self.main_layout = qtutils.vbox(
            defs.no_margin,
            defs.no_spacing,
            self.tree
        )
        self.setLayout(self.main_layout)

    def set_initial_size(self):
        self.setMaximumWidth(222)
        QtCore.QTimer.singleShot(
            1, lambda: self.setMaximumWidth(2 ** 13))

    def refresh(self):
        # self.tree.show_selection()
        print('GUTTED TreeWidget.refresh() is called. Prune!')

_file_states_labels = {
    Modified: '\u270e',
    Untracked: '\u2795',
    Deleted: '\u2796',
    Folder: '\U0001F4C2'
}

_folder_icon = QtGui.QIcon.fromTheme('folder')
_file_icon = QtGui.QIcon.fromTheme('text-x-generic')

_qt_check_states = {
    True: QtCore.Qt.Checked,
    False: QtCore.Qt.Unchecked,
    NotSet: NotSet
}

_qt_check_states_reversed = {
    v: k
    for k, v in _qt_check_states.items()
}
_qt_check_states_reversed[None] = NotSet


class ItemData(IntEnum):
    """
    We store additional data in first column's "data" structure.
    Multiple data points can be stored this way.
    Each data slot needs an index that is >= QtWidgets.QTreeWidgetItem.UserType (1000)
    """
    # (Don't confuse with QTreeWidgetItem Type value which denotes context menu differences)
    full_path = QtWidgets.QTreeWidgetItem.UserType + 3
    is_staged = QtWidgets.QTreeWidgetItem.UserType + 4
    label = QtWidgets.QTreeWidgetItem.UserType + 1
    name = QtWidgets.QTreeWidgetItem.UserType + 2
    node_type = QtWidgets.QTreeWidgetItem.UserType + 5

    @staticmethod
    def set_data(item, data_type, value):
        """
        :type item: QtWidgets.QTreeWidgetItem
        :type data_type: int
        :type value: typing.Any
        """
        item.setData(0, data_type, value)

    @staticmethod
    def get_data(item, data_type):
        """
        :type item: QtWidgets.QTreeWidgetItem
        :type data_type: int
        :rtype: typing.Any
        """
        return item.data(0, data_type)


def NodeFromItem(item):
    try:
        return ItemData.get_data(item, ItemData.node_type)(
            ItemData.get_data(item, ItemData.name),
            full_path = ItemData.get_data(item, ItemData.full_path),
            is_staged = ItemData.get_data(item, ItemData.is_staged)
        )
    except TypeError:
        return None


def render_tree(tree, selected_node, parent):

    stats = defaultdict(int)
    selected_item = None

    # sort folders first
    nodes = sorted([
        (
            1 if isinstance(node, Folder) else 2,
            name,
            node
        )
        for name, node in tree.items()
    ])

    for _, _, node in nodes:
        check_state = _qt_check_states[node.is_staged]
        node_type = type(node)

        i = QtWidgets.QTreeWidgetItem(parent)

        if node_type is Folder:
            sub_stats, sub_selected_item = render_tree(node, selected_node, i)
            selected_item = selected_item or sub_selected_item

            # expand only if:
            # 1. number of *direct* children is less than COLLAPSE_CHILDREN OR
            # 2. selected_item is in children tree
            i.setExpanded(bool(
                len(node) < COLLAPSE_CHILDREN or
                sub_selected_item
            ))

            label_parts = []
            for state, state_value in sub_stats.items():
                stats[state] += state_value
                label_parts.append(
                    '%s%s' % (
                        state_value,
                        _file_states_labels[state]
                    )
                )
            node_label = '%s %s (%s)' % (
                _file_states_labels[Folder],
                node.name,
                ' '.join(label_parts),
            )
        else:
            stats[node_type] += 1
            node_label = '%s %s' % (
                _file_states_labels[node_type], node.name,
            )

        i.setText(FIRST, node_label)

        # this allows keyboard-less, right-click-less action.
        # imagine touch-based interfaces, where there is only "left-click" possible
        # check == change of state / bucket
        if check_state is NotSet:
            pass
        else:
            i.setCheckState(0, check_state)

        ItemData.set_data(i, ItemData.full_path, node.full_path)
        ItemData.set_data(i, ItemData.is_staged, node.is_staged)
        ItemData.set_data(i, ItemData.node_type, node_type)
        ItemData.set_data(i, ItemData.name, node.name)

        if selected_node is not None and selected_item is None and selected_node == node:
            selected_item = i
            selected_node = None # to turn off futher searches

    return stats, selected_item


def _fold_into_tree(full_path, tree, T, **params):
    path_parts = full_path.split('/') # not OS-adapted. Git always uses '/'
    file_name = path_parts.pop(-1)
    for i, folder_name in enumerate(path_parts):
        folder = tree.get(folder_name)
        if folder is None:
            folder = Folder(folder_name, full_path='/'.join(path_parts[:i+1]), **params)
        tree[folder_name] = folder
        tree = folder
    tree[file_name] = T(file_name, full_path=full_path, **params)


FileTreeDict = typing.Dict[str, Node]


def _full_path_list_to_dict(items, T, tree_data=None, **params):
    tree_data = tree_data or {}

    for full_path in items:
        _fold_into_tree(
            full_path,
            tree_data,
            T,
            **params
        )

    return tree_data


# pylint: disable=too-many-ancestors
class StatusTreeWidget(QtWidgets.QTreeWidget):
    # Signals
    about_to_update = Signal()
    updated = Signal()
    diff_text_changed = Signal()

    # Item categories
    idx_header = -1
    idx_staged = 0
    idx_unstaged = 1
    idx_modified = 2
    idx_untracked = 3
    idx_end = 4

    # stores instance of Node subclass of element we need to select on next refresh
    selected_node = None

    # Read-only access to the mode state
    mode = property(lambda self: self.m.mode)

    def __init__(self, context, parent=None):
        QtWidgets.QTreeWidget.__init__(self, parent)
        self.context = context
        self.selection_model = context.selection

        self.headerItem().setHidden(True)
        self.setAllColumnsShowFocus(True)
        self.setAlternatingRowColors(True)
        self.setAutoScroll(False)
        self.setDragEnabled(False)
        self.setRootIsDecorated(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setSortingEnabled(False)
        self.setUniformRowHeights(True)

        if not prefs.status_indent(context):
            self.setIndentation(0)

        self._add_toplevel_item(N_(STAGED), icons.ok(), hide=False)
        self._add_toplevel_item(N_(UNSTAGED), icons.question(), hide=False)

        # Used to restore the selection
        self.old_vscroll = None
        self.old_hscroll = None
        self.old_selection = None
        self.old_contents = None
        self.old_current_item = None

        self.image_formats = qtutils.ImageFormats()

        self.revert_unstaged_edits_action = qtutils.add_action(
            self,
            cmds.RevertUnstagedEdits.name(),
            cmds.run(
                cmds.RevertUnstagedEdits,
                context
            ),
            hotkeys.REVERT
        )
        self.revert_unstaged_edits_action.setIcon(icons.undo())

        self.launch_difftool_action = qtutils.add_action(
            self,
            cmds.LaunchDifftool.name(),
            cmds.run(cmds.LaunchDifftool, context),
            hotkeys.DIFF
        )
        self.launch_difftool_action.setIcon(icons.diff())

        self.copy_path_action = qtutils.add_action(
            self, N_('Copy Path to Clipboard'),
            partial(copy_path, context), hotkeys.COPY)
        self.copy_path_action.setIcon(icons.copy())

        self.copy_relpath_action = qtutils.add_action(
            self, N_('Copy Relative Path to Clipboard'),
            partial(copy_relpath, context), hotkeys.CUT)
        self.copy_relpath_action.setIcon(icons.copy())

        self.copy_leading_path_action = qtutils.add_action(
            self, N_('Copy Leading Path to Clipboard'),
            partial(copy_leading_path, context))
        self.copy_leading_path_action.setIcon(icons.copy())

        self.copy_basename_action = qtutils.add_action(
            self, N_('Copy Basename to Clipboard'),
            partial(copy_basename, context))
        self.copy_basename_action.setIcon(icons.copy())

        self.copy_customize_action = qtutils.add_action(
            self, N_('Customize...'),
            partial(customize_copy_actions, context, self))
        self.copy_customize_action.setIcon(icons.configure())

        self.view_history_action = qtutils.add_action(
            self, N_('View History...'), partial(view_history, context),
            hotkeys.HISTORY)

        self.view_blame_action = qtutils.add_action(
            self, N_('Blame...'),
            partial(view_blame, context), hotkeys.BLAME)

        self.annex_add_action = qtutils.add_action(
            self, N_('Add to Git Annex'), cmds.run(cmds.AnnexAdd, context))

        self.lfs_track_action = qtutils.add_action(
            self, N_('Add to Git LFS'), cmds.run(cmds.LFSTrack, context))

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
        self.diff_text_changed.connect(
            self._make_current_item_visible, type=Qt.QueuedConnection)

        self.m = m = context.model # type: MainModel
        m.add_observer(m.message_about_to_update, self.about_to_update.emit)
        m.add_observer(m.message_updated, self.updated.emit)
        m.add_observer(m.message_diff_text_changed,
                            self.diff_text_changed.emit)

        # self.itemSelectionChanged.connect(self._handle_item_selection_changed)
        self.currentItemChanged.connect(self._handle_item_focused)
        self.itemActivated.connect(self._handle_item_activated)
        self.itemChanged.connect(self._handle_item_changed)

        self.itemCollapsed.connect(lambda x: self._update_column_widths())
        self.itemExpanded.connect(lambda x: self._update_column_widths())

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._handle_context_menu)

    def _handle_context_menu(self, point):
        item = self.itemAt(point)
        if item:
            node = NodeFromItem(item)
            if node:
                menu = self._create_context_menu(node)
                menu.exec_(self.mapToGlobal(point))

    def _stage_full_path(self, full_path, node_type):
        context = self.context
        cmds.do(cmds.StageHinted, context, [full_path], [node_type])

    def _unstage_full_path(self, full_path, node_type):
        context = self.context
        cmds.do(cmds.UnstageHinted, context, [full_path], [node_type])

    def _determine_next_focus(self, item):
        index = self.indexFromItem(item)
        row = index.row()

        # by default we shift focus to NEXT sibling
        next_index = index.siblingAtRow(row + 1)
        if next_index.isValid():
            return self.itemFromIndex(next_index)

        # if we are here, we don't have NEXT sibling,
        # so we have to go for PRIOR sibling
        if row > 0:
            next_index = index.siblingAtRow(row - 1)
            return self.itemFromIndex(next_index)

        # if we are here there are no valid siblings. (We were the only one)
        # Let's go for parent's siblings
        next_index = index.parent()
        if next_index.isValid():
            return self._determine_next_focus(self.itemFromIndex(next_index))

        # if we are here, no valid parents.
        return None

    # @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, int)
    def _handle_item_changed(self, item, column_index):
        """
        Hanlder for events when line item is changed.
        In our case, because the only change action possible is check/uncheck
        this is the only action we check for
        """
        is_checked = _qt_check_states_reversed[item.checkState(0)]
        is_staged = ItemData.get_data(item, ItemData.is_staged)
        full_path = ItemData.get_data(item, ItemData.full_path)
        node_type = ItemData.get_data(item, ItemData.node_type)

        next_item = self._determine_next_focus(item)
        if next_item:
            self.selected_node = NodeFromItem(next_item)
            self.setCurrentItem(next_item)

        if is_staged is False and is_checked:
            self._stage_full_path(full_path, node_type)
        elif is_staged is True and not is_checked:
            self._unstage_full_path(full_path, node_type)

    def _handle_item_activated(self, item, column_index):
        is_staged = ItemData.get_data(item, ItemData.is_staged)
        full_path = ItemData.get_data(item, ItemData.full_path)
        node_type = ItemData.get_data(item, ItemData.node_type)

        next_item = self._determine_next_focus(item)
        if next_item:
            self.selected_node = NodeFromItem(next_item)
            self.setCurrentItem(next_item)

        if is_staged is False:
            self._stage_full_path(full_path, node_type)
        elif is_staged is True:
            self._unstage_full_path(full_path, node_type)

    # @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, QtWidgets.QTreeWidgetItem)
    def _handle_item_focused(self, item, prior_item):
        """
        Qt-native slot firing when focus (singular selection) moves from
        one item in the tree to another one.

        Used mostly to drigger detail views specific for that single focused item.

        :type item: QtWidgets.QTreeWidgetItem
        :type prior_item: QtWidgets.QTreeWidgetItem
        """
        self.scrollToItem(item)

        node = NodeFromItem(item)
        if isinstance(node, File):
            self._update_actions(node)
            s = self.context.selection
            s.set_selection_from_node(node)
            self._show_diff_for_selection(node)

    def _make_current_item_visible(self):
        item = self.currentItem()
        if item:
            self.scroll_to_item(item)

    def _add_toplevel_item(self, txt, icon, hide=False):
        context = self.context
        font = self.font()
        if prefs.bold_headers(context):
            font.setBold(True)
        else:
            font.setItalic(True)

        item = QtWidgets.QTreeWidgetItem(self)
        item.setFont(0, font)
        item.setText(0, txt)
        item.setIcon(0, icon)
        if prefs.bold_headers(context):
            item.setBackground(0, self.palette().midlight())
        if hide:
            item.setHidden(True)
        item.setExpanded(True)

    def _restore_scrollbars(self):
        vscroll = self.verticalScrollBar()
        if vscroll and self.old_vscroll is not None:
            vscroll.setValue(self.old_vscroll)
            self.old_vscroll = None

        hscroll = self.horizontalScrollBar()
        if hscroll and self.old_hscroll is not None:
            hscroll.setValue(self.old_hscroll)
            self.old_hscroll = None

    def _about_to_update(self):
        self._save_scrollbars()
        self._save_selection()

    def _save_scrollbars(self):
        vscroll = self.verticalScrollBar()
        if vscroll:
            self.old_vscroll = get(vscroll)

        hscroll = self.horizontalScrollBar()
        if hscroll:
            self.old_hscroll = get(hscroll)

    def _save_selection(self):
        item = self.currentItem()
        if item:
            self.selected_node = NodeFromItem(item)

    def refresh(self):
        m = self.m
        staged = m.locals_staged or {}
        unstaged = m.locals_unstaged or {}

        staged_dict = {}
        unstaged_dict = {}

        for marker, node_type in _git_status_node_type_map.items():
            staged_dict = _full_path_list_to_dict(
                staged.get(marker, []),
                node_type,
                staged_dict,
                is_staged = True
            )
            unstaged_dict = _full_path_list_to_dict(
                unstaged.get(marker, []),
                node_type,
                unstaged_dict,
                is_staged = False
            )

        self._set_subtree(
            staged_dict,
            self.idx_staged
        )
        self._set_subtree(
            unstaged_dict,
            self.idx_unstaged
        )

        self._update_column_widths()
        self._restore_scrollbars()

    def _update_actions(self, node):
        can_revert_edits = (not node.is_staged) and isinstance(node, File)
        self.revert_unstaged_edits_action.setEnabled(can_revert_edits)

    def _set_subtree(self, items, top_item_index):
        """Add a list of items to a treewidget item."""

        # show_totals = prefs.status_show_totals(self.context)

        with qtutils.BlockSignals(self):
            parent = self.topLevelItem(top_item_index)

            # sip v4.14.7 and below leak memory in parent.takeChildren()
            # so we use this backwards-compatible construct instead
            # while parent.takeChild(0) is not None:
            #     pass
            parent.takeChildren()

            stats, selected_item = render_tree(items, self.selected_node, parent)

            if selected_item:
                # selected_item.setExpanded(True)
                self.setCurrentItem(selected_item)

    def _update_column_widths(self):
        self.resizeColumnToContents(0)

    def _create_context_menu(self, node):
        """Set up the status menu for the repo status tree."""

        menu = qtutils.create_menu('Status', self)

        # TODO
        # if category == self.idx_header:
        #     return self._create_header_context_menu(menu, idx)

        if node.is_staged:
            self._create_staged_context_menu(menu, node)
        elif isinstance(node, Unmerged):
            self._create_unmerged_context_menu(menu, node)
        else:
            self._create_unstaged_context_menu(menu, node)

        # TODO
        # if not utils.is_win32():
        #     if not menu.isEmpty():
        #         menu.addSeparator()
        #     if not self.selection_model.is_empty():
        #         menu.addAction(self.default_app_action)
        #         menu.addAction(self.parent_dir_action)

        self._add_copy_actions(menu, node)

        return menu

    def _add_copy_actions(self, menu, node):
        """Add the "Copy" sub-menu"""

        enabled = isinstance(node, File)

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

        context = self.context
        for entry in copy_formats:
            name = entry.get('name', '')
            fmt = entry.get('format', '')
            if name and fmt:
                action = copy_menu.addAction(
                    name, partial(copy_format, context, fmt))
                action.setIcon(copy_icon)
                action.setEnabled(enabled)

        copy_menu.addSeparator()
        copy_menu.addAction(self.copy_customize_action)

    def _create_header_context_menu(self, menu, idx):
        context = self.context
        if idx == self.idx_staged:
            menu.addAction(icons.remove(), N_('Unstage All'),
                           cmds.run(cmds.UnstageAll, context))
        elif idx == self.idx_unstaged:
            action = menu.addAction(icons.add(), cmds.StageUnmerged.name(),
                                    cmds.run(cmds.StageUnmerged, context))
            action.setShortcut(hotkeys.STAGE_SELECTION)
        elif idx == self.idx_modified:
            action = menu.addAction(icons.add(), cmds.StageModified.name(),
                                    cmds.run(cmds.StageModified, context))
            action.setShortcut(hotkeys.STAGE_SELECTION)
        elif idx == self.idx_untracked:
            action = menu.addAction(icons.add(), cmds.StageUntracked.name(),
                                    cmds.run(cmds.StageUntracked, context))
            action.setShortcut(hotkeys.STAGE_SELECTION)
        return menu

    def _create_staged_context_menu(self, menu, node):
        # TODO
        # if s.staged[0] in self.m.submodules:
        #     return self._create_staged_submodule_context_menu(menu, s)

        context = self.context
        menu.addAction(
            icons.remove(),
            N_('Unstage'),
            cmds.run(cmds.Unstage, context, [node.full_path]),
            hotkeys.STAGE_DIFF
        )

        menu.addSeparator()

        if isinstance(node, Unmerged):
            menu.addAction(
                icons.diff(),
                cmds.LaunchDifftoolUnmergedDirect.name(),
                cmds.run(cmds.LaunchDifftoolUnmergedDirect, context, node),
                hotkeys.DIFF,
            )
        else:
            menu.addAction(
                icons.diff(),
                cmds.LaunchDifftoolDirect.name(),
                cmds.run(cmds.LaunchDifftoolDirect, context, node),
                hotkeys.DIFF,
            )

        menu.addAction(self.view_history_action)
        menu.addAction(self.view_blame_action)
        return menu

    def _create_staged_submodule_context_menu(self, menu, s):
        context = self.context
        path = core.abspath(s.staged[0])
        if len(self.staged()) == 1:
            menu.addAction(icons.cola(), N_('Launch git-cola'),
                           cmds.run(cmds.OpenRepo, context, path))
            menu.addSeparator()
        action = menu.addAction(
            icons.remove(), N_('Unstage Selected'),
            cmds.run(cmds.Unstage, context, self.staged()))
        action.setShortcut(hotkeys.STAGE_SELECTION)

        menu.addAction(self.view_history_action)
        return menu

    def _create_unmerged_context_menu(self, menu, node):
        context = self.context
        menu.addAction(
            icons.add(),
            N_('Stage'),
            cmds.run(cmds.Stage, context, [node.full_path]),
            hotkeys.STAGE_DIFF
        )
        menu.addSeparator()

        menu.addAction(
            icons.diff(),
            cmds.LaunchDifftoolUnmergedDirect.name(),
            cmds.run(cmds.LaunchDifftoolUnmergedDirect, context, node),
            hotkeys.DIFF,
        )
        menu.addAction(self.view_history_action)
        menu.addAction(self.view_blame_action)
        return menu

    def _create_unstaged_context_menu(self, menu, node):
        context = self.context

        # TODO
        # modified_submodule = (node.modified and
        #                       node.modified[0] in self.m.submodules)
        # if modified_submodule:
        #     return self._create_modified_submodule_context_menu(menu, node)

        action = menu.addAction(
            icons.add(), N_('Stage'),
            cmds.run(cmds.Stage, context, [node.full_path]))
        action.setShortcut(hotkeys.STAGE_SELECTION)

        if isinstance(node, Untracked):
            menu.addAction(self.delete_untracked_files_action)
            menu.addAction(icons.edit(), N_('Ignore...'),
                           partial(gitignore.gitignore_view, self.context))
            menu.addSeparator()
            annex = self.m.annex
            lfs = core.find_executable('git-lfs')
            if annex or lfs:
                menu.addSeparator()
            if annex:
                menu.addAction(self.annex_add_action)
            if lfs:
                menu.addAction(self.lfs_track_action)
        else:
            menu.addAction(
                # self.revert_unstaged_edits_action,
                icons.undo(),
                cmds.RevertUnstagedEditsDirect.name(),
                cmds.run(
                    cmds.RevertUnstagedEditsDirect,
                    context,
                    node
                ),
                hotkeys.REVERT
            )

        menu.addSeparator()
        if isinstance(node, Unmerged):
            menu.addAction(
                icons.diff(),
                cmds.LaunchDifftoolUnmergedDirect.name(),
                cmds.run(cmds.LaunchDifftoolUnmergedDirect, context, node),
                hotkeys.DIFF,
            )
        elif not isinstance(node, Untracked):
            menu.addAction(
                icons.diff(),
                cmds.LaunchDifftoolDirect.name(),
                cmds.run(cmds.LaunchDifftoolDirect, context, node),
                hotkeys.DIFF,
            )

        menu.addAction(self.view_history_action)
        menu.addAction(self.view_blame_action)
        return menu

    def _create_modified_submodule_context_menu(self, menu, s):
        context = self.context
        path = core.abspath(s.modified[0])
        if len(self.unstaged()) == 1:
            menu.addAction(icons.cola(), N_('Launch git-cola'),
                           cmds.run(cmds.OpenRepo, context, path))
            menu.addAction(icons.pull(), N_('Update this submodule'),
                           cmds.run(cmds.SubmoduleUpdate, context, path))
            menu.addSeparator()

        if self.m.stageable():
            menu.addSeparator()
            action = menu.addAction(
                icons.add(), N_('Stage Selected'),
                cmds.run(cmds.Stage, context, self.unstaged()))
            action.setShortcut(hotkeys.STAGE_SELECTION)

        menu.addAction(self.view_history_action)
        return menu

    def _delete_untracked_files(self):
        cmds.do(cmds.Delete, self.context, self.untracked())

    def _trash_untracked_files(self):
        cmds.do(cmds.MoveToTrash, self.context, self.untracked())

    def scroll_to_item(self, item):
        # First, scroll to the item, but keep the original hscroll
        hscroll = None
        hscrollbar = self.horizontalScrollBar()
        if hscrollbar:
            hscroll = get(hscrollbar)
        self.scrollToItem(item)
        if hscroll is not None:
            hscrollbar.setValue(hscroll)

    def _show_diff_for_selection(self, node):
        # self.show_selection()  # original handler
        context = self.context

        # TODO
        # if False:
        #     if self.m.amending():
        #         cmds.do(cmds.SetDiffText, context, '')
        #     else:
        #         cmds.do(cmds.ResetMode, context)
        #     return

        # TODO
        # # A header item e.g. 'Staged', 'Modified', etc.
        # header = category == self.idx_header
        # if header:
        #     cls = {
        #         self.idx_staged: cmds.DiffStagedSummary,
        #         self.idx_modified: cmds.Diffstat,
        #         # TODO implement UnmergedSummary
        #         # self.idx_unmerged: cmds.UnmergedSummary,
        #         self.idx_untracked: cmds.UntrackedSummary,
        #     }.get(idx, cmds.Diffstat)
        #     cmds.do(cls, context)
        #     return

        path = node.full_path
        node_type = type(node)
        deleted = node_type is Deleted
        image = self.image_formats.ok(path)

        # Images are diffed differently
        if image:
            s = context.selection
            cmds.do(
                cmds.DiffImage,
                context,
                path,
                deleted,
                s.staged,
                s.modified,
                s.unmerged,
                s.untracked
            )
        elif node.is_staged:
            cmds.do(cmds.DiffStaged, context, path, deleted=deleted)
        elif node_type is Untracked:
            cmds.do(cmds.ShowUntracked, context, path)
        elif node_type in (Modified, Deleted):
            cmds.do(cmds.Diff, context, path, deleted=deleted)
        # elif unmerged:
        #     cmds.do(cmds.Diff, context, path)

    def mimeData(self, items):
        """Return a list of absolute-path URLs"""
        context = self.context
        paths = qtutils.paths_from_items(items, item_filter=_item_filter)
        return qtutils.mimedata_from_paths(context, paths)

    # pylint: disable=no-self-use
    def mimeTypes(self):
        return qtutils.path_mimetypes()


def _item_filter(item):
    return not item.deleted and core.exists(item.path)


def view_blame(context):
    """Signal that we should view blame for paths."""
    cmds.do(cmds.BlamePaths, context)


def view_history(context):
    """Signal that we should view history for paths."""
    cmds.do(cmds.VisualizePaths, context, context.selection.union())


def copy_path(context, absolute=True):
    """Copy a selected path to the clipboard"""
    filename = context.selection.filename()
    qtutils.copy_path(filename, absolute=absolute)


def copy_relpath(context):
    """Copy a selected relative path to the clipboard"""
    copy_path(context, absolute=False)


def copy_basename(context):
    filename = os.path.basename(context.selection.filename())
    basename, _ = os.path.splitext(filename)
    qtutils.copy_path(basename, absolute=False)


def copy_leading_path(context):
    """Copy the selected leading path to the clipboard"""
    filename = context.selection.filename()
    dirname = os.path.dirname(filename)
    qtutils.copy_path(dirname, absolute=False)


def copy_format(context, fmt):
    values = {}
    values['path'] = path = context.selection.filename()
    values['abspath'] = abspath = os.path.abspath(path)
    values['absdirname'] = os.path.dirname(abspath)
    values['dirname'] = os.path.dirname(path)
    values['filename'] = os.path.basename(path)
    values['basename'], values['ext'] = (
        os.path.splitext(os.path.basename(path)))
    qtutils.set_clipboard(fmt % values)


def show_help(context):
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
    return text.text_dialog(context, help_text, title)


class StatusFilterWidget(QtWidgets.QWidget):

    def __init__(self, context, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.context = context

        hint = N_('Filter paths...')
        self.text = completion.GitStatusFilterLineEdit(
            context, hint=hint, parent=self)
        self.text.setToolTip(hint)
        self.setFocusProxy(self.text)
        self._filter = None

        self.main_layout = qtutils.hbox(defs.no_margin, defs.spacing, self.text)
        self.setLayout(self.main_layout)

        widget = self.text
        # pylint: disable=no-member
        widget.changed.connect(self.apply_filter)
        widget.cleared.connect(self.apply_filter)
        widget.enter.connect(self.apply_filter)
        widget.editingFinished.connect(self.apply_filter)

    def apply_filter(self):
        value = get(self.text)
        if value == self._filter:
            return
        self._filter = value
        paths = utils.shell_split(value)
        self.context.model.update_path_filter(paths)


def customize_copy_actions(context, parent):
    """Customize copy actions"""
    dialog = CustomizeCopyActions(context, parent)
    dialog.show()
    dialog.exec_()


class CustomizeCopyActions(standard.Dialog):

    def __init__(self, context, parent):
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
        qtutils.connect_button(
            self.show_help_button, partial(show_help, context))
        qtutils.connect_button(self.close_button, self.reject)
        qtutils.connect_button(self.save_button, self.save)
        qtutils.add_close_action(self)
        # pylint: disable=no-member
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
        standard.apply_header_columns(self.table, state)
        return result

    def add(self):
        self.table.setFocus()
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
