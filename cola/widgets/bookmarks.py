"""Provides widgets related to bookmarks"""
from __future__ import division, absolute_import, unicode_literals
import os

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import cmds
from .. import core
from .. import git
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import utils
from ..i18n import N_
from ..interaction import Interaction
from ..models import prefs
from ..settings import Settings
from ..widgets import defs
from ..widgets import standard


BOOKMARKS = 0
RECENT_REPOS = 1


def bookmark(context, parent):
    return BookmarksWidget(context, BOOKMARKS, parent=parent)


def recent(context, parent):
    return BookmarksWidget(context, RECENT_REPOS, parent=parent)


class BookmarksWidget(QtWidgets.QFrame):

    def __init__(self, context, style=BOOKMARKS, parent=None):
        QtWidgets.QFrame.__init__(self, parent)

        self.style = style
        self.settings = Settings()
        self.tree = BookmarksTreeWidget(
            context, style, self.settings, parent=self)

        self.add_button = qtutils.create_action_button(
            tooltip=N_('Add'), icon=icons.add())

        self.delete_button = qtutils.create_action_button(
            tooltip=N_('Delete'), icon=icons.remove())

        self.open_button = qtutils.create_action_button(
            tooltip=N_('Open'), icon=icons.repo())

        self.button_group = utils.Group(self.delete_button, self.open_button)
        self.button_group.setEnabled(False)

        self.setFocusProxy(self.tree)
        if style == BOOKMARKS:
            self.setToolTip(N_('Favorite repositories'))
        elif style == RECENT_REPOS:
            self.setToolTip(N_('Recent repositories'))
            self.add_button.hide()

        self.button_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                          self.open_button, self.add_button,
                                          self.delete_button)

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing, self.tree)
        self.setLayout(self.main_layout)

        self.corner_widget = QtWidgets.QWidget(self)
        self.corner_widget.setLayout(self.button_layout)
        titlebar = parent.titleBarWidget()
        titlebar.add_corner_widget(self.corner_widget)

        qtutils.connect_button(self.add_button, self.tree.add_bookmark)
        qtutils.connect_button(self.delete_button, self.tree.delete_bookmark)
        qtutils.connect_button(self.open_button, self.tree.open_repo)

        item_selection_changed = self.tree_item_selection_changed
        self.tree.itemSelectionChanged.connect(item_selection_changed)

        QtCore.QTimer.singleShot(0, self.reload_bookmarks)

    def reload_bookmarks(self):
        # Called once after the GUI is initialized
        self.settings.load()
        self.tree.refresh()

    def tree_item_selection_changed(self):
        enabled = bool(self.tree.selected_item())
        self.button_group.setEnabled(enabled)

    def connect_to(self, other):
        self.tree.default_changed.connect(other.tree.refresh)
        other.tree.default_changed.connect(self.tree.refresh)


def disable_rename(_path, _name, _new_name):
    return False


class BookmarksTreeWidget(standard.TreeWidget):
    default_changed = Signal()

    def __init__(self, context, style, settings, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)
        self.context = context
        self.style = style
        self.settings = settings

        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)

        # We make the items editable, but we don't want the double-click
        # behavior to trigger editing.  Make it behave like Mac OS X's Finder.
        self.setEditTriggers(self.SelectedClicked)

        self.open_action = qtutils.add_action(
            self, N_('Open'), self.open_repo, hotkeys.OPEN)

        self.accept_action = qtutils.add_action(
            self, N_('Accept'), self.accept_repo, *hotkeys.ACCEPT)

        self.open_new_action = qtutils.add_action(
            self, N_('Open in New Window'), self.open_new_repo, hotkeys.NEW)

        self.set_default_repo_action = qtutils.add_action(
            self, N_('Set Default Repository'), self.set_default_repo)

        self.clear_default_repo_action = qtutils.add_action(
            self, N_('Clear Default Repository'), self.clear_default_repo)

        self.rename_repo_action = qtutils.add_action(
            self, N_('Rename Repository'), self.rename_repo)

        self.open_default_action = qtutils.add_action(
            self, cmds.OpenDefaultApp.name(), self.open_default,
            hotkeys.PRIMARY_ACTION)

        self.launch_editor_action = qtutils.add_action(
            self, cmds.Edit.name(), self.launch_editor, hotkeys.EDIT)

        self.launch_terminal_action = qtutils.add_action(
            self, cmds.LaunchTerminal.name(), self.launch_terminal,
            hotkeys.TERMINAL)

        self.copy_action = qtutils.add_action(
            self, N_('Copy'), self.copy, hotkeys.COPY)

        self.itemChanged.connect(self.item_changed)
        self.itemSelectionChanged.connect(self.item_selection_changed)
        self.itemDoubleClicked.connect(self.tree_double_clicked)

        self.action_group = utils.Group(self.open_action,
                                        self.open_new_action,
                                        self.copy_action,
                                        self.launch_editor_action,
                                        self.launch_terminal_action,
                                        self.open_default_action,
                                        self.rename_repo_action)
        self.action_group.setEnabled(False)
        self.set_default_repo_action.setEnabled(False)
        self.clear_default_repo_action.setEnabled(False)

    def refresh(self):
        context = self.context
        settings = self.settings
        builder = BuildItem(context)

        # bookmarks
        if self.style == BOOKMARKS:
            entries = settings.bookmarks
        # recent items
        elif self.style == RECENT_REPOS:
            entries = settings.recent

        items = [builder.get(entry['path'], entry['name']) for entry in entries]
        if self.style == BOOKMARKS and prefs.sort_bookmarks(context):
            items.sort(key=lambda x: x.name)

        self.clear()
        self.addTopLevelItems(items)

    def contextMenuEvent(self, event):
        menu = qtutils.create_menu(N_('Actions'), self)
        menu.addAction(self.open_action)
        menu.addAction(self.open_new_action)
        menu.addAction(self.open_default_action)
        menu.addSeparator()
        menu.addAction(self.copy_action)
        menu.addAction(self.launch_editor_action)
        menu.addAction(self.launch_terminal_action)
        menu.addSeparator()
        item = self.selected_item()
        is_default = bool(item and item.is_default)
        if is_default:
            menu.addAction(self.clear_default_repo_action)
        else:
            menu.addAction(self.set_default_repo_action)
        menu.addAction(self.rename_repo_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def item_changed(self, item, _index):
        self.rename_entry(item, item.text(0))

    def rename_entry(self, item, new_name):
        if self.style == BOOKMARKS:
            rename = self.settings.rename_bookmark
        elif self.style == RECENT_REPOS:
            rename = self.settings.rename_recent
        else:
            rename = disable_rename
        if rename(item.path, item.name, new_name):
            self.settings.save()
            item.name = new_name
        else:
            item.setText(0, item.name)

    def apply_fn(self, fn, *args, **kwargs):
        item = self.selected_item()
        if item:
            fn(item, *args, **kwargs)

    def copy(self):
        self.apply_fn(lambda item: qtutils.set_clipboard(item.path))

    def open_default(self):
        context = self.context
        self.apply_fn(
            lambda item: cmds.do(cmds.OpenDefaultApp, context, [item.path]))

    def set_default_repo(self):
        self.apply_fn(self.set_default_item)

    def set_default_item(self, item):
        context = self.context
        cmds.do(cmds.SetDefaultRepo, context, item.path)
        self.refresh()
        self.default_changed.emit()

    def clear_default_repo(self):
        self.apply_fn(self.clear_default_item)
        self.default_changed.emit()

    def clear_default_item(self, _item):
        context = self.context
        cmds.do(cmds.SetDefaultRepo, context, None)
        self.refresh()

    def rename_repo(self):
        self.apply_fn(lambda item: self.editItem(item, 0))

    def accept_repo(self):
        self.apply_fn(self.accept_item)

    def accept_item(self, item):
        if self.state() & self.EditingState:
            widget = self.itemWidget(item, 0)
            if widget:
                self.commitData(widget)
            self.closePersistentEditor(item, 0)
        else:
            self.open_repo()

    def open_repo(self):
        context = self.context
        self.apply_fn(lambda item: cmds.do(cmds.OpenRepo, context, item.path))

    def open_new_repo(self):
        context = self.context
        self.apply_fn(
            lambda item: cmds.do(cmds.OpenNewRepo, context, item.path))

    def launch_editor(self):
        context = self.context
        self.apply_fn(lambda item: cmds.do(cmds.Edit, context, [item.path]))

    def launch_terminal(self):
        context = self.context
        self.apply_fn(
            lambda item: cmds.do(cmds.LaunchTerminal, context, item.path))

    def item_selection_changed(self):
        item = self.selected_item()
        enabled = bool(item)
        self.action_group.setEnabled(enabled)

        is_default = bool(item and item.is_default)
        self.set_default_repo_action.setEnabled(not is_default)
        self.clear_default_repo_action.setEnabled(is_default)

    def tree_double_clicked(self, item, _column):
        context = self.context
        cmds.do(cmds.OpenRepo, context, item.path)

    def add_bookmark(self):
        normpath = utils.expandpath(core.getcwd())
        name = os.path.basename(normpath)
        prompt = (
            (N_('Name'), name),
            (N_('Path'), core.getcwd()),
        )
        ok, values = qtutils.prompt_n(N_('Add Favorite'), prompt)
        if not ok:
            return
        name, path = values
        normpath = utils.expandpath(path)
        if git.is_git_worktree(normpath):
            self.settings.add_bookmark(normpath, name)
            self.settings.save()
            self.refresh()
        else:
            Interaction.critical(
                N_('Error'), N_('%s is not a Git repository.') % path)

    def delete_bookmark(self):
        """Removes a bookmark from the bookmarks list"""
        item = self.selected_item()
        context = self.context
        if not item:
            return
        if self.style == BOOKMARKS:
            cmd = cmds.RemoveBookmark
        elif self.style == RECENT_REPOS:
            cmd = cmds.RemoveRecent
        else:
            return
        ok, _, _, _ = cmds.do(
            cmd, context, self.settings, item.path, item.name,
            icon=icons.discard())
        if ok:
            self.refresh()


class BuildItem(object):

    def __init__(self, context):
        self.star_icon = icons.star()
        self.folder_icon = icons.folder()
        cfg = context.cfg
        self.default_repo = cfg.get('cola.defaultrepo')

    def get(self, path, name):
        is_default = self.default_repo == path
        if is_default:
            icon = self.star_icon
        else:
            icon = self.folder_icon
        return BookmarksTreeWidgetItem(path, name, icon, is_default)


class BookmarksTreeWidgetItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, path, name, icon, is_default):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self.path = path
        self.name = name
        self.is_default = is_default

        self.setIcon(0, icon)
        self.setText(0, name)
        self.setToolTip(0, path)
        self.setFlags(self.flags() | Qt.ItemIsEditable)
