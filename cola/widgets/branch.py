"""Provides widgets related to branchs"""
from __future__ import division, absolute_import, unicode_literals
import re

from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import cmds
from .. import gitcmds
from .. import icons
from .. import qtutils
from ..i18n import N_
from ..interaction import Interaction
from ..models import main
from ..widgets import defs
from ..widgets import standard


SEPARATOR_CHAR = '/'
NAME_LOCAL_BRANCH = N_("Local branch")
NAME_REMOTE_BRANCH = N_("Remote")
NAME_TAGS_BRANCH = N_("Tags")


class AsyncPullTask(qtutils.Task):
    """Run pull action asynchronously"""

    def __init__(self, parent, remote, branch):
        qtutils.Task.__init__(self, parent)
        self.parent = parent
        self.remote = remote
        self.args = {
            'local_branch': '',
            'no_ff': True,
            'force': False,
            'tags': False,
            'rebase': False,
            'remote_branch': branch,
            'set_upstream': False,
            'ff_only': False
        }

    def task(self):
        """Runs action and captures the result"""
        return self.parent.m.pull(self.remote, **self.args)


class BranchesWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.tree = BranchesTreeWidget(parent=self)

        self.setFocusProxy(self.tree)
        self.setToolTip(N_('Branches'))

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing, self.tree)
        self.setLayout(self.main_layout)


class BranchesTreeWidget(standard.TreeWidget):
    updated = Signal()

    def __init__(self, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)

        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)
        self.setAlternatingRowColors(False)
        self.setRootIsDecorated(True)
        self.setColumnCount(1)

        self.m = main.model()
        self.tree_helper = TreeHelper()
        self.current = None

        self.updated.connect(self.refresh, type=Qt.QueuedConnection)
        self.m.add_observer(self.m.message_updated, self.updated.emit)

        self.runtask = qtutils.RunTask(parent=self)
        self.progress = standard.ProgressDialog(N_('Pull'),
                                                N_('Updating'), self)

    # fix key == Qt.Key_Left and index.parent().isValid() error throw
    # in standard.py when navigating with keyboard and press left key
    def model(self):
        return self

    def refresh(self):
        self.current = gitcmds.current_branch()
        states = self.save_tree_states()

        local = self.create_branch_item(NAME_LOCAL_BRANCH,
                                        gitcmds.branch_list(),
                                        icons.branch())
        remote = self.create_branch_item(NAME_REMOTE_BRANCH,
                                         gitcmds.branch_list(True),
                                         icons.branch())
        tags = self.create_branch_item(NAME_TAGS_BRANCH,
                                       gitcmds.tag_list(),
                                       icons.tag())

        self.clear()
        self.addTopLevelItems([local, remote, tags])
        self.update_select_branch()
        self.load_tree_states(states)

    def contextMenuEvent(self, event):
        selected = self.selected_item()
        root = self.tree_helper.get_root(selected)

        if selected.childCount() == 0 and root is not None:
            full_name = self.tree_helper.get_full_name(selected, SEPARATOR_CHAR)
            menu = qtutils.create_menu(N_('Actions'), self)

            # all branches except current item
            if full_name != self.current:
                menu.addAction(qtutils.add_action(
                    self,
                    N_('Checkout'),
                    self.checkout_action))
                merge_menu_action = qtutils.add_action(
                    self,
                    N_('Merge in current branch'),
                    self.merge_action)
                merge_menu_action.setIcon(icons.merge())

                menu.addAction(merge_menu_action)

            # local and remote branch
            if NAME_TAGS_BRANCH != root.name:
                # local branch
                if NAME_LOCAL_BRANCH == root.name:
                    remote = gitcmds.tracked_branch(full_name)
                    if remote is not None:
                        pull_menu_action = qtutils.add_action(
                            self,
                            N_("Pull from origin"),
                            self.pull_action)
                        pull_menu_action.setIcon(icons.pull())
                        menu.addSeparator()
                        menu.addAction(pull_menu_action)

                    rename_menu_action = qtutils.add_action(
                        self,
                        N_("Rename branch"),
                        self.rename_action)
                    rename_menu_action.setIcon(icons.edit())

                    menu.addSeparator()
                    menu.addAction(rename_menu_action)

                # not current item
                if full_name != self.current:
                    delete_label = N_("Delete branch")
                    if NAME_REMOTE_BRANCH == root.name:
                        delete_label = N_("Delete remote branch")

                    delete_menu_action = qtutils.add_action(
                        self,
                        delete_label,
                        self.delete_action)
                    delete_menu_action.setIcon(icons.discard())

                    menu.addSeparator()
                    menu.addAction(delete_menu_action)

            menu.exec_(self.mapToGlobal(event.pos()))

    def save_tree_states(self):
        states = {}

        for item in self.items():
            states.update(self.tree_helper.save_state(item))

        return states

    def load_tree_states(self, states):
        for item in self.items():
            if item.name in states:
                self.tree_helper.load_state(item, states[item.name])

    def update_select_branch(self):
        parts = self.current.split(SEPARATOR_CHAR)
        current_item = self.findItems(
                            parts[len(parts) - 1],
                            Qt.MatchExactly | Qt.MatchRecursive)

        if len(current_item) > 0:
            item = current_item[0]
            tracked_branch = gitcmds.tracked_branch(self.current)

            item.setIcon(0, icons.star())

            if self.current is not None and tracked_branch is not None:
                status = {'ahead': 0, 'behind': 0}
                status_str = ""
                args = ["--oneline"]

                origin = tracked_branch + ".." + self.current
                log = self.m.git.log(origin, *args)
                status['ahead'] = len(log[1].splitlines())

                origin = self.current + ".." + tracked_branch
                log = self.m.git.log(origin, *args)
                status['behind'] = len(log[1].splitlines())

            if status["ahead"] > 0:
                status_str += "\u2191" + str(status["ahead"])

            if status["behind"] > 0:
                status_str += "  \u2193" + str(status["behind"])

            if status_str != "":
                item.setText(0, item.text(0) + "\t" + status_str)

    def create_branch_item(self, branch_name, children, icon):
        # returns a nested dictionary from a list of branches names
        # grouped by their names separated by SEPARATOR_CHAR
        def group_branches(branches):
            result = {}
            for item in branches:
                tree = result
                for part in item.split(SEPARATOR_CHAR):
                    tree = tree.setdefault(part, {})

            return result

        def generate_tree(grouped_branches):
            result = []
            for key in grouped_branches.keys():
                item = BranchTreeWidgetItem(key, icon)
                item.addChildren(generate_tree(grouped_branches[key]))

                if item.childCount() > 0:
                    item.setIcon(0, icons.ellipsis())

                result.append(item)

            result.sort(key=lambda x: x)

            return result

        branch = BranchTreeWidgetItem(branch_name, icons.ellipsis())
        branch.addChildren(generate_tree(group_branches(children)))

        return branch

    def rename_action(self):
        branch = self.tree_helper.get_full_name(self.selected_item(), SEPARATOR_CHAR)
        new_branch = qtutils.prompt(N_("Rename branch"),
                                    N_("New branch name"),
                                    branch)
        if new_branch[1] is True and new_branch[0]:
            cmds.do(cmds.RenameBranch, branch, new_branch[0])

    def pull_action(self):
        full_name = self.tree_helper.get_full_name(self.selected_item(), SEPARATOR_CHAR)
        remote_name = gitcmds.tracked_branch(full_name)

        if remote_name is not None:
            rgx = re.compile(r'^(?P<remote>[^/]+)/(?P<branch>.+)$')
            match = rgx.match(remote_name)

            if match:
                remote = match.group('remote')
                branch = match.group('branch')
                task = AsyncPullTask(self, remote, branch)
                self.runtask.start(task,
                                   progress=self.progress,
                                   finish=self.pull_completed)

    def pull_completed(self, task):
        status, out, err = task.result
        Interaction.log_status(status, out, err)
        if status > 0:
            qtutils.information(N_("Pull result"), err)

        self.refresh()

    def delete_action(self):
        title = N_('Delete Branch')
        question = N_('Delete selected branch?')
        info = N_('The branch will be deleted')
        ok_btn = N_('Delete Branch')

        full_name = self.tree_helper.get_full_name(self.selected_item(), SEPARATOR_CHAR)
        if full_name != self.current and qtutils.confirm(
                title, question, info, ok_btn):
            remote = False
            root = self.tree_helper.get_root(self.selected_item())
            if NAME_REMOTE_BRANCH == root.name:
                remote = True

            if remote is False:
                cmds.do(cmds.DeleteBranch, full_name)
            else:
                rgx = re.compile(r'^(?P<remote>[^/]+)/(?P<branch>.+)$')
                match = rgx.match(full_name)
                if match:
                    remote = match.group('remote')
                    branch = match.group('branch')
                    cmds.do(cmds.DeleteRemoteBranch, remote, branch)

    def merge_action(self):
        full_name = self.tree_helper.get_full_name(self.selected_item(), SEPARATOR_CHAR)

        if full_name != self.current:
            cmds.do(cmds.Merge, full_name, True, False, False, False)

    def checkout_action(self):
        full_name = self.tree_helper.get_full_name(self.selected_item(), SEPARATOR_CHAR)

        if full_name != self.current:
            status, out, err = self.m.git.checkout(full_name)
            Interaction.log_status(status, out, err)
            self.m.update_status()

            if status > 0:
                qtutils.information(N_("Checkout result"), err)


class BranchTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, name, icon):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self.name = name

        self.setIcon(0, icon)
        self.setText(0, name)
        self.setToolTip(0, name)
        self.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

    # fix key == Qt.Key_Left and index.parent().isValid() error throw
    # in standard.py when navigating with keyboard and press left key
    def rowCount(self):
        return 1


class TreeHelper(object):

    # load expanded items from a dict
    def load_state(self, item, state):
        if len(state.keys()) > 0:
            item.setExpanded(True)

        for i in range(item.childCount()):
            child = item.child(i)
            if child.name in state:
                self.load_state(child, state[child.name])

    # save expanded items in a dict
    def save_state(self, item):
        result = {item.name: {}}

        if item.isExpanded():
            for i in range(item.childCount()):
                child = item.child(i)
                result[item.name].update(self.save_state(child))

        return result

    # returns top level item from an item
    def get_root(self, item):
        parents = [item]
        parent = item.parent()

        while parent is not None:
            parents.append(parent)
            parent = parent.parent()

        return parents[len(parents) - 1]

    # returns item full name generated by iterating over
    # parents and joining their names with 'join_char'
    def get_full_name(self, item, join_char):
        parents = [item.name]
        parent = item.parent()

        while parent is not None:
            parents.append(parent.name)
            parent = parent.parent()

        result = join_char.join(reversed(parents))

        return result[result.find(join_char) + 1:]