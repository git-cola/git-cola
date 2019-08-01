"""Provides widgets related to branches"""
from __future__ import division, absolute_import, unicode_literals
from functools import partial

from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..compat import odict
from ..compat import uchr
from ..i18n import N_
from ..interaction import Interaction
from ..widgets import defs
from ..widgets import standard
from ..qtutils import get
from .. import cmds
from .. import gitcmds
from .. import hotkeys
from .. import icons
from .. import qtutils
from .text import LineEdit


SLASH = '/'
NAME_LOCAL_BRANCH = N_('Local')
NAME_REMOTE_BRANCH = N_('Remote')
NAME_TAGS_BRANCH = N_('Tags')


def defer_fn(parent, title, fn, *args, **kwargs):
    return qtutils.add_action(parent, title, partial(fn, *args, **kwargs))


def add_branch_to_menu(menu, branch, remote_branch, remote, upstream, fn):
    """Add a remote branch to the context menu"""
    branch_remote, _ = gitcmds.parse_remote_branch(remote_branch)
    if branch_remote != remote:
        menu.addSeparator()
    action = defer_fn(menu, remote_branch, fn, branch, remote_branch)
    if remote_branch == upstream:
        action.setIcon(icons.star())
    menu.addAction(action)
    return branch_remote


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


class BranchesWidget(QtWidgets.QFrame):
    def __init__(self, context, parent):
        QtWidgets.QFrame.__init__(self, parent)
        self.model = model = context.model

        tooltip = N_('Toggle the branches filter')
        icon = icons.ellipsis()
        self.filter_button = qtutils.create_action_button(
            tooltip=tooltip, icon=icon)

        self.order_icons = (
            icons.alphabetical(),
            icons.reverse_chronological(),
        )
        tooltip_order = N_(
            'Set the sort order for branches and tags.\n'
            'Toggle between date-based and version-name-based sorting.'
        )
        icon = self.order_icon(model.ref_sort)
        self.sort_order_button = qtutils.create_action_button(
            tooltip=tooltip_order, icon=icon)

        self.tree = BranchesTreeWidget(context, parent=self)
        self.filter_widget = BranchesFilterWidget(self.tree)
        self.filter_widget.hide()

        self.setFocusProxy(self.tree)
        self.setToolTip(N_('Branches'))

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                        self.filter_widget, self.tree)
        self.setLayout(self.main_layout)

        self.toggle_action = qtutils.add_action(self, tooltip,
                                                self.toggle_filter,
                                                hotkeys.FILTER)
        qtutils.connect_button(self.filter_button, self.toggle_filter)
        qtutils.connect_button(
            self.sort_order_button, cmds.run(cmds.CycleReferenceSort, context))
        model.add_observer(model.message_ref_sort_changed, self.refresh)

    def toggle_filter(self):
        shown = not self.filter_widget.isVisible()
        self.filter_widget.setVisible(shown)
        if shown:
            self.filter_widget.setFocus()
        else:
            self.tree.setFocus()

    def order_icon(self, idx):
        return self.order_icons[idx % len(self.order_icons)]

    def refresh(self):
        icon = self.order_icon(self.model.ref_sort)
        self.sort_order_button.setIcon(icon)
        self.tree.refresh()


class BranchesTreeWidget(standard.TreeWidget):
    updated = Signal()

    def __init__(self, context, parent=None):
        standard.TreeWidget.__init__(self, parent)

        self.context = context
        self.main_model = model = context.model

        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)
        self.setAlternatingRowColors(False)
        self.setColumnCount(1)
        self.setExpandsOnDoubleClick(False)

        self.tree_helper = BranchesTreeHelper()
        self.git_helper = GitHelper(context)
        self.current_branch = None

        self.runtask = qtutils.RunTask(parent=self)
        self._active = False

        self.updated.connect(self.refresh, type=Qt.QueuedConnection)
        model.add_observer(model.message_updated, self.updated.emit)

        # Expand items when they are clicked
        self.clicked.connect(self._toggle_expanded)

        # Checkout branch when double clicked
        self.doubleClicked.connect(self.checkout_action)

    def refresh(self):
        if not self._active:
            return
        model = self.main_model
        self.current_branch = model.currentbranch

        states = self.save_tree_state()

        local_dict = self.tree_helper.group_branches(
            model.local_branches, SLASH)

        remote_dict = self.tree_helper.group_branches(
            model.remote_branches, SLASH)

        tags_dict = self.tree_helper.group_branches(model.tags, SLASH)

        ellipsis = icons.ellipsis()
        local = self.tree_helper.create_top_level_item(
            NAME_LOCAL_BRANCH, local_dict,
            icon=icons.branch(), ellipsis=ellipsis)

        remote = self.tree_helper.create_top_level_item(
            NAME_REMOTE_BRANCH, remote_dict,
            icon=icons.branch(), ellipsis=ellipsis)

        tags = self.tree_helper.create_top_level_item(
            NAME_TAGS_BRANCH, tags_dict,
            icon=icons.tag(), ellipsis=ellipsis)

        self.clear()
        self.addTopLevelItems([local, remote, tags])
        self.update_select_branch()
        self.load_tree_state(states)

    def showEvent(self, event):
        """Defer updating widgets until the widget is visible"""
        if not self._active:
            self._active = True
            self.refresh()
        return super(BranchesTreeWidget, self).showEvent(event)

    def _toggle_expanded(self, index):
        """Toggle expanded/collapsed state when items are clicked"""
        self.setExpanded(index, not self.isExpanded(index))

    def contextMenuEvent(self, event):
        """Build and execute the context menu"""
        context = self.context
        selected = self.selected_item()
        if not selected:
            return
        root = self.tree_helper.get_root(selected)

        if selected.childCount() > 0 or not root:
            return

        full_name = self.tree_helper.get_full_name(selected, SLASH)
        menu = qtutils.create_menu(N_('Actions'), self)

        # all branches except current the current branch
        if full_name != self.current_branch:
            menu.addAction(qtutils.add_action(
                menu, N_('Checkout'), self.checkout_action))
            # remote branch
            if NAME_REMOTE_BRANCH == root.name:
                label = N_('Checkout as new branch')
                action = self.checkout_new_branch_action
                menu.addAction(qtutils.add_action(menu, label, action))

            merge_menu_action = qtutils.add_action(
                menu, N_('Merge into current branch'), self.merge_action)
            merge_menu_action.setIcon(icons.merge())

            menu.addAction(merge_menu_action)

        # local and remote branch
        if NAME_TAGS_BRANCH != root.name:
            # local branch
            if NAME_LOCAL_BRANCH == root.name:

                remote = gitcmds.tracked_branch(context, full_name)
                if remote is not None:
                    menu.addSeparator()

                    pull_menu_action = qtutils.add_action(
                        menu, N_('Pull'), self.pull_action)
                    pull_menu_action.setIcon(icons.pull())
                    menu.addAction(pull_menu_action)

                    push_menu_action = qtutils.add_action(
                        menu, N_('Push'), self.push_action)
                    push_menu_action.setIcon(icons.push())
                    menu.addAction(push_menu_action)

                rename_menu_action = qtutils.add_action(
                    menu, N_('Rename Branch'), self.rename_action)
                rename_menu_action.setIcon(icons.edit())

                menu.addSeparator()
                menu.addAction(rename_menu_action)

            # not current branch
            if full_name != self.current_branch:
                delete_label = N_('Delete Branch')
                if NAME_REMOTE_BRANCH == root.name:
                    delete_label = N_('Delete Remote Branch')

                delete_menu_action = qtutils.add_action(
                    menu, delete_label, self.delete_action)
                delete_menu_action.setIcon(icons.discard())

                menu.addSeparator()
                menu.addAction(delete_menu_action)

        # manage upstreams for local branches
        if root.name == NAME_LOCAL_BRANCH:
            upstream_menu = menu.addMenu(N_('Set Upstream Branch'))
            upstream_menu.setIcon(icons.branch())
            self.build_upstream_menu(upstream_menu)

        menu.exec_(self.mapToGlobal(event.pos()))

    def build_upstream_menu(self, menu):
        """Build the "Set Upstream Branch" sub-menu"""
        context = self.context
        model = self.main_model
        selected_item = self.selected_item()
        selected_branch = self.tree_helper.get_full_name(selected_item, SLASH)
        remote = None
        upstream = None

        branches = []
        other_branches = []

        if selected_branch:
            remote = gitcmds.upstream_remote(context, selected_branch)
            upstream = gitcmds.tracked_branch(context, branch=selected_branch)

        if not remote and 'origin' in model.remotes:
            remote = 'origin'

        if remote:
            prefix = remote + '/'
            for branch in model.remote_branches:
                if branch.startswith(prefix):
                    branches.append(branch)
                else:
                    other_branches.append(branch)
        else:
            # This can be a pretty big list, let's try to split it apart
            branch_remote = ''
            target = branches
            for branch in model.remote_branches:
                new_branch_remote, _ = gitcmds.parse_remote_branch(branch)
                if branch_remote and branch_remote != new_branch_remote:
                    target = other_branches
                branch_remote = new_branch_remote
                target.append(branch)

            limit = 16
            if not other_branches and len(branches) > limit:
                branches, other_branches = (branches[:limit], branches[limit:])

        # Add an action for each remote branch
        current_remote = remote

        for branch in branches:
            current_remote = add_branch_to_menu(
                menu, selected_branch, branch, current_remote,
                upstream, self.set_upstream)

        # This list could be longer so we tuck it away in a sub-menu.
        # Selecting a branch from the non-default remote is less common.
        if other_branches:
            menu.addSeparator()
            sub_menu = menu.addMenu(N_('Other branches'))
            for branch in other_branches:
                current_remote = add_branch_to_menu(
                    sub_menu, selected_branch, branch,
                    current_remote, upstream, self.set_upstream)

    def set_upstream(self, branch, remote_branch):
        """Configure the upstream for a branch"""
        context = self.context
        remote, r_branch = gitcmds.parse_remote_branch(remote_branch)
        if remote and r_branch:
            cmds.do(cmds.SetUpstreamBranch, context, branch, remote, r_branch)

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
        context = self.context
        current_branch = self.current_branch
        top_item = self.topLevelItem(0)
        item = self.tree_helper.find_child(top_item, current_branch)

        if item is not None:
            self.tree_helper.expand_from_item(item)
            item.setIcon(0, icons.star())

            tracked_branch = gitcmds.tracked_branch(context, current_branch)
            if current_branch and tracked_branch:
                status = {'ahead': 0, 'behind': 0}
                status_str = ''

                origin = tracked_branch + '..' + self.current_branch
                log = self.git_helper.log(origin)
                status['ahead'] = len(log[1].splitlines())

                origin = self.current_branch + '..' + tracked_branch
                log = self.git_helper.log(origin)
                status['behind'] = len(log[1].splitlines())

                if status['ahead'] > 0:
                    status_str += '%s%s' % (uchr(0x2191), status['ahead'])

                if status['behind'] > 0:
                    status_str += '  %s%s' % (uchr(0x2193), status['behind'])

                if status_str:
                    item.setText(0, '%s\t%s' % (item.text(0), status_str))

    def git_action_async(self, action, args, kwarg=None, refresh_tree=False,
                         update_remotes=False):
        if kwarg is None:
            kwarg = {}
        task = AsyncGitActionTask(self, self.git_helper, action, args, kwarg,
                                  refresh_tree, update_remotes)
        progress = standard.ProgressDialog(
            N_('Executing action %s') % action, N_('Updating'), self)
        self.runtask.start(task, progress=progress,
                           finish=self.git_action_completed)

    def git_action_completed(self, task):
        status, out, err = task.result
        self.git_helper.show_result(task.action, status, out, err)
        if task.refresh_tree:
            self.refresh()
        if task.update_remotes:
            model = self.main_model
            model.update_remotes()

    def push_action(self):
        context = self.context
        branch = self.tree_helper.get_full_name(self.selected_item(), SLASH)
        remote_branch = gitcmds.tracked_branch(context, branch)
        if remote_branch:
            remote, branch_name = gitcmds.parse_remote_branch(remote_branch)
            if remote and branch_name:
                # we assume that user wants to "Push" the selected local
                # branch to a remote with same name
                self.git_action_async('push', [remote, branch_name])

    def rename_action(self):
        branch = self.tree_helper.get_full_name(self.selected_item(), SLASH)
        new_branch = qtutils.prompt(
            N_('Enter New Branch Name'),
            title=N_('Rename branch'), text=branch)
        if new_branch[1] is True and new_branch[0]:
            self.git_action_async('rename', [branch, new_branch[0]],
                                  refresh_tree=True)

    def pull_action(self):
        context = self.context
        branch = self.tree_helper.get_full_name(self.selected_item(), SLASH)
        remote_branch = gitcmds.tracked_branch(context, branch)
        if remote_branch:
            remote, branch_name = gitcmds.parse_remote_branch(remote_branch)
            if remote and branch_name:
                self.git_action_async(
                    'pull', [remote, branch_name], refresh_tree=True)

    def delete_action(self):
        title = N_('Delete Branch')
        question = N_('Delete selected branch?')
        info = N_('The branch will be no longer available.')
        ok_btn = N_('Delete Branch')

        branch = self.tree_helper.get_full_name(self.selected_item(), SLASH)

        if (branch != self.current_branch and
                Interaction.confirm(title, question, info, ok_btn)):
            remote = False
            root = self.tree_helper.get_root(self.selected_item())
            if NAME_REMOTE_BRANCH == root.name:
                remote = True

            if remote:
                remote, branch_name = gitcmds.parse_remote_branch(branch)
                if remote and branch_name:
                    self.git_action_async(
                        'delete_remote', [remote, branch_name],
                        update_remotes=True)
            else:
                self.git_action_async('delete_local', [branch])

    def merge_action(self):
        branch = self.tree_helper.get_full_name(self.selected_item(), SLASH)

        if branch != self.current_branch:
            self.git_action_async('merge', [branch], refresh_tree=True)

    def checkout_action(self):
        branch = self.tree_helper.get_full_name(self.selected_item(), SLASH)
        if branch != self.current_branch:
            self.git_action_async('checkout', [branch])

    def checkout_new_branch_action(self):
        branch = self.tree_helper.get_full_name(self.selected_item(), SLASH)
        if branch != self.current_branch:
            _, new_branch = gitcmds.parse_remote_branch(branch)
            self.git_action_async('checkout', ['-b', new_branch, branch])


class BranchTreeWidgetItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, name, icon=None):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self.name = name
        self.setText(0, name)
        self.setToolTip(0, name)
        if icon is not None:
            self.setIcon(0, icon)
        self.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

    # TODO: review standard.py 317.
    # original function returns 'QTreeWidgetItem' object which has no
    # attribute 'rowCount'. This workaround fix error throw when
    # navigating with keyboard and press left key
    @staticmethod
    def rowCount():
        return 1


class BranchesTreeHelper(object):
    @staticmethod
    def group_branches(list_branches, separator_char):
        """Convert a list of delimited strings to a nested tree dict"""
        result = odict()
        for item in list_branches:
            tree = result
            for part in item.split(separator_char):
                tree = tree.setdefault(part, odict())

        return result

    @staticmethod
    def create_top_level_item(name, dict_children,
                              icon=None, ellipsis=None):
        """Create a top level tree item and its children """

        def create_children(grouped_branches):
            """Create children items for a tree item"""
            result = []
            for k, v in grouped_branches.items():
                item = BranchTreeWidgetItem(k, icon=icon)
                item.addChildren(create_children(v))

                if item.childCount() > 0 and ellipsis is not None:
                    item.setIcon(0, ellipsis)

                result.append(item)

            return result

        branch = BranchTreeWidgetItem(name, icon=ellipsis)
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

    def find_child(self, top_level_item, name):
        """Find child by full name recursive"""
        result = None

        for i in range(top_level_item.childCount()):
            child = top_level_item.child(i)
            full_name = self.get_full_name(child, SLASH)

            if full_name == name:
                result = child
                return result
            else:
                result = self.find_child(child, name)
                if result is not None:
                    return result

        return result

    def load_state(self, item, state):
        """Load expanded items from a dict"""
        if state.keys():
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

    def __init__(self, context):
        self.context = context
        self.git = context.git

    def log(self, origin):
        return self.git.log(origin, oneline=True)

    def push(self, remote, branch):
        return self.git.push(remote, branch, verbose=True)

    def pull(self, remote, branch):
        return self.git.pull(remote, branch, no_ff=True, verbose=True)

    def delete_remote(self, remote, branch):
        return self.git.push(remote, branch, delete=True)

    def delete_local(self, branch):
        return self.git.branch(branch, D=True)

    def merge(self, branch):
        return self.git.merge(branch, no_commit=True)

    def rename(self, branch, new_branch):
        return self.git.branch(branch, new_branch, m=True)

    def checkout(self, *args, **options):
        return self.git.checkout(*args, **options)

    @staticmethod
    def show_result(command, status, out, err):
        Interaction.log_status(status, out, err)
        if status != 0:
            Interaction.command_error(N_('Error'), command, status, out, err)


class BranchesFilterWidget(QtWidgets.QWidget):
    def __init__(self, tree, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        self.tree = tree

        hint = N_('Filter branches...')
        self.text = LineEdit(parent=self, clear_button=True)
        self.text.setToolTip(hint)
        self.setFocusProxy(self.text)
        self._filter = None

        self.main_layout = qtutils.hbox(defs.no_margin, defs.spacing, self.text)
        self.setLayout(self.main_layout)

        text = self.text
        text.textChanged.connect(self.apply_filter)
        self.tree.updated.connect(self.apply_filter, type=Qt.QueuedConnection)

    def apply_filter(self):
        text = get(self.text)
        if text == self._filter:
            return
        self._apply_bold(self._filter, False)
        self._filter = text
        if text:
            self._apply_bold(text, True)

    def _apply_bold(self, text, value):
        match = Qt.MatchContains | Qt.MatchRecursive
        children = self.tree.findItems(text, match)

        for child in children:
            if child.childCount() == 0:
                font = child.font(0)
                font.setBold(value)
                child.setFont(0, font)
