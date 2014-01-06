"""Provides widgets related to bookmarks"""
import os
import sys

from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL


from cola import cmds
from cola import core
from cola import qtutils
from cola import settings
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
        self.model = settings.Settings()

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
        self.bookmarks.addItems(self.model.bookmarks)

    def selection(self):
        return qtutils.selection_list(self.bookmarks, self.model.bookmarks)

    def item_selection_changed(self):
        has_selection = bool(self.selection())
        self.open_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def save(self):
        """Saves the bookmarks settings and exits"""
        self.model.save()
        self.save_button.setEnabled(False)

    def add(self):
        path, ok = qtutils.prompt(N_('Path to git repository'),
                                  title=N_('Enter Git Repository'),
                                  text=core.getcwd())
        if not ok:
            return
        self.model.bookmarks.append(path)
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
            self.model.remove_bookmark(repo)
        self.update_bookmarks()
        self.save_button.setEnabled(True)


class BookmarksWidget(QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.tree = BookmarksTreeWidget(parent=self)
        self.open_button = qtutils.create_action_button(
                N_('Open'), qtutils.open_icon())
        self.open_button.setEnabled(False)

        self.open_action = qtutils.add_action(self,
                N_('Open'), self.open_repo, 'Return')
        self.open_action.setEnabled(False)

        self.edit_button = qtutils.create_action_button(
                N_('Bookmarks...'), qtutils.add_icon())

        qtutils.connect_button(self.open_button, self.open_repo)
        qtutils.connect_button(self.edit_button, self.manage_bookmarks)

        self.connect(self.tree, SIGNAL('itemSelectionChanged()'),
                     self._tree_selection_changed)

        self.connect(self.tree,
                     SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self._tree_double_clicked)

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
        self.open_action.setEnabled(enabled)

    def open_repo(self):
        item = self.tree.selected_item()
        if not item:
            return
        cmds.do(cmds.OpenRepo, item.path)

    def _tree_double_clicked(self, item, column):
        cmds.do(cmds.OpenRepo, item.path)

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
        self.refresh()

    def refresh(self):
        self.clear()
        settings = Settings()
        items = []
        icon = qtutils.dir_icon()
        for path in settings.bookmarks + settings.recent:
            item = BookmarksTreeWidgetItem(path, icon)
            items.append(item)
        self.addTopLevelItems(items)


class BookmarksTreeWidgetItem(QtGui.QTreeWidgetItem):

    def __init__(self, path, icon):
        QtGui.QTreeWidgetItem.__init__(self)
        self.path = path
        self.setIcon(0, icon)
        self.setText(0, os.path.basename(path))
        self.setToolTip(0, path)
