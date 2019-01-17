"""Provides widgets related to submodules"""
from __future__ import absolute_import

from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import cmds
from .. import core
from .. import qtutils
from .. import icons
from .. import version
from ..i18n import N_
from ..widgets import defs
from ..widgets import standard


class SubmodulesWidget(QtWidgets.QWidget):

    def __init__(self, context, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.setToolTip(N_('Submodules'))
        # main
        self.tree = SubmodulesTreeWidget(context, parent=self)
        self.setFocusProxy(self.tree)
        self.main_layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.tree)
        self.setLayout(self.main_layout)
        # button
        # TODO better icons
        self.refresh_button = qtutils.create_action_button(
                tooltip=N_('Refresh'), icon=icons.sync())
        qtutils.connect_button(self.refresh_button, self.tree.refresh_command)
        self.open_parent_button = qtutils.create_action_button(
                tooltip=N_('Open Parent'), icon=icons.push())
        qtutils.connect_button(self.open_parent_button,
                               lambda: cmds.do(cmds.OpenParentRepo, context))
        if not version.check_git(context, 'show-superproject-working-tree'):
            self.open_parent_button.setVisible(False)
        self.button_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                          self.open_parent_button,
                                          self.refresh_button)
        self.corner_widget = QtWidgets.QWidget(self)
        self.corner_widget.setLayout(self.button_layout)
        # titlebar
        titlebar = parent.titleBarWidget()
        titlebar.add_corner_widget(self.corner_widget)


class SubmodulesTreeWidget(standard.TreeWidget):
    updated = Signal()

    def __init__(self, context, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)

        self.context = context
        self.main_model = model = context.model

        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)
        # model
        self.updated.connect(self.refresh, type=Qt.QueuedConnection)
        model.add_observer(model.message_updated, self.updated.emit)
        # UI
        self._active = False
        self.list_helper = BuildItem()
        self.itemDoubleClicked.connect(self.tree_double_clicked)

    def refresh_command(self):
        # TODO how to monitor changes of submodules?
        self.main_model._update_submodules_list()
        self.refresh()

    def refresh(self):
        if not self._active:
            return

        items = [self.list_helper.get(entry) for entry in
                 self.main_model.submodules_list]
        self.clear()
        self.addTopLevelItems(items)

    def showEvent(self, event):
        """Defer updating widgets until the widget is visible"""
        if not self._active:
            self._active = True
            self.refresh()
        return super(SubmodulesTreeWidget, self).showEvent(event)

    def tree_double_clicked(self, item, _column):
        path = core.abspath(item.path)
        cmds.do(cmds.OpenRepo, self.context, path)


class BuildItem(object):

    def __init__(self):
        self.state_folder_map = {}
        # TODO better icons
        self.state_folder_map[''] = icons.folder()
        self.state_folder_map['+'] = icons.new()
        self.state_folder_map['-'] = icons.close()
        self.state_folder_map['U'] = icons.merge()

    def get(self, entry):
        """entry: same as returned from list_submodule"""
        name = entry[2]
        path = entry[2]
        # TODO better tip
        tip = path + '\n' + entry[1]
        if entry[3]:
            tip += '\n({0})'.format(entry[3])
        icon = self.state_folder_map[entry[0]]
        return SubmodulesTreeWidgetItem(name, path, tip, icon)


class SubmodulesTreeWidgetItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, name, path, tip, icon):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self.path = path

        self.setIcon(0, icon)
        self.setText(0, name)
        self.setToolTip(0, tip)
