"""Provides widgets related to bookmarks"""
from __future__ import division, absolute_import, unicode_literals

import os
import sys

from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL


from cola import cmds
from cola import core
from cola import qtutils
from cola.i18n import N_
from cola.settings import Settings
from cola.widgets import defs
from cola.widgets import standard


def manage_bookmarks():
    dlg = BookmarksDialog(qtutils.active_window())
    dlg.show()
    dlg.exec_()
    return dlg


class BookmarksDialog(standard.Dialog):
    def __init__(self, parent):
        standard.Dialog.__init__(self, parent=parent)
        self.settings = Settings()
        self.settings.load()

        self.resize(494, 238)
        self.setWindowTitle(N_('Bookmarks'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)
        self.layt = QtGui.QVBoxLayout(self)
        self.layt.setMargin(defs.margin)
        self.layt.setSpacing(defs.spacing)

        self.bookmarks = QtGui.QListWidget(self)
        self.bookmarks.setAlternatingRowColors(True)
        self.bookmarks.setSelectionMode(QtGui.QAbstractItemView
                                             .ExtendedSelection)

        self.layt.addWidget(self.bookmarks)
        self.button_layout = QtGui.QHBoxLayout()

        self.open_button = qtutils.create_button(text=N_('Open'),
                icon=qtutils.open_icon())
        self.open_button.setEnabled(False)
        self.button_layout.addWidget(self.open_button)

        self.add_button = qtutils.create_button(text=N_('Add'),
                icon=qtutils.add_icon())
        self.button_layout.addWidget(self.add_button)

        self.delete_button = QtGui.QPushButton(self)
        self.delete_button.setText(N_('Delete'))
        self.delete_button.setIcon(qtutils.discard_icon())
        self.delete_button.setEnabled(False)
        self.button_layout.addWidget(self.delete_button)
        self.button_layout.addStretch()

        self.save_button = QtGui.QPushButton(self)
        self.save_button.setText(N_('Save'))
        self.save_button.setIcon(qtutils.save_icon())
        self.save_button.setEnabled(False)
        self.button_layout.addWidget(self.save_button)

        self.close_button = QtGui.QPushButton(self)
        self.close_button.setText(N_('Close'))
        self.button_layout.addWidget(self.close_button)

        self.layt.addLayout(self.button_layout)

        self.connect(self.bookmarks, SIGNAL('itemSelectionChanged()'),
                     self.item_selection_changed)

        qtutils.connect_button(self.open_button, self.open_repo)
        qtutils.connect_button(self.add_button, self.add)
        qtutils.connect_button(self.delete_button, self.delete)
        qtutils.connect_button(self.save_button, self.save)
        qtutils.connect_button(self.close_button, self.accept)

        self.update_bookmarks()

    def update_bookmarks(self):
        self.bookmarks.clear()
        self.bookmarks.addItems(self.settings.bookmarks)

    def selection(self):
        return qtutils.selection_list(self.bookmarks, self.settings.bookmarks)

    def item_selection_changed(self):
        has_selection = bool(self.selection())
        self.open_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def save(self):
        """Saves the bookmarks settings and exits"""
        self.settings.save()
        self.save_button.setEnabled(False)

    def add(self):
        path, ok = qtutils.prompt(N_('Path to git repository'),
                                  title=N_('Enter Git Repository'),
                                  text=core.getcwd())
        if not ok:
            return
        self.settings.bookmarks.append(path)
        self.update_bookmarks()
        self.save()

    def open_repo(self):
        """Opens a new git-cola session on a bookmark"""
        for repo in self.selection():
            core.fork([sys.executable, sys.argv[0], '--repo', repo])

    def delete(self):
        """Removes a bookmark from the bookmarks list"""
        selection = self.selection()
        if not selection:
            return
        for repo in selection:
            self.settings.remove_bookmark(repo)
        self.update_bookmarks()
        self.save_button.setEnabled(True)


class BookmarksWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.tree = BookmarksTreeWidget(parent=self)
        self.open_button = qtutils.create_action_button(
                tooltip=N_('Open'), icon=qtutils.open_icon())
        self.open_button.setEnabled(False)

        self.edit_button = qtutils.create_action_button(
                tooltip=N_('Bookmarks...'), icon=qtutils.add_icon())

        qtutils.connect_button(self.open_button, self.tree.open_repo)
        qtutils.connect_button(self.edit_button, self.manage_bookmarks)

        self.connect(self.tree, SIGNAL('itemSelectionChanged()'),
                     self._tree_selection_changed)

        self.button_layout = QtGui.QHBoxLayout()
        self.button_layout.setMargin(defs.no_margin)
        self.button_layout.setSpacing(defs.spacing)
        self.button_layout.addWidget(self.open_button)
        self.button_layout.addWidget(self.edit_button)

        self.layout = QtGui.QVBoxLayout()
        self.layout.setMargin(defs.no_margin)
        self.layout.setSpacing(defs.spacing)
        self.layout.addWidget(self.tree)
        self.setLayout(self.layout)

        self.corner_widget = QtGui.QWidget(self)
        self.corner_widget.setLayout(self.button_layout)
        titlebar = parent.titleBarWidget()
        titlebar.add_corner_widget(self.corner_widget)
        self.setFocusProxy(self.tree)

    def _tree_selection_changed(self):
        enabled = bool(self.tree.selected_item())
        self.open_button.setEnabled(enabled)

    def manage_bookmarks(self):
        manage_bookmarks()
        self.refresh()

    def refresh(self):
        self.tree.refresh()


class BookmarksTreeWidget(standard.TreeWidget):

    def __init__(self, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)

        self.open_action = qtutils.add_action(self,
                N_('Open'), self.open_repo, QtGui.QKeySequence.Open)
        self.open_action.setEnabled(False)

        self.open_new_action = qtutils.add_action(self,
                N_('Open in New Window'), self.open_new_repo,
                QtGui.QKeySequence.New)
        self.open_new_action.setEnabled(False)

        self.open_default_action = qtutils.add_action(self,
                cmds.OpenDefaultApp.name(), self.open_default,
                cmds.OpenDefaultApp.SHORTCUT)
        self.open_default_action.setEnabled(False)

        self.launch_editor_action = qtutils.add_action(self,
                cmds.Edit.name(), self.launch_editor,
                cmds.Edit.SHORTCUT)
        self.launch_editor_action.setEnabled(False)

        self.launch_terminal_action = qtutils.add_action(self,
                cmds.LaunchTerminal.name(), self.launch_terminal,
                cmds.LaunchTerminal.SHORTCUT)
        self.launch_terminal_action.setEnabled(False)

        self.copy_action = qtutils.add_action(self,
                N_('Copy'), self.copy, QtGui.QKeySequence.Copy)
        self.copy_action.setEnabled(False)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self._tree_selection_changed)

        self.connect(self, SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self._tree_double_clicked)

        self.refresh()

    def refresh(self):
        self.clear()
        settings = Settings()
        settings.load()
        items = []
        icon = qtutils.dir_icon()
        recents = set(settings.recent)
        for path in settings.recent:
            item = BookmarksTreeWidgetItem(path, icon)
            items.append(item)
        for path in settings.bookmarks:
            if path in recents: # avoid duplicates
                continue
            item = BookmarksTreeWidgetItem(path, icon)
            items.append(item)
        self.addTopLevelItems(items)

    def contextMenuEvent(self, event):
        menu = QtGui.QMenu(self)
        menu.addAction(self.open_action)
        menu.addAction(self.open_new_action)
        menu.addAction(self.open_default_action)
        menu.addSeparator()
        menu.addAction(self.copy_action)
        menu.addAction(self.launch_editor_action)
        menu.addAction(self.launch_terminal_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def copy(self):
        item = self.selected_item()
        if not item:
            return
        qtutils.set_clipboard(item.path)

    def open_default(self):
        item = self.selected_item()
        if not item:
            return
        cmds.do(cmds.OpenDefaultApp, [item.path])

    def open_repo(self):
        item = self.selected_item()
        if not item:
            return
        cmds.do(cmds.OpenRepo, item.path)

    def open_new_repo(self):
        item = self.selected_item()
        if not item:
            return
        cmds.do(cmds.OpenNewRepo, item.path)

    def launch_editor(self):
        item = self.selected_item()
        if not item:
            return
        cmds.do(cmds.Edit, [item.path])

    def launch_terminal(self):
        item = self.selected_item()
        if not item:
            return
        cmds.do(cmds.LaunchTerminal, item.path)

    def _tree_selection_changed(self):
        enabled = bool(self.selected_item())
        self.open_action.setEnabled(enabled)
        self.open_new_action.setEnabled(enabled)
        self.copy_action.setEnabled(enabled)
        self.launch_editor_action.setEnabled(enabled)
        self.launch_terminal_action.setEnabled(enabled)
        self.open_default_action.setEnabled(enabled)

    def _tree_double_clicked(self, item, column):
        cmds.do(cmds.OpenRepo, item.path)


class BookmarksTreeWidgetItem(QtGui.QTreeWidgetItem):

    def __init__(self, path, icon):
        QtGui.QTreeWidgetItem.__init__(self)
        self.path = path
        self.setIcon(0, icon)
        self.setText(0, os.path.basename(path))
        self.setToolTip(0, path)
