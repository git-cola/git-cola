"""Provides widgets related to branchs"""
from __future__ import division, absolute_import, unicode_literals
import os

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import cmds
from .. import core
from .. import git
from .. import gitcfg
from .. import gitcmds
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import utils
from ..i18n import N_
from ..models import prefs
from ..settings import Settings
from ..widgets import defs
from ..widgets import standard


class BranchWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.tree = BranchTreeWidget(parent=self)

        self.refresh_button = qtutils.create_action_button(
                tooltip=N_('Refresh'), icon=icons.sync())

        self.setFocusProxy(self.tree)
        self.setToolTip(N_('Branchs'))

        self.button_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                          self.refresh_button)

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing, self.tree)
        self.setLayout(self.main_layout)

        self.corner_widget = QtWidgets.QWidget(self)
        self.corner_widget.setLayout(self.button_layout)
        titlebar = parent.titleBarWidget()
        titlebar.add_corner_widget(self.corner_widget)

        qtutils.connect_button(self.refresh_button, self.reload_branchs)

        QtCore.QTimer.singleShot(0, self.reload_branchs)

    def reload_branchs(self):
        # Called once after the GUI is initialized
        self.tree.refresh()


class BranchTreeWidget(standard.TreeWidget):
    updated = Signal()

    def __init__(self, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)

        #self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        self.current = None

        self.updated.connect(self.refresh, type=Qt.QueuedConnection)

    def refresh(self):
        builder = BuildItem()

        self.current = gitcmds.current_branch()
        local_branchs = BranchTreeWidgetItem("Local", icons.ellipsis())
        entries = gitcmds.branch_list()
        local_items = [builder.get(entry, self.current) for entry in entries]
        local_items.sort(key=lambda x: x)

        local_branchs.addChildren(local_items)

        remote_branchs = BranchTreeWidgetItem("Remote", icons.ellipsis())
        entries = gitcmds.branch_list(True)
        remote_items = [builder.get(entry) for entry in entries]
        remote_items.sort(key=lambda x: x)

        remote_branchs.addChildren(remote_items)

        self.clear()
        self.addTopLevelItems([local_branchs, remote_branchs])

        self.expandAll()

    def contextMenuEvent(self, event):
        menu = qtutils.create_menu(N_('Actions'), self)
        menu.addAction(qtutils.add_action(self, N_('Checkout'),
                                 self.checkout_action))

        menu.exec_(self.mapToGlobal(event.pos()))

    def checkout_action(self):
        if self.selected_item().name != self.current:
            cmds.do(cmds.CheckoutBranch, self.selected_item().name)
            self.refresh()

        ## We make the items editable, but we don't want the double-click
        ## behavior to trigger editing.  Make it behave like Mac OS X's Finder.
        #self.setEditTriggers(self.SelectedClicked)

        #self.open_action = qtutils.add_action(
                #self, N_('Open'), self.open_repo, hotkeys.OPEN)

        #self.accept_action = qtutils.add_action(
                #self, N_('Accept'), self.accept_repo, *hotkeys.ACCEPT)

        #self.open_new_action = qtutils.add_action(
                #self, N_('Open in New Window'), self.open_new_repo, hotkeys.NEW)

        #self.set_default_repo_action = qtutils.add_action(
                #self, N_('Set Default Repository'), self.set_default_repo)

        #self.clear_default_repo_action = qtutils.add_action(
                #self, N_('Clear Default Repository'), self.clear_default_repo)

        #self.rename_repo_action = qtutils.add_action(
                #self, N_('Rename Repository'), self.rename_repo)

        #self.open_default_action = qtutils.add_action(
                #self, cmds.OpenDefaultApp.name(), self.open_default,
                #hotkeys.PRIMARY_ACTION)

        #self.launch_editor_action = qtutils.add_action(
                #self, cmds.Edit.name(), self.launch_editor, hotkeys.EDIT)

        #self.launch_terminal_action = qtutils.add_action(
                #self, cmds.LaunchTerminal.name(), self.launch_terminal,
                #hotkeys.TERMINAL)

        #self.copy_action = qtutils.add_action(
                #self, N_('Copy'), self.copy, hotkeys.COPY)

        #self.itemChanged.connect(self.item_changed)
        #self.itemSelectionChanged.connect(self.item_selection_changed)
        #self.itemDoubleClicked.connect(self.tree_double_clicked)

        #self.action_group = utils.Group(self.open_action,
                                        #self.open_new_action,
                                        #self.copy_action,
                                        #self.launch_editor_action,
                                        #self.launch_terminal_action,
                                        #self.open_default_action,
                                        #self.rename_repo_action)
        #self.action_group.setEnabled(False)
        #self.set_default_repo_action.setEnabled(False)
        #self.clear_default_repo_action.setEnabled(False)

    #def refresh(self):
        #settings = self.settings
        #builder = BuildItem()

        #entries = settings.branchs

        #items = [builder.get(entry['path'], entry['name']) for entry in entries]
        #if self.style == BOOKMARKS and prefs.sort_bookmarks():
            #items.sort(key=lambda x: x.name)

        #self.clear()
        #self.addTopLevelItems(items)

    #def contextMenuEvent(self, event):
        #menu = qtutils.create_menu(N_('Actions'), self)
        #menu.addAction(self.open_action)
        #menu.addAction(self.open_new_action)
        #menu.addAction(self.open_default_action)
        #menu.addSeparator()
        #menu.addAction(self.copy_action)
        #menu.addAction(self.launch_editor_action)
        #menu.addAction(self.launch_terminal_action)
        #menu.addSeparator()
        #item = self.selected_item()
        #is_default = bool(item and item.is_default)
        #if is_default:
            #menu.addAction(self.clear_default_repo_action)
        #else:
            #menu.addAction(self.set_default_repo_action)
        #menu.addAction(self.rename_repo_action)
        #menu.exec_(self.mapToGlobal(event.pos()))

    #def item_changed(self, item, index):
        #self.rename_entry(item, item.text(0))

    #def rename_entry(self, item, new_name):
        #if self.style == BOOKMARKS:
            #rename = self.settings.rename_bookmark
        #elif self.style == RECENT_REPOS:
            #rename = self.settings.rename_recent
        #else:
            #rename = lambda *args: False
        #if rename(item.path, item.name, new_name):
            #self.settings.save()
            #item.name = new_name
        #else:
            #item.setText(0, item.name)

    #def apply_fn(self, fn, *args, **kwargs):
        #item = self.selected_item()
        #if item:
            #fn(item, *args, **kwargs)

    #def copy(self):
        #self.apply_fn(lambda item: qtutils.set_clipboard(item.path))

    #def open_default(self):
        #self.apply_fn(lambda item: cmds.do(cmds.OpenDefaultApp, [item.path]))

    #def set_default_repo(self):
        #self.apply_fn(self.set_default_item)

    #def set_default_item(self, item):
        #cmds.do(cmds.SetDefaultRepo, item.path, item.name)
        #self.refresh()
        #self.default_changed.emit()

    #def clear_default_repo(self):
        #self.apply_fn(self.clear_default_item)
        #self.default_changed.emit()

    #def clear_default_item(self, item):
        #cmds.do(cmds.SetDefaultRepo, None, None)
        #self.refresh()

    #def rename_repo(self):
        #self.apply_fn(lambda item: self.editItem(item, 0))

    #def accept_repo(self):
        #self.apply_fn(lambda item: self.accept_item(item))

    #def accept_item(self, item):
        #if self.state() & self.EditingState:
            #widget = self.itemWidget(item, 0)
            #if widget:
                #self.commitData(widget)
            #self.closePersistentEditor(item, 0)
        #else:
            #self.open_repo()

    #def open_repo(self):
        #self.apply_fn(lambda item: cmds.do(cmds.OpenRepo, item.path))

    #def open_new_repo(self):
        #self.apply_fn(lambda item: cmds.do(cmds.OpenNewRepo, item.path))

    #def launch_editor(self):
        #self.apply_fn(lambda item: cmds.do(cmds.Edit, [item.path]))

    #def launch_terminal(self):
        #self.apply_fn(lambda item: cmds.do(cmds.LaunchTerminal, item.path))

    #def item_selection_changed(self):
        #item = self.selected_item()
        #enabled = bool(item)
        #self.action_group.setEnabled(enabled)

        #is_default = bool(item and item.is_default)
        #self.set_default_repo_action.setEnabled(not is_default)
        #self.clear_default_repo_action.setEnabled(is_default)

    #def tree_double_clicked(self, item, column):
        #cmds.do(cmds.OpenRepo, item.path)

    #def add_bookmark(self):
        #normpath = utils.expandpath(core.getcwd())
        #name = os.path.basename(normpath)
        #prompt = (
            #(N_('Name'), name),
            #(N_('Path'), core.getcwd()),
        #)
        #ok, values = qtutils.prompt_n(N_('Add Favorite'), prompt)
        #if not ok:
            #return
        #name, path = values
        #normpath = utils.expandpath(path)
        #if git.is_git_worktree(normpath):
            #self.settings.add_bookmark(normpath, name)
            #self.settings.save()
            #self.refresh()
        #else:
            #qtutils.critical(N_('Error'),
                             #N_('%s is not a Git repository.') % path)

    #def delete_bookmark(self):
        #"""Removes a bookmark from the bookmarks list"""
        #item = self.selected_item()
        #if not item:
            #return
        #if self.style == BOOKMARKS:
            #cmd = cmds.RemoveBookmark
        #elif self.style == RECENT_REPOS:
            #cmd = cmds.RemoveRecent
        #else:
            #return
        #ok, status, out, err = cmds.do(cmd, self.settings, item.path,
                                       #item.name, icon=icons.discard())
        #if ok:
            #self.refresh()


class BuildItem(object):

    def __init__(self):
        self.icon = icons.folder()

    def get(self, name, current=None):
        icon = self.icon
        if name == current:
            icon = icons.star()
        return BranchTreeWidgetItem(name, icon)


class BranchTreeWidgetItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, name, icon):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self.name = name

        self.setIcon(0, icon)
        self.setText(0, name)
        self.setToolTip(0, name)
        self.setFlags(self.flags() | Qt.ItemIsEditable)
