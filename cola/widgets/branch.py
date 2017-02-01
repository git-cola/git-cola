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

        local_branches = self.create_branch_item(N_("Local"),
                                          gitcmds.branch_list(),
                                          self.current)
        remote_branches = self.create_branch_item(N_("Remote"),
                                          gitcmds.branch_list(True))
        tag_branches = self.create_branch_item(N_("Tags"),
                                          gitcmds.tag_list())

        self.clear()
        self.addTopLevelItems([local_branches, remote_branches, tag_branches])

        self.expandItem(local_branches)

    def contextMenuEvent(self, event):
        selected = self.selected_item()

        if selected.parent() is not None and selected.name != self.current:
            menu = qtutils.create_menu(N_('Actions'), self)
            menu.addAction(qtutils.add_action(self, N_('Checkout'),
                            self.checkout_action))
            menu.addAction(qtutils.add_action(self,
                                     N_('Merge in current branch'),
                                     self.merge_action))
            menu.addSeparator()

            if N_("Tags") != selected.parent().name:
                delete_label = N_("Delete branch")

                if N_("Remote") == selected.parent().name:
                    delete_label = N_("Delete remote branch")

                delete_menu_action = qtutils.add_action(self,
                                         delete_label,
                                         self.delete_action)
                delete_menu_action.setIcon(icons.discard())
                menu.addAction(delete_menu_action)

            menu.exec_(self.mapToGlobal(event.pos()))

    def create_branch_item(self, branch_name, children, current=False):
        builder = BuildItem()

        branch = BranchTreeWidgetItem(branch_name, icons.ellipsis())
        items = [builder.get(child, current) for child in children]
        items.sort(key=lambda x: x)

        branch.addChildren(items)

        return branch

    def delete_action(self):
        title = N_('Delete Branch')
        question = N_('Delete selected branch?')
        info = N_('The branch will be deleted')
        ok_btn = N_('Delete Branch')

        selected_name = self.selected_item().name
        if selected_name != self.current and qtutils.confirm(
                                     title, question, info, ok_btn):
            remote = False
            if N_("Remote") == self.selected_item().parent().name:
                    remote = True

            if remote is False:
                cmds.do(cmds.DeleteBranch, self.selected_item().name)
            else:
                rgx = re.compile(r'^(?P<remote>[^/]+)/(?P<branch>.+)$')
                match = rgx.match(selected_name)
                if match:
                    remote = match.group('remote')
                    branch = match.group('branch')
                    cmds.do(cmds.DeleteRemoteBranch, remote, branch)

            self.refresh()

    def merge_action(self):
        if self.selected_item().name != self.current:
            cmds.do(cmds.Merge, self.selected_item().name,
                                True, False, False, False)

            self.refresh()

    def checkout_action(self):
        if self.selected_item().name != self.current:
            status, result = cmds.do(cmds.CheckoutBranch,
                                     self.selected_item().name)

            if status != 0:
                qtutils.information(N_("Checkout result"), result)

            self.refresh()


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
        self.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
