# encoding: utf-8
from __future__ import division, absolute_import, unicode_literals

import copy

from cola import cmds
from cola import guicmds
from cola.qtutils import app
from cola.widgets import action
from cola.widgets import browse
from cola.widgets import compare
from cola.widgets import createbranch
from cola.widgets import createtag
from cola.widgets import editremotes
from cola.widgets import finder
from cola.widgets import grep
from cola.widgets import merge
from cola.widgets import patch
from cola.widgets import recent
from cola.widgets import remote
from cola.widgets import search
from cola.widgets import standard
from cola.widgets import stash
from qtpy import QtGui
from qtpy.QtCore import Qt
from qtpy import QtWidgets

from ..i18n import N_
from .. import icons
from .. import qtutils
from . import defs


def configure_toolbar_dialog(toolbar):
    """Launches the Toolbar configure dialog"""
    view = ToolbarView(toolbar, qtutils.active_window())
    view.show()
    return view


class ColaToolBar(QtWidgets.QToolBar):
    SEPARATOR = 130

    def __init__(self, title, actions_tree):
        QtWidgets.QToolBar.__init__(self)
        self.setWindowTitle(title)
        self.setObjectName(title)

        self.actions_tree = actions_tree

    def set_show_icons(self, show_icons):
        if show_icons:
            self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        else:
            self.setToolButtonStyle(Qt.ToolButtonTextOnly)

    def show_icons(self):
        return self.toolButtonStyle() == Qt.ToolButtonIconOnly

    def get_actions_tree(self):
        return self.actions_tree

    def get_current_actions_tree(self):
        result = copy.deepcopy(self.actions_tree)
        for toolbar_action in self.actions():
            data = toolbar_action.data()
            parent_id = data['parent_id']
            child_id = data['child_id']
            if parent_id in self.actions_tree:
                result.setdefault(parent_id, {'title': toolbar_action.text(),
                                              'items': {}})
                if child_id in self.actions_tree[parent_id]['items']:
                    del result[parent_id]['items'][child_id]

        return result

    def get_current_toolbar_actions(self):
        current_actions = []
        for toolbar_action in self.actions():
            data = toolbar_action.data()
            if data['child_id'] == self.SEPARATOR:
                current_actions.append({'title': None,
                                        'data': data, 'icon': None})
            if data and data['parent_id'] in self.actions_tree:
                items = self.actions_tree[data['parent_id']]['items']
                if data['child_id'] in items:
                    item = items[data['child_id']]
                    current_actions.append({'title': item['title'],
                                            'data': data, 'icon': item['icon']})

        return current_actions

    def get_config(self):
        current_data = [x.data() for x in self.actions()]

        return {'data': current_data, 'show_icons': self.show_icons()}

    def load_config(self, config):
        for data in config['data']:
            self.add_action_from_data(data)

        self.set_show_icons(config['show_icons'])

    def add_action_from_data(self, data):
        parent_id = data['parent_id']
        child_id = data['child_id']

        if child_id == self.SEPARATOR:
            toolbar_action = self.addSeparator()
            toolbar_action.setData(data)
        else:
            if parent_id in self.actions_tree:
                items = self.actions_tree[parent_id]['items']
                if child_id in items:
                    item = items[child_id]
                    title = N_(item['title'])
                    callback = item['action']

                    if item['icon'] is None:
                        toolbar_action = self.addAction(title, callback)
                    else:
                        icon = getattr(icons, item['icon'], None)
                        toolbar_action = self.addAction(icon(), title, callback)

                    toolbar_action.setData(data)

    def configure_toolbar(self):
        configure_toolbar_dialog(self)

    def delete_toolbar(self):
        self.parent().removeToolBar(self)

    def contextMenuEvent(self, event):
        menu = QtWidgets.QMenu()
        menu.addAction(N_('Configure toolbar'), self.configure_toolbar)
        menu.addAction(N_('Delete toolbar'), self.delete_toolbar)

        menu.exec_(event.globalPos())


class ToolbarView(QtWidgets.QDialog):
    """Provides the git-cola 'ColaToolBar' configure dialog"""
    SEPARATOR_TEXT = '----------------------------'

    def __init__(self, toolbar, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.setWindowTitle(N_('Configure toolbar'))
        self.setWindowModality(Qt.WindowModal)

        self.toolbar = toolbar
        self.left_list = ToolbarTreeWidget(self)
        self.right_list = DraggableListWidget(self)
        self.add_separator = qtutils.create_button(N_('Add Separator'))
        self.remove_item = qtutils.create_button(N_('Remove Element'))
        checked = toolbar.show_icons()
        checkbox_text = N_('Show icon? (if available)')
        self.show_icon = qtutils.checkbox(checkbox_text, checkbox_text, checked)
        self.apply_button = qtutils.ok_button(N_('Apply'))
        self.close_button = qtutils.close_button()
        self.close_button.setDefault(True)

        self.right_actions = qtutils.hbox(defs.no_margin, defs.spacing,
                                          self.add_separator, self.remove_item)
        self.left_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                        self.left_list)
        self.right_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                         self.right_list, self.right_actions)
        self.top_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                       self.left_layout, self.right_layout)
        self.actions_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                           self.show_icon, qtutils.STRETCH,
                                           self.close_button, self.apply_button)
        self.main_layout = qtutils.vbox(defs.margin, defs.spacing,
                                        self.top_layout, self.actions_layout)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.add_separator, self.add_separator_action)
        qtutils.connect_button(self.remove_item, self.remove_item_action)
        qtutils.connect_button(self.apply_button, self.apply_action)
        qtutils.connect_button(self.close_button, self.accept)

        self.resize(550, 450)
        self.load_right_items()
        self.load_left_items()

    def load_right_items(self):
        right_items = self.toolbar.get_current_toolbar_actions()
        for current in right_items:
            if current['data']['child_id'] == self.toolbar.SEPARATOR:
                self.add_separator_action()
            else:
                self.right_list.add_item(current['title'], current['data'],
                                         current['icon'])

    def load_left_items(self):
        left_items = self.toolbar.get_current_actions_tree()

        for parent_id, parent in left_items.items():
            top = self.left_list.insert_top(parent_id, parent['title'])

            for child_id, action_tree in parent['items'].items():
                child = self.left_list.insert_child(parent_id, child_id,
                                                    action_tree['title'],
                                                    action_tree['icon'])

                top.appendRow(child)

            top.sortChildren(0, Qt.AscendingOrder)

    def add_separator_action(self):
        data = {'parent_id': None, 'child_id': self.toolbar.SEPARATOR}
        self.right_list.add_separator(self.SEPARATOR_TEXT, data)

    def remove_item_action(self):
        items = self.right_list.selectedItems()

        for item in items:
            took_item = self.right_list.takeItem(self.right_list.row(item))
            data = took_item.data(Qt.UserRole)
            if data and data['child_id'] != self.toolbar.SEPARATOR:
                actions_tree = self.toolbar.get_actions_tree()
                if data['parent_id'] in actions_tree:
                    parent_dict = actions_tree[data['parent_id']]
                    child_dict = parent_dict['items'][data['child_id']]
                    self.left_list.update_top_item(parent_dict['title'],
                                                   data['child_id'],
                                                   child_dict['title'],
                                                   child_dict['icon'])

    def apply_action(self):
        self.toolbar.clear()
        self.toolbar.set_show_icons(self.show_icon.isChecked())

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

    def create_item(self, name, data):
        item = QtGui.QStandardItem()

        item.setEditable(False)
        item.setDragEnabled(True)
        item.setText(N_(name))
        item.setToolTip(N_(name))
        item.setData(data, Qt.UserRole)

        return item

    def insert_top(self, parent_id, title):
        item = self.create_item(title, parent_id)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        self.model().insertRow(0, item)
        self.model().sort(0)

        return item

    def insert_child(self, parent_id, child_id, title, icon_text=None):
        data = {'parent_id': parent_id, 'child_id': child_id}
        item = self.create_item(title, data)

        if icon_text is not None:
            icon = getattr(icons, icon_text, None)
            item.setIcon(icon())

        return item

    def update_top_item(self, parent_title, child_id, title, icon):
        items = self.model().findItems(N_(parent_title), Qt.MatchExactly)

        if len(items) > 0:
            top = items[0]
            child = self.insert_child(top.data(Qt.UserRole), child_id, title,
                                      icon)
            top.appendRow(child)
            top.sortChildren(0, Qt.AscendingOrder)


MAIN_ACTIONS = {
    120: {
        'title': 'File',
        'items': {
            1: {
                'title': 'New Repository...',
                'action': lambda: guicmds.open_new_repo(),
                'icon': 'new'
            },
            2: {
                'title': 'Open...',
                'action': lambda: guicmds.open_repo(),
                'icon': 'folder'
            },
            3: {
                'title': 'Open in New Window...',
                'action': lambda: guicmds.open_repo_in_new_window(),
                'icon': 'folder'
            },
            4: {
                'title': 'Clone...',
                'action': lambda: app().activeWindow().clone_repo(),
                'icon': 'repo'
            },
            5: {
                'title': 'Refresh...',
                'action': cmds.run(cmds.Refresh),
                'icon': 'sync'
            },
            6: {
                'title': 'Find Files',
                'action': lambda: finder.finder(),
                'icon': 'zoom_in'
            },
            7: {
                'title': 'Edit Remotes...',
                'action': lambda: editremotes.remote_editor().exec_(),
                'icon': None
            },
            8: {
                'title': 'Recently Modified Files...',
                'action': lambda: recent.browse_recent_files(),
                'icon': None
            },
            9: {
                'title': 'Apply Patches...',
                'action': lambda: patch.apply_patches(),
                'icon': None
            },
            10: {
                'title': 'Export Patches...',
                'action': lambda: guicmds.export_patches(),
                'icon': None
            },
            11: {
                'title': 'Save As Tarball/Zip...',
                'action': lambda: app().activeWindow().save_archive(),
                'icon': 'file_zip'
            },
            12: {
                'title': 'Preferences',
                'action': lambda: app().activeWindow().preferences(),
                'icon': 'configure'
            }
        }
    },
    121: {
        'title': 'Actions',
        'items': {
            20: {
                'title': 'Fetch...',
                'action': lambda: remote.fetch(),
                'icon': None
            },
            21: {
                'title': 'Pull...',
                'action': lambda: remote.pull(),
                'icon': 'pull'
            },
            22: {
                'title': 'Push...',
                'action': lambda: remote.push(),
                'icon': 'push'
            },
            23: {
                'title': 'Stash...',
                'action': lambda: stash.stash(),
                'icon': None
            },
            24: {
                'title': 'Create Tag...',
                'action': lambda: createtag.create_tag(),
                'icon': 'tag'
            },
            25: {
                'title': 'Cherry-Pick...',
                'action': lambda: guicmds.cherry_pick(),
                'icon': None
            },
            26: {
                'title': 'Merge...',
                'action': lambda: merge.local_merge(),
                'icon': 'merge'
            },
            27: {
                'title': 'Abort Merge...',
                'action': lambda: merge.abort_merge(),
                'icon': None
            },
            28: {
                'title': 'Reset Branch Head',
                'action': lambda: guicmds.reset_branch_head(),
                'icon': None
            },
            29: {
                'title': 'Reset Worktree',
                'action': lambda: guicmds.reset_worktree(),
                'icon': None
            },
            30: {
                'title': 'Grep',
                'action': lambda: grep.grep(),
                'icon': None
            },
            31: {
                'title': 'Search...',
                'action': lambda: search.search(),
                'icon': 'search'
            }
        }
    },
    122: {
        'title': 'Commit@@verb',
        'items': {
            40: {
                'title': 'Stage',
                'action': cmds.run(cmds.AmendMode, True),
                'icon': None
            },
            41: {
                'title': 'Amend Last Commit',
                'action': lambda: action.ActionButtons.stage(
                    action.ActionButtons()),
                'icon': None
            },
            42: {
                'title': 'Stage All Untracked',
                'action': cmds.run(cmds.StageUntracked),
                'icon': None
            },
            43: {
                'title': 'Unstage All',
                'action': cmds.run(cmds.UnstageAll),
                'icon': None
            },
            44: {
                'title': 'Unstage',
                'action': lambda: action.ActionButtons.unstage(
                    action.ActionButtons()),
                'icon': None
            },
            45: {
                'title': 'Load Commit Message...',
                'action': lambda: guicmds.load_commitmsg(),
                'icon': None
            },
            46: {
                'title': 'Get Commit Message Template',
                'action': cmds.run(cmds.LoadCommitMessageFromTemplate),
                'icon': None
            }
        }
    },
    123: {
        'title': 'Diff',
        'items': {
            60: {
                'title': 'Expression...',
                'action': lambda: guicmds.diff_expression(),
                'icon': None
            },
            61: {
                'title': 'Branches...',
                'action': lambda: compare.compare_branches(),
                'icon': None
            },
            62: {
                'title': 'Diffstat',
                'action': cmds.run(cmds.Diffstat),
                'icon': None
            }
        }
     },
    124: {
        'title': 'Branch',
        'items': {
            80: {
                'title': 'Review...',
                'action': lambda: guicmds.review_branch(),
                'icon': None
            },
            81: {
                'title': 'Create...',
                'action': lambda: createbranch.create_new_branch(),
                'icon': None
            },
            82: {
                'title': 'Checkout...',
                'action': lambda: guicmds.checkout_branch(),
                'icon': None
            },
            83: {
                'title': 'Delete...',
                'action': lambda: guicmds.delete_branch(),
                'icon': None
            },
            84: {
                'title': 'Delete Remote Branch...',
                'action': lambda: guicmds.delete_remote_branch(),
                'icon': None
            },
            85: {
                'title': 'Rename Branch...',
                'action': lambda: guicmds.rename_branch(),
                'icon': None
            },
            86: {
                'title': 'Browse Current Branch...',
                'action': lambda: guicmds.browse_current(),
                'icon': None
            },
            87: {
                'title': 'Browse Other Branch...',
                'action': lambda: guicmds.browse_other(),
                'icon': None
            },
            88: {
                'title': 'Visualize Current Branch...',
                'action': cmds.run(cmds.VisualizeCurrent),
                'icon': None
            },
            89: {
                'title': 'Visualize All Branches...',
                'action': cmds.run(cmds.VisualizeAll),
                'icon': None
            }
        }
    },
    125: {
        'title': 'Rebase',
        'items': {
            100: {
                'title': 'Start Interactive Rebase...',
                'action': lambda: app().activeWindow().rebase_start(),
                'icon': None
            },
            101: {
                'title': 'Edit...',
                'action': lambda: app().activeWindow().rebase_edit_todo(),
                'icon': None
            },
            102: {
                'title': 'Continue',
                'action': lambda: app().activeWindow().rebase_continue(),
                'icon': None
            },
            103: {
                'title': 'Skip Current Patch',
                'action': lambda: app().activeWindow().rebase_skip(),
                'icon': None
            },
            104: {
                'title': 'Abort',
                'action': lambda: app().activeWindow().rebase_abort(),
                'icon': None
            }
        }
    },
    126: {
        'title': 'View',
        'items': {
            120: {
                'title': 'File Browser...',
                'action': lambda: browse.worktree_browser(show=True),
                'icon': 'cola'
            },
            121: {
                'title': 'DAG...',
                'action': lambda: app().activeWindow().git_dag(),
                'icon': 'cola'
            }
        }
    }
}
