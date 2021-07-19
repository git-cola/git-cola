"""Provides widgets related to branches"""
from __future__ import absolute_import, division, print_function, unicode_literals
from functools import partial

from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

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

    def __init__(self, parent, git_helper, action, args, kwarg):
        qtutils.Task.__init__(self, parent)
        self.git_helper = git_helper
        self.action = action
        self.args = args
        self.kwarg = kwarg

    def task(self):
        """Runs action and captures the result"""
        git_action = getattr(self.git_helper, self.action)
        return git_action(*self.args, **self.kwarg)


class BranchesWidget(QtWidgets.QFrame):
    updated = Signal()

    def __init__(self, context, parent):
        QtWidgets.QFrame.__init__(self, parent)
        self.model = model = context.model

        tooltip = N_('Toggle the branches filter')
        icon = icons.ellipsis()
        self.filter_button = qtutils.create_action_button(tooltip=tooltip, icon=icon)

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
            tooltip=tooltip_order, icon=icon
        )

        self.tree = BranchesTreeWidget(context, parent=self)
        self.filter_widget = BranchesFilterWidget(self.tree)
        self.filter_widget.hide()

        self.setFocusProxy(self.tree)
        self.setToolTip(N_('Branches'))

        self.main_layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.filter_widget, self.tree
        )
        self.setLayout(self.main_layout)

        self.toggle_action = qtutils.add_action(
            self, tooltip, self.toggle_filter, hotkeys.FILTER
        )
        qtutils.connect_button(self.filter_button, self.toggle_filter)
        qtutils.connect_button(
            self.sort_order_button, cmds.run(cmds.CycleReferenceSort, context)
        )

        self.updated.connect(self.refresh, Qt.QueuedConnection)
        model.add_observer(model.message_refs_updated, self.updated.emit)

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


# pylint: disable=too-many-ancestors
class BranchesTreeWidget(standard.TreeWidget):
    updated = Signal()

    def __init__(self, context, parent=None):
        standard.TreeWidget.__init__(self, parent)

        model = context.model
        self.context = context

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
        # pylint: disable=no-member
        self.clicked.connect(self._toggle_expanded)

        # Checkout branch when double clicked
        self.doubleClicked.connect(self.checkout_action)

    def refresh(self):
        if not self._active:
            return
        model = self.context.model
        self.current_branch = model.currentbranch

        states = self.save_tree_state()
        ellipsis = icons.ellipsis()

        local_tree = create_tree_entries(model.local_branches)
        local_tree.basename = N_('Local')
        local = create_toplevel_item(local_tree, icon=icons.branch(), ellipsis=ellipsis)

        remote_tree = create_tree_entries(model.remote_branches)
        remote_tree.basename = N_('Remote')
        remote = create_toplevel_item(
            remote_tree, icon=icons.branch(), ellipsis=ellipsis
        )

        tags_tree = create_tree_entries(model.tags)
        tags_tree.basename = N_('Tags')
        tags = create_toplevel_item(tags_tree, icon=icons.tag(), ellipsis=ellipsis)

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
        # Only allow actions on leaf nodes that have a valid refname.
        if not selected.refname:
            return

        root = get_toplevel_item(selected)
        full_name = selected.refname
        menu = qtutils.create_menu(N_('Actions'), self)

        # all branches except current the current branch
        if full_name != self.current_branch:
            menu.addAction(
                qtutils.add_action(menu, N_('Checkout'), self.checkout_action)
            )
            # remote branch
            if root.name == N_('Remote'):
                label = N_('Checkout as new branch')
                action = self.checkout_new_branch_action
                menu.addAction(qtutils.add_action(menu, label, action))

            merge_menu_action = qtutils.add_action(
                menu, N_('Merge into current branch'), self.merge_action
            )
            merge_menu_action.setIcon(icons.merge())

            menu.addAction(merge_menu_action)

        # local and remote branch
        if root.name != N_('Tags'):
            # local branch
            if root.name == N_('Local'):

                remote = gitcmds.tracked_branch(context, full_name)
                if remote is not None:
                    menu.addSeparator()

                    pull_menu_action = qtutils.add_action(
                        menu, N_('Pull'), self.pull_action
                    )
                    pull_menu_action.setIcon(icons.pull())
                    menu.addAction(pull_menu_action)

                    push_menu_action = qtutils.add_action(
                        menu, N_('Push'), self.push_action
                    )
                    push_menu_action.setIcon(icons.push())
                    menu.addAction(push_menu_action)

                rename_menu_action = qtutils.add_action(
                    menu, N_('Rename Branch'), self.rename_action
                )
                rename_menu_action.setIcon(icons.edit())

                menu.addSeparator()
                menu.addAction(rename_menu_action)

            # not current branch
            if full_name != self.current_branch:
                delete_label = N_('Delete Branch')
                if root.name == N_('Remote'):
                    delete_label = N_('Delete Remote Branch')

                delete_menu_action = qtutils.add_action(
                    menu, delete_label, self.delete_action
                )
                delete_menu_action.setIcon(icons.discard())

                menu.addSeparator()
                menu.addAction(delete_menu_action)

        # manage upstreams for local branches
        if root.name == N_('Local'):
            upstream_menu = menu.addMenu(N_('Set Upstream Branch'))
            upstream_menu.setIcon(icons.branch())
            self.build_upstream_menu(upstream_menu)

        menu.exec_(self.mapToGlobal(event.pos()))

    def build_upstream_menu(self, menu):
        """Build the "Set Upstream Branch" sub-menu"""
        context = self.context
        model = context.model
        selected_branch = self.selected_refname()
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
                menu,
                selected_branch,
                branch,
                current_remote,
                upstream,
                self.set_upstream,
            )

        # This list could be longer so we tuck it away in a sub-menu.
        # Selecting a branch from the non-default remote is less common.
        if other_branches:
            menu.addSeparator()
            sub_menu = menu.addMenu(N_('Other branches'))
            for branch in other_branches:
                current_remote = add_branch_to_menu(
                    sub_menu,
                    selected_branch,
                    branch,
                    current_remote,
                    upstream,
                    self.set_upstream,
                )

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
        item = find_by_refname(top_item, current_branch)

        if item is not None:
            expand_item_parents(item)
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

    def git_action_async(self, action, args, kwarg=None):
        if kwarg is None:
            kwarg = {}
        task = AsyncGitActionTask(self, self.git_helper, action, args, kwarg)
        progress = standard.progress(
            N_('Executing action %s') % action, N_('Updating'), self
        )
        self.runtask.start(task, progress=progress, finish=self.git_action_completed)

    def git_action_completed(self, task):
        status, out, err = task.result
        self.git_helper.show_result(task.action, status, out, err)
        self.context.model.update_refs()

    def push_action(self):
        context = self.context
        branch = self.selected_refname()
        remote_branch = gitcmds.tracked_branch(context, branch)
        if remote_branch:
            remote, branch_name = gitcmds.parse_remote_branch(remote_branch)
            if remote and branch_name:
                # we assume that user wants to "Push" the selected local
                # branch to a remote with same name
                self.git_action_async('push', [remote, branch_name])

    def rename_action(self):
        branch = self.selected_refname()
        new_branch, ok = qtutils.prompt(
            N_('Enter New Branch Name'), title=N_('Rename branch'), text=branch
        )
        if ok and new_branch:
            self.git_action_async('rename', [branch, new_branch])

    def pull_action(self):
        context = self.context
        branch = self.selected_refname()
        if not branch:
            return
        remote_branch = gitcmds.tracked_branch(context, branch)
        if remote_branch:
            remote, branch_name = gitcmds.parse_remote_branch(remote_branch)
            if remote and branch_name:
                self.git_action_async('pull', [remote, branch_name])

    def delete_action(self):
        branch = self.selected_refname()
        if not branch or branch == self.current_branch:
            return

        remote = False
        root = get_toplevel_item(self.selected_item())
        if root.name == N_('Remote'):
            remote = True

        if remote:
            remote, branch = gitcmds.parse_remote_branch(branch)
            if remote and branch:
                cmds.do(cmds.DeleteRemoteBranch, self.context, remote, branch)
        else:
            cmds.do(cmds.DeleteBranch, self.context, branch)

    def merge_action(self):
        branch = self.selected_refname()
        if branch and branch != self.current_branch:
            self.git_action_async('merge', [branch])

    def checkout_action(self):
        branch = self.selected_refname()
        if branch and branch != self.current_branch:
            self.git_action_async('checkout', [branch])

    def checkout_new_branch_action(self):
        branch = self.selected_refname()
        if branch and branch != self.current_branch:
            _, new_branch = gitcmds.parse_remote_branch(branch)
            self.git_action_async('checkout', ['-b', new_branch, branch])

    def selected_refname(self):
        return getattr(self.selected_item(), 'refname', None)


class BranchTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, name, refname=None, icon=None):
        QtWidgets.QTreeWidgetItem.__init__(self)
        self.name = name
        self.refname = refname
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


class TreeEntry(object):
    """Tree representation for the branches widget

    The branch widget UI displays the basename.  For intermediate names, e.g.
    "xxx" in the "xxx/abc" and "xxx/def" branches, the 'refname' will be None.
    'children' contains a list of TreeEntry, and is empty when refname is
    defined.

    """

    def __init__(self, basename, refname, children):
        self.basename = basename
        self.refname = refname
        self.children = children


def create_tree_entries(names):
    """Create a nested tree structure with a single root TreeEntry.

    When names == ['xxx/abc', 'xxx/def'] the result will be::

        TreeEntry(
            basename=None,
            refname=None,
            children=[
                TreeEntry(
                    basename='xxx',
                    refname=None,
                    children=[
                        TreeEntry(
                            basename='abc',
                            refname='xxx/abc',
                            children=[]
                        ),
                        TreeEntry(
                            basename='def',
                            refname='xxx/def',
                            children=[]
                        )
                    ]
                )
            ]
        )

    """
    # Phase 1: build a nested dictionary representing the intermediate
    # names in the branches.  e.g. {'xxx': {'abc': {}, 'def': {}}}
    tree_names = create_name_dict(names)

    # Loop over the names again, this time we'll create tree entries
    entries = {}
    root = TreeEntry(None, None, [])
    for item in names:
        cur_names = tree_names
        cur_entries = entries
        tree = root
        children = root.children
        for part in item.split('/'):
            if cur_names[part]:
                # This has children
                try:
                    tree, _ = cur_entries[part]
                except KeyError:
                    # New entry
                    tree = TreeEntry(part, None, [])
                    cur_entries[part] = (tree, {})
                    # Append onto the parent children list only once
                    children.append(tree)
            else:
                # This is the actual branch
                tree = TreeEntry(part, item, [])
                children.append(tree)
                cur_entries[part] = (tree, {})

            # Advance into the nested child list
            children = tree.children
            # Advance into the inner dict
            cur_names = cur_names[part]
            _, cur_entries = cur_entries[part]

    return root


def create_name_dict(names):
    # Phase 1: build a nested dictionary representing the intermediate
    # names in the branches.  e.g. {'xxx': {'abc': {}, 'def': {}}}
    tree_names = {}
    for item in names:
        part_names = tree_names
        for part in item.split('/'):
            # Descend into the inner names dict.
            part_names = part_names.setdefault(part, {})
    return tree_names


def create_toplevel_item(tree, icon=None, ellipsis=None):
    """Create a top-level BranchTreeWidgetItem and its children"""

    item = BranchTreeWidgetItem(tree.basename, icon=ellipsis)
    children = create_tree_items(tree.children, icon=icon, ellipsis=ellipsis)
    if children:
        item.addChildren(children)
    return item


def create_tree_items(entries, icon=None, ellipsis=None):
    """Create children items for a tree item"""
    result = []
    for tree in entries:
        item = BranchTreeWidgetItem(tree.basename, refname=tree.refname, icon=icon)
        children = create_tree_items(tree.children, icon=icon, ellipsis=ellipsis)
        if children:
            item.addChildren(children)
            if ellipsis is not None:
                item.setIcon(0, ellipsis)
        result.append(item)

    return result


def expand_item_parents(item):
    """Expand tree parents from item"""
    parent = item.parent()
    while parent is not None:
        parent.setExpanded(True)
        parent = parent.parent()


def find_by_refname(item, refname):
    """Find child by full name recursive"""
    result = None

    for i in range(item.childCount()):
        child = item.child(i)
        if child.refname and child.refname == refname:
            return child

        result = find_by_refname(child, refname)
        if result is not None:
            return result

    return result


def get_toplevel_item(item):
    """Returns top-most item found by traversing up the specified item"""
    parents = [item]
    parent = item.parent()

    while parent is not None:
        parents.append(parent)
        parent = parent.parent()

    return parents[-1]


class BranchesTreeHelper(object):
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
        # pylint: disable=no-member
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
