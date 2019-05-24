from __future__ import division, absolute_import, unicode_literals
from functools import partial

from qtpy import QtGui
from qtpy.QtCore import Qt
from qtpy import QtWidgets

from ..i18n import N_
from ..widgets import standard
from ..qtutils import get
from .. import icons
from .. import qtutils
from .toolbarcmds import COMMANDS
from . import defs

TREE_LAYOUT = {
    'Others': [
        'Others::LaunchEditor',
        'Others::RevertUnstagedEdits'
    ],
    'File': [
        'File::NewRepo',
        'File::OpenRepo',
        'File::OpenRepoNewWindow',
        'File::Refresh',
        'File::EditRemotes',
        'File::RecentModified',
        'File::SaveAsTarZip',
        'File::ApplyPatches',
        'File::ExportPatches',
    ],
    'Actions': [
        'Actions::Fetch',
        'Actions::Pull',
        'Actions::Push',
        'Actions::Stash',
        'Actions::CreateTag',
        'Actions::CherryPick',
        'Actions::Merge',
        'Actions::AbortMerge',
        'Actions::UpdateSubmodules',
        'Actions::ResetBranchHead',
        'Actions::ResetWorktree',
        'Actions::Grep',
        'Actions::Search'
    ],
    'Commit@@verb': [
        'Commit::Stage',
        'Commit::AmendLast',
        'Commit::StageAll',
        'Commit::UnstageAll',
        'Commit::Unstage',
        'Commit::LoadCommitMessage',
        'Commit::GetCommitMessageTemplate',
    ],
    'Diff': [
        'Diff::Difftool',
        'Diff::Expression',
        'Diff::Branches',
        'Diff::Diffstat'
    ],
    'Branch': [
        'Branch::Review',
        'Branch::Create',
        'Branch::Checkout',
        'Branch::Delete',
        'Branch::DeleteRemote',
        'Branch::Rename',
        'Branch::BrowseCurrent',
        'Branch::BrowseOther',
        'Branch::VisualizeCurrent',
        'Branch::VisualizeAll'
    ],
    'View': [
        'View::DAG',
        'View::FileBrowser',
    ]
}


def configure(toolbar, parent=None):
    """Launches the Toolbar configure dialog"""
    view = ToolbarView(toolbar, parent if parent else qtutils.active_window())
    view.show()
    return view


def get_toolbars(widget):
    return widget.findChildren(ToolBar)


def add_toolbar(context, widget):
    toolbars = get_toolbars(widget)
    name = 'ToolBar%d' % (len(toolbars) + 1)
    toolbar = ToolBar.create(context, name)
    widget.addToolBar(toolbar)
    configure(toolbar)


class ToolBarState(object):
    """export_state() and apply_state() providers for toolbars"""

    def __init__(self, context, widget):
        """widget must be a QMainWindow for toolBarArea(), etc."""
        self.context = context
        self.widget = widget

    def apply_state(self, toolbars):
        context = self.context
        widget = self.widget

        for data in toolbars:
            toolbar = ToolBar.create(context, data['name'])
            toolbar.load_items(data['items'])
            toolbar.set_show_icons(data['show_icons'])
            toolbar.setVisible(data['visible'])

            toolbar_area = decode_toolbar_area(data['area'])
            if data['break']:
                widget.addToolBarBreak(toolbar_area)
            widget.addToolBar(toolbar_area, toolbar)

            # floating toolbars must be set after added
            if data['float']:
                toolbar.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
                toolbar.move(data['x'], data['y'])
            # TODO: handle changed width when exists more than one toolbar in
            # an area

    def export_state(self):
        result = []
        widget = self.widget
        toolbars = widget.findChildren(ToolBar)

        for toolbar in toolbars:
            toolbar_area = widget.toolBarArea(toolbar)
            if toolbar_area == Qt.NoToolBarArea:
                continue  # filter out removed toolbars
            items = [x.data() for x in toolbar.actions()]

            result.append({
                'name': toolbar.windowTitle(),
                'area': encode_toolbar_area(toolbar_area),
                'break': widget.toolBarBreak(toolbar),
                'float': toolbar.isFloating(),
                'x': toolbar.pos().x(),
                'y': toolbar.pos().y(),
                'width': toolbar.width(),
                'height': toolbar.height(),
                'show_icons': toolbar.show_icons(),
                'visible': toolbar.isVisible(),
                'items': items,
                })

        return result


class ToolBar(QtWidgets.QToolBar):
    SEPARATOR = 'Separator'

    @staticmethod
    def create(context, name):
        return ToolBar(context, name, TREE_LAYOUT, COMMANDS)

    def __init__(self, context, title, tree_layout, toolbar_commands):
        QtWidgets.QToolBar.__init__(self)
        self.setWindowTitle(title)
        self.setObjectName(title)

        self.context = context
        self.tree_layout = tree_layout
        self.commands = toolbar_commands

    def set_show_icons(self, show_icons):
        if show_icons:
            self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        else:
            self.setToolButtonStyle(Qt.ToolButtonTextOnly)

    def show_icons(self):
        return self.toolButtonStyle() == Qt.ToolButtonIconOnly

    def load_items(self, items):
        for data in items:
            self.add_action_from_data(data)

    def add_action_from_data(self, data):
        parent = data['parent']
        child = data['child']

        if child == self.SEPARATOR:
            toolbar_action = self.addSeparator()
            toolbar_action.setData(data)
            return

        tree_items = self.tree_layout.get(parent, [])
        if child in tree_items and child in self.commands:
            command = self.commands[child]
            title = N_(command['title'])
            callback = partial(command['action'], self.context)

            icon = None
            command_icon = command.get('icon', None)
            if command_icon:
                icon = getattr(icons, command_icon, None)
                if callable(icon):
                    icon = icon()
            if icon:
                toolbar_action = self.addAction(icon, title, callback)
            else:
                toolbar_action = self.addAction(title, callback)

            toolbar_action.setData(data)

    def delete_toolbar(self):
        self.parent().removeToolBar(self)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        menu.addAction(N_('Configure toolbar'), partial(configure, self))
        menu.addAction(N_('Delete toolbar'), self.delete_toolbar)

        menu.exec_(event.globalPos())


def encode_toolbar_area(toolbar_area):
    """Encode a Qt::ToolBarArea as a string"""
    if toolbar_area == Qt.LeftToolBarArea:
        result = 'left'
    elif toolbar_area == Qt.RightToolBarArea:
        result = 'right'
    elif toolbar_area == Qt.TopToolBarArea:
        result = 'top'
    elif toolbar_area == Qt.BottomToolBarArea:
        result = 'bottom'
    else:  # fallback to "bottom"
        result = 'bottom'
    return result


def decode_toolbar_area(string):
    """Decode an encoded toolbar area string into a Qt::ToolBarArea"""
    if string == 'left':
        result = Qt.LeftToolBarArea
    elif string == 'right':
        result = Qt.RightToolBarArea
    elif string == 'top':
        result = Qt.TopToolBarArea
    elif string == 'bottom':
        result = Qt.BottomToolBarArea
    else:
        result = Qt.BottomToolBarArea
    return result


class ToolbarView(standard.Dialog):
    """Provides the git-cola 'ToolBar' configure dialog"""
    SEPARATOR_TEXT = '----------------------------'

    def __init__(self, toolbar, parent=None):
        standard.Dialog.__init__(self, parent)
        self.setWindowTitle(N_('Configure toolbar'))

        self.toolbar = toolbar
        self.left_list = ToolbarTreeWidget(self)
        self.right_list = DraggableListWidget(self)
        self.text_toolbar_name = QtWidgets.QLabel()
        self.text_toolbar_name.setText(N_('Name'))
        self.toolbar_name = QtWidgets.QLineEdit()
        self.toolbar_name.setText(toolbar.windowTitle())
        self.add_separator = qtutils.create_button(N_('Add Separator'))
        self.remove_item = qtutils.create_button(N_('Remove Element'))
        checked = toolbar.show_icons()
        checkbox_text = N_('Show icon? (if available)')
        self.show_icon = qtutils.checkbox(
            checkbox_text, checkbox_text, checked)
        self.apply_button = qtutils.ok_button(N_('Apply'))
        self.close_button = qtutils.close_button()
        self.close_button.setDefault(True)

        self.right_actions = qtutils.hbox(
            defs.no_margin, defs.spacing,
            self.add_separator,
            self.remove_item)
        self.name_layout = qtutils.hbox(
            defs.no_margin, defs.spacing,
            self.text_toolbar_name,
            self.toolbar_name)
        self.left_layout = qtutils.vbox(
            defs.no_margin, defs.spacing,
            self.left_list)
        self.right_layout = qtutils.vbox(
            defs.no_margin, defs.spacing,
            self.right_list,
            self.right_actions)
        self.top_layout = qtutils.hbox(
            defs.no_margin, defs.spacing,
            self.left_layout,
            self.right_layout)
        self.actions_layout = qtutils.hbox(
            defs.no_margin, defs.spacing,
            self.show_icon,
            qtutils.STRETCH,
            self.close_button,
            self.apply_button)
        self.main_layout = qtutils.vbox(
            defs.margin, defs.spacing,
            self.name_layout,
            self.top_layout,
            self.actions_layout)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.add_separator, self.add_separator_action)
        qtutils.connect_button(self.remove_item, self.remove_item_action)
        qtutils.connect_button(self.apply_button, self.apply_action)
        qtutils.connect_button(self.close_button, self.accept)

        self.load_right_items()
        self.load_left_items()

        self.init_size(parent=parent)

    def load_right_items(self):
        for action in self.toolbar.actions():
            data = action.data()
            if data['child'] == self.toolbar.SEPARATOR:
                self.add_separator_action()
            else:
                command = self.toolbar.commands[data['child']]
                title = command['title']
                icon = command['icon']
                self.right_list.add_item(title, data, icon)

    def load_left_items(self):

        # def current_children(actions):
        #     result = []
        #     for action in actions:
        #         data = action.data()
        #         if data['child'] != self.toolbar.SEPARATOR:
        #             result.append(data['child'])

        #     return result

        for parent in self.toolbar.tree_layout:
            top = self.left_list.insert_top(parent)
            # current_items = current_children(self.toolbar.actions())
            for item in self.toolbar.tree_layout[parent]:
                command = self.toolbar.commands[item]
                child = create_child(parent, item,
                                     command['title'], command['icon'])
                top.appendRow(child)

            top.sortChildren(0, Qt.AscendingOrder)

    def add_separator_action(self):
        data = {'parent': None, 'child': self.toolbar.SEPARATOR}
        self.right_list.add_separator(self.SEPARATOR_TEXT, data)

    def remove_item_action(self):
        items = self.right_list.selectedItems()

        for item in items:
            self.right_list.takeItem(self.right_list.row(item))

    def apply_action(self):
        self.toolbar.clear()
        self.toolbar.set_show_icons(get(self.show_icon))
        self.toolbar.setWindowTitle(self.toolbar_name.text())

        for item in self.right_list.get_items():
            data = item.data(Qt.UserRole)
            self.toolbar.add_action_from_data(data)


class DraggableListMixin(object):
    items = []

    def __init__(self, widget, Base):
        self.widget = widget
        self.Base = Base

        widget.setAcceptDrops(True)
        widget.setSelectionMode(widget.SingleSelection)
        widget.setDragEnabled(True)
        widget.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        widget = self.widget
        self.Base.dragEnterEvent(widget, event)

    def dragMoveEvent(self, event):
        widget = self.widget
        self.Base.dragMoveEvent(widget, event)

    def dragLeaveEvent(self, event):
        widget = self.widget
        self.Base.dragLeaveEvent(widget, event)

    def dropEvent(self, event):
        widget = self.widget
        event.setDropAction(Qt.MoveAction)
        self.Base.dropEvent(widget, event)

    def get_items(self):
        widget = self.widget
        base = self.Base
        items = [base.item(widget, i) for i in range(base.count(widget))]

        return items


class DraggableListWidget(QtWidgets.QListWidget):
    Mixin = DraggableListMixin

    def __init__(self, parent=None):
        QtWidgets.QListWidget.__init__(self, parent)

        self.setAcceptDrops(True)
        self.setSelectionMode(self.SingleSelection)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)

        self._mixin = self.Mixin(self, QtWidgets.QListWidget)

    def dragEnterEvent(self, event):
        return self._mixin.dragEnterEvent(event)

    def dragMoveEvent(self, event):
        return self._mixin.dragMoveEvent(event)

    def dropEvent(self, event):
        return self._mixin.dropEvent(event)

    def add_separator(self, title, data):
        item = QtWidgets.QListWidgetItem()
        item.setText(title)
        item.setData(Qt.UserRole, data)

        self.addItem(item)

    def add_item(self, title, data, icon_text=None):
        item = QtWidgets.QListWidgetItem()
        item.setText(N_(title))
        item.setData(Qt.UserRole, data)

        if icon_text is not None:
            icon = getattr(icons, icon_text, None)
            item.setIcon(icon())

        self.addItem(item)

    def get_items(self):
        return self._mixin.get_items()


class ToolbarTreeWidget(standard.TreeView):

    def __init__(self, parent):
        standard.TreeView.__init__(self, parent)

        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setDropIndicatorShown(True)
        self.setRootIsDecorated(True)
        self.setHeaderHidden(True)
        self.setAlternatingRowColors(False)
        self.setSortingEnabled(False)

        self.setModel(QtGui.QStandardItemModel())

    def insert_top(self, title):
        item = create_item(title, title)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        self.model().insertRow(0, item)
        self.model().sort(0)

        return item


def create_child(parent, child, title, icon_text=None):
    data = {'parent': parent, 'child': child}
    item = create_item(title, data)

    if icon_text is not None:
        icon = getattr(icons, icon_text, None)
        item.setIcon(icon())

    return item


def create_item(name, data):
    item = QtGui.QStandardItem()

    item.setEditable(False)
    item.setDragEnabled(True)
    item.setText(N_(name))
    item.setData(data, Qt.UserRole)

    return item
