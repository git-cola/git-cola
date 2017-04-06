# encoding: utf-8
from __future__ import division, absolute_import, unicode_literals

import json

from cola import cmds
from cola import guicmds
from cola.models import prefs
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
from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy import QtWidgets

from ..i18n import N_
from .. import icons
from .. import qtutils
from . import defs


SOURCE_CONFIG = 'user'
PREFS_TOOLBAR = 'cola.toolbar'

ACTION_NEW_REPO = 1
ACTION_OPEN_REPO = 2
ACTION_OPEN_NEW_WIN = 3
ACTION_CLONE = 4
ACTION_REFRESH = 5
ACTION_FIND_FILES = 6
ACTION_EDIT_REMOTE_REPO = 7
ACTION_RECENT_EDIT = 8
ACTION_APPLY_PATCHS = 9
ACTION_EXPORT_PATCHS = 10
ACTION_SAVE_TAR_ZIP = 11
ACTION_PREFERENCES = 12

ACTION_FETCH = 20
ACTION_PULL = 21
ACTION_PUSH = 22
ACTION_STASH = 23
ACTION_CREATE_TAG = 24
ACTION_CHERRY_PICK = 25
ACTION_MERGE = 26
ACTION_ABORT_MERGE = 27
ACTION_RESET_HEAD = 28
ACTION_RESET_WORKTREE = 29
ACTION_GREP = 30
ACTION_SEARCH = 31

ACTION_AMMEND_LAST = 40
ACTION_STAGE = 41
ACTION_STAGE_ALL = 42
ACTION_UNSTAGE_ALL = 43
ACTION_UNSTAGE = 44
ACTION_LOAD_COMMIT = 45
ACTION_APPLY_COMMIT = 46

ACTION_EXPRESSION = 60
ACTION_BRANCHES = 61
ACTION_DIFFSTAT = 62

ACTION_REVIEW = 80
ACTION_CREATE = 81
ACTION_CHECKOUT = 82
ACTION_DELETE = 83
ACTION_DELETE_REMOTE = 84
ACTION_RENAME = 85
ACTION_BROWSE_CURRENT = 86
ACTION_BROWSE_OTHER = 87
ACTION_VISUALIZE_CURRENT = 88
ACTION_VISUALIZE_ALL = 89

ACTION_REBASE = 100
ACTION_REBASE_EDIT = 101
ACTION_REBASE_CONT = 102
ACTION_REBASE_IGNORE = 103
ACTION_REBASE_ABORT = 104

ACTION_SHOW_FILE_BROWSER = 110
ACTION_SHOW_DAG = 111

PARENT_FILE = 120
PARENT_ACTIONS = 121
PARENT_COMMIT = 122
PARENT_DIFF = 123
PARENT_BRANCH = 124
PARENT_REBASE = 125
PARENT_VIEW = 126

SEPARATOR = 130
SEPARATOR_TEXT = '--------------------'

SEPARATOR_ACTION = {'title': SEPARATOR, 'icon': None, 'action': None}

# We assume that a parent key defined in TOOLBAR_ACTIONS has a key
# defined with the same name in PARENT_TEXTS and a child key in
# TOOLBAR_ACTIONS a key in TOOLBAR_TEXTS. Icons are optional.
TOOLBAR_ACTIONS = {
    PARENT_FILE: {
        ACTION_NEW_REPO: lambda: guicmds.open_new_repo(),
        ACTION_OPEN_REPO: lambda: guicmds.open_repo(),
        ACTION_OPEN_NEW_WIN: lambda: guicmds.open_repo_in_new_window(),
        ACTION_CLONE: lambda: app().activeWindow().clone_repo(),
        ACTION_REFRESH: cmds.run(cmds.Refresh),
        ACTION_FIND_FILES: lambda: finder.finder(),
        ACTION_EDIT_REMOTE_REPO: lambda: editremotes.remote_editor().exec_(),
        ACTION_RECENT_EDIT: lambda: recent.browse_recent_files(),
        ACTION_APPLY_PATCHS: lambda: patch.apply_patches(),
        ACTION_EXPORT_PATCHS: lambda: guicmds.export_patches(),
        ACTION_SAVE_TAR_ZIP: lambda: app().activeWindow().save_archive(),
        ACTION_PREFERENCES: lambda: app().activeWindow().preferences()
    },
    PARENT_ACTIONS: {
        ACTION_FETCH: lambda: remote.fetch(),
        ACTION_PULL: lambda: remote.pull(),
        ACTION_PUSH: lambda: remote.push(),
        ACTION_STASH: lambda: stash.stash(),
        ACTION_CREATE_TAG: lambda: createtag.create_tag(),
        ACTION_CHERRY_PICK: lambda: guicmds.cherry_pick(),
        ACTION_MERGE: lambda: merge.local_merge(),
        ACTION_ABORT_MERGE: lambda: merge.abort_merge(),
        ACTION_RESET_HEAD: lambda: guicmds.reset_branch_head(),
        ACTION_RESET_WORKTREE: lambda: guicmds.reset_worktree(),
        ACTION_GREP: lambda: grep.grep(),
        ACTION_SEARCH: lambda: search.search()
    },
    PARENT_COMMIT: {
        ACTION_AMMEND_LAST: cmds.run(cmds.AmendMode, True),
        ACTION_STAGE: lambda: action.ActionButtons.stage(
            action.ActionButtons()),
        ACTION_STAGE_ALL: cmds.run(cmds.StageUntracked),
        ACTION_UNSTAGE_ALL: cmds.run(cmds.UnstageAll),
        ACTION_UNSTAGE: lambda: action.ActionButtons.unstage(
            action.ActionButtons()),
        ACTION_LOAD_COMMIT: lambda: guicmds.load_commitmsg(),
        ACTION_APPLY_COMMIT: cmds.run(cmds.LoadCommitMessageFromTemplate)
    },
    PARENT_DIFF: {
        ACTION_EXPRESSION: lambda: guicmds.diff_expression(),
        ACTION_BRANCHES: lambda: compare.compare_branches(),
        ACTION_DIFFSTAT: cmds.run(cmds.Diffstat)
    },
    PARENT_BRANCH: {
        ACTION_REVIEW: lambda: guicmds.review_branch(),
        ACTION_CREATE: lambda: createbranch.create_new_branch(),
        ACTION_CHECKOUT: lambda: guicmds.checkout_branch(),
        ACTION_DELETE: lambda: guicmds.delete_branch(),
        ACTION_DELETE_REMOTE: lambda: guicmds.delete_remote_branch(),
        ACTION_RENAME: lambda: guicmds.rename_branch(),
        ACTION_BROWSE_CURRENT: lambda: guicmds.browse_current(),
        ACTION_BROWSE_OTHER: lambda: guicmds.browse_other(),
        ACTION_VISUALIZE_CURRENT: cmds.run(cmds.VisualizeCurrent),
        ACTION_VISUALIZE_ALL: cmds.run(cmds.VisualizeAll)
    },
    PARENT_REBASE: {
        ACTION_REBASE: lambda: app().activeWindow().rebase_start(),
        ACTION_REBASE_EDIT: lambda: app().activeWindow().rebase_edit_todo(),
        ACTION_REBASE_CONT: lambda: app().activeWindow().rebase_continue(),
        ACTION_REBASE_IGNORE: lambda: app().activeWindow().rebase_skip(),
        ACTION_REBASE_ABORT: lambda: app().activeWindow().rebase_abort()
    },
    PARENT_VIEW: {
        ACTION_SHOW_FILE_BROWSER: lambda: browse.worktree_browser(show=True),
        ACTION_SHOW_DAG: lambda: app().activeWindow().git_dag()
    }
}
TOOLBAR_TEXTS = {
    ACTION_NEW_REPO: N_('New Repository...'),
    ACTION_OPEN_REPO: N_('Open...'),
    ACTION_OPEN_NEW_WIN: N_('Open in New Window...'),
    ACTION_CLONE: N_('Clone...'),
    ACTION_REFRESH: N_('Refresh'),
    ACTION_FIND_FILES: N_('Find Files'),
    ACTION_EDIT_REMOTE_REPO: N_('Edit Remotes...'),
    ACTION_RECENT_EDIT: N_('Recently Modified Files...'),
    ACTION_APPLY_PATCHS: N_('Apply Patches...'),
    ACTION_EXPORT_PATCHS: N_('Export Patches...'),
    ACTION_SAVE_TAR_ZIP: N_('Save As Tarball/Zip...'),
    ACTION_PREFERENCES: N_('Preferences'),

    ACTION_FETCH: N_('Fetch...'),
    ACTION_PULL: N_('Pull...'),
    ACTION_PUSH: N_('Push...'),
    ACTION_STASH: N_('Stash...'),
    ACTION_CREATE_TAG: N_('Create Tag...'),
    ACTION_CHERRY_PICK: N_('Cherry-Pick...'),
    ACTION_MERGE: N_('Merge...'),
    ACTION_ABORT_MERGE: N_('Abort Merge...'),
    ACTION_RESET_HEAD: N_('Reset Branch Head'),
    ACTION_RESET_WORKTREE: N_('Reset Worktree'),
    ACTION_GREP: N_('Grep'),
    ACTION_SEARCH: N_('Search...'),

    ACTION_STAGE: N_('Stage'),
    ACTION_AMMEND_LAST: N_('Amend Last Commit'),
    ACTION_STAGE_ALL: N_('Stage All Untracked'),
    ACTION_UNSTAGE_ALL: N_('Unstage All'),
    ACTION_UNSTAGE: N_('Unstage'),
    ACTION_LOAD_COMMIT: N_('Load Commit Message...'),
    ACTION_APPLY_COMMIT: N_('Get Commit Message Template'),

    ACTION_EXPRESSION: N_('Expression...'),
    ACTION_BRANCHES: N_('Branches...'),
    ACTION_DIFFSTAT: N_('Diffstat'),

    ACTION_REVIEW: N_('Review...'),
    ACTION_CREATE: N_('Create...'),
    ACTION_CHECKOUT: N_('Checkout...'),
    ACTION_DELETE: N_('Delete...'),
    ACTION_DELETE_REMOTE: N_('Delete Remote Branch...'),
    ACTION_RENAME: N_('Rename Branch...'),
    ACTION_BROWSE_CURRENT: N_('Browse Current Branch...'),
    ACTION_BROWSE_OTHER: N_('Browse Other Branch...'),
    ACTION_VISUALIZE_CURRENT: N_('Visualize Current Branch...'),
    ACTION_VISUALIZE_ALL: N_('Visualize All Branches...'),

    ACTION_REBASE: N_('Start Interactive Rebase...'),
    ACTION_REBASE_EDIT: N_('Edit...'),
    ACTION_REBASE_CONT: N_('Continue'),
    ACTION_REBASE_IGNORE: N_('Skip Current Patch'),
    ACTION_REBASE_ABORT: N_('Abort'),

    ACTION_SHOW_FILE_BROWSER: N_('File Browser...'),
    ACTION_SHOW_DAG: N_('DAG...')
}
TOOLBAR_ICONS = {
    ACTION_NEW_REPO: icons.new(),
    ACTION_OPEN_REPO: icons.folder(),
    ACTION_OPEN_NEW_WIN: icons.folder(),
    ACTION_CLONE: icons.repo(),
    ACTION_REFRESH: icons.sync(),
    ACTION_FIND_FILES: icons.zoom_in(),
    ACTION_SAVE_TAR_ZIP: icons.file_zip(),
    ACTION_PREFERENCES: icons.configure(),

    ACTION_PULL: icons.pull(),
    ACTION_PUSH: icons.push(),
    ACTION_CREATE_TAG: icons.tag(),
    ACTION_MERGE: icons.merge(),
    ACTION_SEARCH: icons.search(),

    ACTION_SHOW_FILE_BROWSER: icons.cola(),
    ACTION_SHOW_DAG: icons.cola()
}
PARENT_TEXTS = {
    PARENT_FILE: N_('File'),
    PARENT_ACTIONS: N_('Actions'),
    PARENT_COMMIT: N_('Commit@@verb'),
    PARENT_DIFF: N_('Diff'),
    PARENT_BRANCH: N_('Branch'),
    PARENT_REBASE: N_('Rebase'),
    PARENT_VIEW: N_('View')
}


def configure_toolbar_dialog(toolbar):
    """Launches the Toolbar configure dialog"""
    view = ToolbarView(toolbar, qtutils.active_window())
    view.show()
    return view


class ColaToolBar(QtWidgets.QToolBar):
    def __init__(self, title):
        QtWidgets.QToolBar.__init__(self)
        self.setWindowTitle(title)
        self.setObjectName(title)

    def show_icons(self, show_icons):
        if show_icons:
            self.setToolButtonStyle(Qt.ToolButtonIconOnly)
        else:
            self.setToolButtonStyle(Qt.ToolButtonTextOnly)

    def add_action_from_dict(self, action_dict):
        if action_dict['title'] == SEPARATOR:
            self.addSeparator()
        else:
            title = TOOLBAR_TEXTS[action_dict['title']]
            callback = TOOLBAR_ACTIONS[action_dict['parent']][
                action_dict['action']]
            if action_dict['icon'] in TOOLBAR_ICONS:
                icon = TOOLBAR_ICONS[action_dict['icon']]
                toolbar_action = self.addAction(icon, title, callback)
            else:
                toolbar_action = self.addAction(title, callback)

            toolbar_action.setData(action_dict)

    def get_config(self):
        prefs_model = prefs.PreferencesModel()
        toolbar_config = prefs_model.get_config(SOURCE_CONFIG,
                                                PREFS_TOOLBAR)
        result = {
            'actions_dict': {},
            'show_icons': True
        }
        if toolbar_config:
            result = json.loads(toolbar_config)

        return result

    def load_config(self):
        config = self.get_config()
        actions_dict = config['actions_dict']

        # No actions, no toolbar. This must be deferred
        if len(actions_dict) == 0:
            QtCore.QTimer.singleShot(0, lambda: self.setVisible(False))
            return

        self.show_icons(config['show_icons'])

        for action_dict in actions_dict:
            self.add_action_from_dict(action_dict)

    def save_config(self, actions_dict, show_icons):
        prefs_model = prefs.PreferencesModel()
        data = json.dumps(
            {'actions_dict': actions_dict, 'show_icons': show_icons})
        cmds.do(prefs.SetConfig, prefs_model, SOURCE_CONFIG, PREFS_TOOLBAR,
                data)

    # TODO: review widgets/main.py showdock method
    # returning parent will prevent an error thrown in showdock method
    # when user show the toolbar, because QToolBar class has no widget method
    def widget(self):
        return self


class ToolbarView(QtWidgets.QDialog):
    """Provides the git-cola 'Toolbar' configure dialog"""

    def __init__(self, toolbar, parent=None):
        QtWidgets.QDialog.__init__(self, parent)

        self.setWindowTitle(N_('Configure toolbar'))
        self.setWindowModality(Qt.WindowModal)

        self.toolbar = toolbar
        self.left_list = ToolbarTreeWidget(self)
        self.right_list = DraggableListWidget(self)
        self.add_separator = qtutils.create_button(N_('Add Separator'))
        self.remove_item = qtutils.create_button(N_('Remove Element'))

        right_names_items = self.right_items_from_toolbar()
        self.right_list.load_items(right_names_items['items'])

        left_items = self.left_items_from_dict(right_names_items['names'])
        self.left_list.load_items(left_items)

        checked = toolbar.toolButtonStyle() == Qt.ToolButtonIconOnly
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

    def add_separator_action(self):
        self.right_list.add_item(SEPARATOR_ACTION)

    def remove_item_action(self):
        items = self.right_list.selectedItems()

        for item in items:
            took_item = self.right_list.takeItem(self.right_list.row(item))
            data = took_item.data(Qt.UserRole)
            if took_item.text() != SEPARATOR_TEXT and data:
                self.left_list.update_top_item(PARENT_TEXTS[data['parent']],
                                               data)

    def apply_action(self):
        self.toolbar.clear()
        self.toolbar.show_icons(self.show_icon.isChecked())

        actions_dict = []
        for item in self.right_list.get_items():
            data = item.data(Qt.UserRole)
            actions_dict.append(data)
            self.toolbar.add_action_from_dict(data)

        self.toolbar.save_config(actions_dict, self.show_icon.isChecked())

    def right_items_from_toolbar(self):
        right_names = []
        right_items = []
        for toolbar_action in self.toolbar.actions():
            text = toolbar_action.text()
            if toolbar_action.isSeparator():
                text = SEPARATOR_TEXT

            right_names.append(text)
            data = toolbar_action.data()
            if not data:
                data = SEPARATOR_ACTION
            right_items.append(data)

        return {'names': right_names, 'items': right_items}

    def left_items_from_dict(self, right_names):
        left_items = {}
        for key, items in TOOLBAR_ACTIONS.items():
            left_items.setdefault(key, [])
            for action_key, action_callback in items.items():
                left_items.setdefault(key, [])
                if TOOLBAR_TEXTS[action_key] not in right_names:
                    icon = None
                    if action_key in TOOLBAR_ICONS:
                        icon = action_key
                    left_items[key].append({'title': action_key, 'icon': icon,
                                            'action': action_key,
                                            'parent': key})
        return left_items


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
        items = []
        for index in range(self.Base.count(widget)):
            items.append(self.Base.item(widget, index))

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

    def load_items(self, actions_dict):
        for action_dict in actions_dict:
            self.add_item(action_dict)

    def add_item(self, action_dict):
        item = QtWidgets.QListWidgetItem()

        item.setData(Qt.UserRole, action_dict)

        if action_dict['title'] == SEPARATOR:
            item.setText(SEPARATOR_TEXT)
        else:
            item.setText(TOOLBAR_TEXTS[action_dict['title']])

        if action_dict['icon'] and action_dict['icon'] in TOOLBAR_ICONS:
            item.setIcon(TOOLBAR_ICONS[action_dict['icon']])

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

    def update_top_item(self, top_item_name, action_dict):
        items = self.model().findItems(top_item_name, Qt.MatchExactly)
        top_item = items[0]

        self.create_child_item(top_item, action_dict)
        top_item.sortChildren(0, Qt.AscendingOrder)

    def load_items(self, actions_dict):
        self.model().clear()

        for key, actions_dict in actions_dict.items():
            top_item = self.create_item(PARENT_TEXTS[key])
            top_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

            for action_dict in actions_dict:
                self.create_child_item(top_item, action_dict)

            self.model().insertRow(0, top_item)
            self.model().sort(0)
            top_item.sortChildren(0, Qt.AscendingOrder)

    def create_item(self, name):
        item = QtGui.QStandardItem()

        item.setEditable(False)
        item.setDragEnabled(True)
        item.setText(name)
        item.setToolTip(name)

        return item

    def create_child_item(self, top_item,  action_dict):
        item = self.create_item(TOOLBAR_TEXTS[action_dict['title']])
        item.setData(action_dict, Qt.UserRole)

        if action_dict['icon'] and action_dict['icon'] in TOOLBAR_ICONS:
            item.setIcon(TOOLBAR_ICONS[action_dict['icon']])

        top_item.appendRow(item)

        return item
