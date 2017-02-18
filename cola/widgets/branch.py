"""Provides widgets related to branchs"""
from __future__ import division, absolute_import, unicode_literals
import re

from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

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


class AsyncGitActionTask(qtutils.Task):
    """Run git action asynchronously"""

    def __init__(self, parent, git_helper, action, args, kwarg,
                 refresh_tree, update_remotes):
        qtutils.Task.__init__(self, parent)
        self.git_helper = git_helper
        self.action = action
        self.args = args
        self.kwarg = kwarg
        self.refresh_tree = refresh_tree
        self.update_remotes = update_remotes

    def task(self):
        """Runs action and captures the result"""
        git_action = getattr(self.git_helper, self.action)
        return git_action(*self.args, **self.kwarg)


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
        standard.TreeWidget.__init__(self, parent)

        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)
        self.setAlternatingRowColors(False)
        self.setRootIsDecorated(True)
        self.setColumnCount(1)

        model = main.model()

        self.tree_helper = BranchesTreeHelper()
        self.git_helper = GitHelper(model.git)
        self.current_branch = None

        self.updated.connect(self.refresh, type=Qt.QueuedConnection)
        model.add_observer(model.message_updated, self.updated.emit)

        self.runtask = qtutils.RunTask(parent=self)

    # fix key == Qt.Key_Left and index.parent().isValid() error throw
    # in standard.py when navigating with keyboard and press left key
    def model(self):
        return self

    def refresh(self):
        print("refresh\n")
        self.current_branch = gitcmds.current_branch()
        states = self.save_tree_state()

        local_dict = self.tree_helper.group_branches(gitcmds.branch_list(),
                                                     SEPARATOR_CHAR)
        remote_dict = self.tree_helper.group_branches(gitcmds.branch_list(True),
                                                      SEPARATOR_CHAR)
        tags_dict = self.tree_helper.group_branches(gitcmds.tag_list(),
                                                    SEPARATOR_CHAR)

        local = self.tree_helper.create_top_level_item(NAME_LOCAL_BRANCH,
                                                       local_dict,
                                                       icons.branch())
        remote = self.tree_helper.create_top_level_item(NAME_REMOTE_BRANCH,
                                                        remote_dict,
                                                        icons.branch())
        tags = self.tree_helper.create_top_level_item(NAME_TAGS_BRANCH,
                                                      tags_dict,
                                                      icons.tag())

        self.clear()
        self.addTopLevelItems([local, remote, tags])
        self.update_select_branch()
        self.load_tree_state(states)

    def contextMenuEvent(self, event):
        selected = self.selected_item()
        root = self.tree_helper.get_root(selected)

        if selected.childCount() == 0 and root is not None:
            full_name = self.tree_helper.get_full_name(selected, SEPARATOR_CHAR)
            menu = qtutils.create_menu(N_('Actions'), self)

            # all branches except current item
            if full_name != self.current_branch:
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
                if full_name != self.current_branch:
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

    def save_tree_state(self):
        states = {}

        for item in self.items():
            states.update(self.tree_helper.save_state(item))

        return states

    def load_tree_state(self, states):
        for item in self.items():
            if item.name in states:
                self.tree_helper.load_state(item, states[item.name])

    def update_select_branch(self):

        def find_child(top_level_item, name):
            """Find child by name recursive"""
            def find_recursive(parent, child_name):
                result = None

                for i in range(parent.childCount()):
                    child = parent.child(i)
                    full_name = self.tree_helper.get_full_name(
                        child,
                        SEPARATOR_CHAR)

                    if full_name == child_name:
                        result = child
                        return result
                    else:
                        result = find_recursive(child, child_name)
                        if result is not None:
                            return result

                return result

            return find_recursive(top_level_item, name)

        item = find_child(
            self.topLevelItem(0),
            self.current_branch)

        if item is not None:
            self.tree_helper.expand_from_item(item)
            item.setIcon(0, icons.star())

            tracked_branch = gitcmds.tracked_branch(self.current_branch)

            if self.current_branch is not None and tracked_branch is not None:
                status = {'ahead': 0, 'behind': 0}
                status_str = ""
                args = ["--oneline"]

                origin = tracked_branch + ".." + self.current_branch
                log = self.git_helper.log(origin, args)
                status['ahead'] = len(log[1].splitlines())

                origin = self.current_branch + ".." + tracked_branch
                log = self.git_helper.log(origin, args)
                status['behind'] = len(log[1].splitlines())

                if status["ahead"] > 0:
                    status_str += "\u2191" + str(status["ahead"])

                if status["behind"] > 0:
                    status_str += "  \u2193" + str(status["behind"])

                if status_str != "":
                    item.setText(0, item.text(0) + "\t" + status_str)

    def git_action_async(self, action, args, kwarg=None,
                         refresh_tree=False, update_remotes=False):
        if kwarg is None:
            kwarg = {}

        task = AsyncGitActionTask(self, self.git_helper, action, args, kwarg,
                                  refresh_tree, update_remotes)
        progress = standard.ProgressDialog(
            N_('Executing action %s') % action,
            N_('Updating'), self)

        self.runtask.start(
            task,
            progress=progress,
            finish=self.git_action_completed)

    def git_action_completed(self, task):
        status, out, err = task.result
        self.git_helper.show_result(task.action, status, out, err)

        if task.refresh_tree:
            self.refresh()

        if task.update_remotes:
            model = main.model()
            model.update_remotes()

    def rename_action(self):
        branch = self.tree_helper.get_full_name(
            self.selected_item(),
            SEPARATOR_CHAR)
        new_branch = qtutils.prompt(
            N_("Rename branch"),
            N_("New branch name"),
            branch)
        if new_branch[1] is True and new_branch[0]:
            self.git_action_async('rename', [branch, new_branch[0]],
                                  refresh_tree=True)

    def pull_action(self):
        branch = self.tree_helper.get_full_name(
            self.selected_item(),
            SEPARATOR_CHAR)
        remote_branch = gitcmds.tracked_branch(branch)

        if remote_branch is not None:
            rgx = re.compile(r'^(?P<remote>[^/]+)/(?P<branch>.+)$')
            match = rgx.match(remote_branch)

            if match:
                remote = match.group('remote')
                branch_name = match.group('branch')
                self.git_action_async('pull', [remote, branch_name],
                                      refresh_tree=True)

    def delete_action(self):
        title = N_('Delete Branch')
        question = N_('Delete selected branch?')
        info = N_('The branch will be no longer available.')
        ok_btn = N_('Delete Branch')

        branch = self.tree_helper.get_full_name(self.selected_item(),
                                                SEPARATOR_CHAR)

        if branch != self.current_branch and qtutils.confirm(title, question,
                                                             info, ok_btn):
            remote = False
            root = self.tree_helper.get_root(self.selected_item())
            if NAME_REMOTE_BRANCH == root.name:
                remote = True

            if remote is False:
                self.git_action_async('delete_local', [branch])
            else:
                rgx = re.compile(r'^(?P<remote>[^/]+)/(?P<branch>.+)$')
                match = rgx.match(branch)
                if match:
                    remote = match.group('remote')
                    branch_name = match.group('branch')
                    self.git_action_async('delete_remote',
                                          [remote, branch_name],
                                          update_remotes=True)

    def merge_action(self):
        branch = self.tree_helper.get_full_name(
            self.selected_item(),
            SEPARATOR_CHAR)

        if branch != self.current_branch:
            self.git_action_async('merge', [branch], refresh_tree=True)

    def checkout_action(self):
        branch = self.tree_helper.get_full_name(self.selected_item(),
                                                SEPARATOR_CHAR)

        if branch != self.current_branch:
            self.git_action_async('checkout', [branch])


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
    @staticmethod
    def rowCount():
        return 1


class BranchesTreeHelper(object):
    @staticmethod
    def group_branches(list_branches, separator_char):
        """Convert a list of delimited strings to a nested tree dict"""
        result = {}
        for item in list_branches:
            tree = result
            for part in item.split(separator_char):
                tree = tree.setdefault(part, {})

        return result

    @staticmethod
    def create_top_level_item(name, dict_children, child_icon):
        """Create a top level tree item and its children """

        def create_children(grouped_branches):
            """Create children items for a tree item"""
            result = []
            for key in grouped_branches.keys():
                item = BranchTreeWidgetItem(key, child_icon)
                item.addChildren(create_children(grouped_branches[key]))

                if item.childCount() > 0:
                    item.setIcon(0, icons.ellipsis())

                result.append(item)

            result.sort(key=lambda x: x)

            return result

        branch = BranchTreeWidgetItem(name, icons.ellipsis())
        branch.addChildren(create_children(dict_children))

        return branch

    @staticmethod
    def get_root(item):
        """Returns top level item from an item"""
        parents = [item]
        parent = item.parent()

        while parent is not None:
            parents.append(parent)
            parent = parent.parent()

        return parents[len(parents) - 1]

    @staticmethod
    def get_full_name(item, join_char):
        """Returns item full name generated by iterating over
        parents and joining their names with 'join_char'"""
        parents = [item.name]
        parent = item.parent()

        while parent is not None:
            parents.append(parent.name)
            parent = parent.parent()

        result = join_char.join(reversed(parents))

        return result[result.find(join_char) + 1:]

    @staticmethod
    def expand_from_item(item):
        """Expand tree parents from item"""
        parent = item.parent()

        while parent is not None:
            parent.setExpanded(True)
            parent = parent.parent()

    def load_state(self, item, state):
        """Load expanded items from a dict"""
        if len(state.keys()) > 0:
            item.setExpanded(True)

        for i in range(item.childCount()):
            child = item.child(i)
            if child.name in state:
                self.load_state(child, state[child.name])

    def save_state(self, item):
        """Save expanded items in a dict"""
        result = {item.name: {}}

        if item.isExpanded():
            for i in range(item.childCount()):
                child = item.child(i)
                result[item.name].update(self.save_state(child))

        return result


class GitHelper(object):
    def __init__(self, git):
        self.git = git

    def log(self, origin, args):
        return self.git.log(origin, *args)

    def pull(self, remote, branch):
        return self.git.pull(
            remote,
            branch,
            no_ff=True,
            verbose=True)

    def delete_remote(self, remote, branch):
        return self.git.push(remote, branch, delete=True)

    def delete_local(self, branch):
        return self.git.branch(branch, D=True)

    def merge(self, branch):
        return self.git.merge(
            branch,
            gpg_sign=False,
            no_ff=False,
            no_commit=True,
            squash=False)

    def rename(self, branch, new_branch):
        return self.git.branch(branch, new_branch, M=True)

    def checkout(self, branch):
        return self.git.checkout(branch)

    @staticmethod
    def show_result(command, status, out, err):
        Interaction.log_status(status, out, err)

        if status > 0:
            title = N_('Error %s') % command
            msg = (N_('"%(command)s" returned exit status %(status)d') %
                   dict(command=command, status=status))
            details = N_('Output:\n%s') % out
            if err:
                details += '\n\n'
                details += N_('Errors: %s') % err

            qtutils.critical(title, msg, details)