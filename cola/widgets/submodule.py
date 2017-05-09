"""Provides widgets related to submodules"""

import os

from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..i18n import N_
from ..models import main
from ..widgets import defs
from ..widgets import standard
from .. import cmds
from .. import qtutils
from .. import icons

from branch import AsyncGitActionTask, GitHelper

class SubmodulesWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.setToolTip(N_('Submodules'))
        # main
        self.tree = SubmodulesTreeWidget(parent=self)
        self.setFocusProxy(self.tree)
        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing, self.tree)
        self.setLayout(self.main_layout)
        # button
        self.refresh_button = qtutils.create_action_button(
                tooltip=N_('Refresh'), icon=icons.sync())
        qtutils.connect_button(self.refresh_button, self.tree.refresh_command)
        self.back_to_parent_button = qtutils.create_action_button(
                tooltip=N_('BackToParent'), icon=icons.push())
        qtutils.connect_button(self.back_to_parent_button, self.tree.back_to_parent_command)
        self.button_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                          self.back_to_parent_button,
                                          self.refresh_button)
        self.corner_widget = QtWidgets.QWidget(self)
        self.corner_widget.setLayout(self.button_layout)
        # titlebar
        titlebar = parent.titleBarWidget()
        titlebar.add_corner_widget(self.corner_widget)


class SubmodulesTreeWidget(standard.TreeWidget):
    updated = Signal()

    def __init__(self, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)

        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)
        # model
        self.main_model = model = main.model()
        self.updated.connect(self.refresh, type=Qt.QueuedConnection)
        model.add_observer(model.message_updated, self.updated.emit)
        # UI
        self._active = False
        self.child_path = None
        self.parent_paths = []
        self.list_helper = BuildItem()
        self.itemDoubleClicked.connect(self.tree_double_clicked)

    def refresh_command(self):
        self.main_model._update_submodule_list()
        self.refresh()

    def refresh(self):
        if not self._active:
          return

        if self.main_model.directory != self.child_path:
            self.child_path = self.main_model.directory
            self.parent_paths = []

        items = [self.list_helper.get(entry[0], entry[2], entry[2])
        for entry in self.main_model.submodule_list]

        self.clear()
        self.addTopLevelItems(items)

    def showEvent(self, event):
        """Defer updating widgets until the widget is visible"""
        if not self._active:
            self._active = True
            self.refresh()
        return super(SubmodulesTreeWidget, self).showEvent(event)

    def back_to_parent_command(self):
        if self.parent_paths:
            path = self.parent_paths.pop()
            self.child_path = path
            cmds.do(cmds.OpenRepo, path)

    def contextMenuEvent(self, event):
        selected = self.selected_item()

    def tree_double_clicked(self, item, column):
        path = os.path.join(self.main_model.directory, item.path)
        self.parent_paths.append(self.main_model.directory)
        self.child_path = path
        cmds.do(cmds.OpenRepo, path)


class BuildItem(object):

    def __init__(self):
        self.sign_folder_map = {}
        self.sign_folder_map[' '] = icons.folder()
        self.sign_folder_map['+'] = icons.new()
        self.sign_folder_map['-'] = icons.add()

    def get(self, sign, path, name):
        icon = self.sign_folder_map[sign]
        return SubmodulesTreeWidgetItem(path, name, icon)


class SubmodulesTreeWidgetItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, path, name, icon):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self.path = path
        self.name = name

        self.setIcon(0, icon)
        self.setText(0, name)
        self.setToolTip(0, path)
        #self.setFlags(self.flags() | Qt.ItemIsEditable)
