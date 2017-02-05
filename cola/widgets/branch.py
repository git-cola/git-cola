"""Provides widgets related to branchs"""
from __future__ import division, absolute_import, unicode_literals
import re

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import cmds
from .. import gitcmds
from .. import icons
from .. import qtutils
from ..i18n import N_
from ..models import main
from ..widgets import defs
from ..widgets import standard


class BranchesWidget(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.tree = BranchesTreeWidget(parent=self)

        self.setFocusProxy(self.tree)
        self.setToolTip(N_('Branches'))

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing, self.tree)
        self.setLayout(self.main_layout)

        QtCore.QTimer.singleShot(0, self.reload_branches)

    def reload_branches(self):
        # Called once after the GUI is initialized
        self.tree.refresh()


class BranchesTreeWidget(standard.TreeWidget):
    updated = Signal()

    def __init__(self, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)

        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)
        self.setColumnCount(1)
        self.current = None

        self.updated.connect(self.refresh, type=Qt.QueuedConnection)

        self.m = main.model()
        self.m.add_observer(self.m.message_updated, self.updated.emit)

    def refresh(self):
        self.current = gitcmds.current_branch()
        states = self.save_tree_states()

        local_branches = self.create_branch_item(N_("Local"),
                                          gitcmds.branch_list())
        remote_branches = self.create_branch_item(N_("Remote"),
                                          gitcmds.branch_list(True))
        tags = self.create_branch_item(N_("Tags"),
                                          gitcmds.tag_list())

        self.clear()
        self.addTopLevelItems([local_branches, remote_branches, tags])
        self.set_select_branch_icon(local_branches, self.current)
        self.load_tree_states(states)

    def contextMenuEvent(self, event):
        selected = self.selected_item()
        full_name = self.get_full_name(selected)

        if selected.childCount() == 0 and full_name != self.current:
            menu = qtutils.create_menu(N_('Actions'), self)

            menu.addAction(qtutils.add_action(self, N_('Checkout'),
                            self.checkout_action))
            menu.addAction(qtutils.add_action(self,
                                     N_('Merge in current branch'),
                                     self.merge_action))
            menu.addSeparator()

            root = self.get_root(selected)

            if root is not None and N_("Tags") != root.name:
                delete_label = N_("Delete branch")

                if N_("Remote") == root.name:
                    delete_label = N_("Delete remote branch")

                delete_menu_action = qtutils.add_action(self,
                                         delete_label,
                                         self.delete_action)
                delete_menu_action.setIcon(icons.discard())
                menu.addAction(delete_menu_action)

            menu.exec_(self.mapToGlobal(event.pos()))

    def save_tree_states(self):

        # iterates over children generating a nested
        # dictionary with those that are expanded
        def save_item_state(item):
            result = {}
            for i in range(item.childCount()):
                tree = result
                child = item.child(i)
                if item.isExpanded():
                    tree = tree.setdefault(child.name, save_item_state(child))

            return result

        states = {}
        for item in self.items():
            if item.isExpanded():
                states.setdefault(item.name, save_item_state(item))

        return states

    def load_tree_states(self, states):

        # iterate over children expanding those that
        # exists in a nested dictionary
        def load_item_state(item, state):
            for key, value in state.iteritems():
                for i in range(item.childCount()):
                    child = item.child(i)
                    if child.name == key and len(value.keys()) > 0:
                        child.setExpanded(True)
                        load_item_state(child, value)

        for item in self.items():
            if item.name in states and len(states[item.name].keys()) > 0:
                item.setExpanded(True)
                load_item_state(item, states[item.name])

    def set_select_branch_icon(self, branch, current):
        for i in range(branch.childCount()):
            item = branch.child(i)

            if (item.childCount() > 0):
                self.set_select_branch_icon(item, current)
            elif self.get_full_name(item) == current:
                item.setIcon(0, icons.star())
                break

    # returns top level item from an item,
    # if is top level it will returns himself
    def get_root(self, item):
        parents = [item]
        parent = item.parent()

        while parent is not None:
            parents.append(parent)
            parent = parent.parent()

        return parents[len(parents) - 1]

    # returns branch name from tree item, it is generated by iterating
    # over parents and joining their names with the character /
    def get_full_name(self, item):
        parents = [item.name]
        parent = item.parent()

        while parent is not None:
            parents.append(parent.name)
            parent = parent.parent()

        result = '/'.join(reversed(parents))

        return result[result.find('/') + 1:]

    def create_branch_item(self, branch_name, children):

        # returns a nested dictionary from a list of branches names
        # grouped by their names separated by the character /
        def group_branches(branches):
            result = {}
            for item in branches:
                tree = result
                for part in item.split('/'):
                    tree = tree.setdefault(part, {})

            return result

        def generate_tree(group_branches):
            result = []
            for key, value in group_branches.iteritems():
                item = BranchTreeWidgetItem(key, icons.folder())
                item.addChildren(generate_tree(value))

                if (item.childCount() > 0):
                    item.setIcon(0, icons.ellipsis())

                result.append(item)

            result.sort(key=lambda x: x)

            return result

        branch = BranchTreeWidgetItem(branch_name, icons.ellipsis())
        branch.addChildren(generate_tree(group_branches(children)))

        return branch

    def delete_action(self):
        title = N_('Delete Branch')
        question = N_('Delete selected branch?')
        info = N_('The branch will be deleted')
        ok_btn = N_('Delete Branch')

        full_name = self.get_full_name(self.selected_item())
        if full_name != self.current and qtutils.confirm(
                                     title, question, info, ok_btn):
            remote = False
            root = self.get_root(self.selected_item())
            if N_("Remote") == root.name:
                    remote = True

            if remote is False:
                print("action", full_name)
                #cmds.do(cmds.DeleteBranch, selected_full_name)
            else:
                rgx = re.compile(r'^(?P<remote>[^/]+)/(?P<branch>.+)$')
                match = rgx.match(full_name)
                if match:
                    remote = match.group('remote')
                    branch = match.group('branch')
                    print("action", remote, branch)
                    #cmds.do(cmds.DeleteRemoteBranch, remote, branch)

            #self.refresh()

    def merge_action(self):
        full_name = self.get_full_name(self.selected_item())

        if full_name != self.current:
            print("action", full_name)
            #cmds.do(cmds.Merge, self.selected_item().full_name,
                                #True, False, False, False)

            self.refresh()

    def checkout_action(self):
        full_name = self.get_full_name(self.selected_item())

        if full_name != self.current:
            status, result = cmds.do(cmds.CheckoutBranch, full_name)

            if status != 0:
                qtutils.information(N_("Checkout result"), result)

            self.refresh()


class BranchTreeWidgetItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, name, icon):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self.name = name

        self.setIcon(0, icon)
        self.setText(0, name)
        self.setToolTip(0, name)
        self.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
