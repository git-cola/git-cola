"""Provides widgets related to branches"""
from functools import partial

from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..compat import uchr
from ..git import STDOUT
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
from . import log
from . import text


def defer_func(parent, title, func, *args, **kwargs):
    """Return a QAction bound against a partial func with arguments"""
    return qtutils.add_action(parent, title, partial(func, *args, **kwargs))


def add_branch_to_menu(menu, branch, remote_branch, remote, upstream, func):
    """Add a remote branch to the context menu"""
    branch_remote, _ = gitcmds.parse_remote_branch(remote_branch)
    if branch_remote != remote:
        menu.addSeparator()
    action = defer_func(menu, remote_branch, func, branch, remote_branch)
    if remote_branch == upstream:
        action.setIcon(icons.star())
    menu.addAction(action)
    return branch_remote


class AsyncGitActionTask(qtutils.Task):
    """Run git action asynchronously"""

    def __init__(self, git_helper, action, args, kwarg, update_refs):
        qtutils.Task.__init__(self)
        self.git_helper = git_helper
        self.action = action
        self.args = args
        self.kwarg = kwarg
        self.update_refs = update_refs

    def task(self):
        """Runs action and captures the result"""
        git_action = getattr(self.git_helper, self.action)
        return git_action(*self.args, **self.kwarg)


class BranchesWidget(QtWidgets.QFrame):
    """A widget for displaying and performing operations on branches"""

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

        model.refs_updated.connect(self.refresh, Qt.QueuedConnection)

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


class BranchesTreeWidget(standard.TreeWidget):
    """A tree widget for displaying branches"""

    updated = Signal()

    def __init__(self, context, parent=None):
        standard.TreeWidget.__init__(self, parent)

        self.context = context

        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)
        self.setAlternatingRowColors(False)
        self.setColumnCount(1)
        self.setExpandsOnDoubleClick(False)

        self.current_branch = None
        self.tree_helper = BranchesTreeHelper(self)
        self.git_helper = GitHelper(context)
        self.runtask = qtutils.RunTask(parent=self)

        self._visible = False
        self._needs_refresh = False
        self._tree_states = None

        self.updated.connect(self.refresh, type=Qt.QueuedConnection)
        context.model.updated.connect(self.updated)

        # Expand items when they are clicked
        self.clicked.connect(self._toggle_expanded)

        # Checkout branch when double clicked
        self.doubleClicked.connect(self.checkout_action)

    def refresh(self):
        """Refresh the UI widgets to match the current state"""
        self._needs_refresh = True
        self._refresh()

    def _refresh(self):
        """Refresh the UI to match the updated state"""
        # There is no need to refresh the UI when this widget is inactive.
        if not self._visible:
            return
        model = self.context.model
        self.current_branch = model.currentbranch

        self._tree_states = self._save_tree_state()
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

        if self._tree_states:
            self._load_tree_state(self._tree_states)
            self._tree_states = None

        self._update_branches()

    def showEvent(self, event):
        """Defer updating widgets until the widget is visible"""
        if not self._visible:
            self._visible = True
            if self._needs_refresh:
                self.refresh()
        return super().showEvent(event)

    def _toggle_expanded(self, index):
        """Toggle expanded/collapsed state when items are clicked"""
        item = self.itemFromIndex(index)
        if item and item.childCount():
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

        visualize_action = qtutils.add_action(
            menu, N_('Visualize'), self.visualize_branch_action
        )
        visualize_action.setIcon(icons.visualize())
        menu.addAction(visualize_action)
        menu.addSeparator()

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

        # manage upstream branches for local branches
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

    def _save_tree_state(self):
        """Save the tree state into a dictionary"""
        states = {}
        for item in self.items():
            states.update(self.tree_helper.save_state(item))
        return states

    def _load_tree_state(self, states):
        """Restore expanded items after rebuilding UI widgets"""
        # Disable animations to eliminate redraw flicker.
        animated = self.isAnimated()
        self.setAnimated(False)

        for item in self.items():
            self.tree_helper.load_state(item, states.get(item.name, {}))
        self.tree_helper.set_current_item()

        self.setAnimated(animated)

    def _update_branches(self):
        """Query branch details using a background task"""
        context = self.context
        current_branch = self.current_branch
        top_item = self.topLevelItem(0)
        item = find_by_refname(top_item, current_branch)

        if item is not None:
            expand_item_parents(item)
            item.setIcon(0, icons.star())

            branch_details_task = BranchDetailsTask(
                context, current_branch, self.git_helper
            )
            self.runtask.start(
                branch_details_task, finish=self._update_branches_finished
            )

    def _update_branches_finished(self, task):
        """Update the UI with the branch details once the background task completes"""
        current_branch, tracked_branch, ahead, behind = task.result
        top_item = self.topLevelItem(0)
        item = find_by_refname(top_item, current_branch)
        if current_branch and tracked_branch and item is not None:
            status_str = ''
            if ahead > 0:
                status_str += f'{uchr(0x2191)}{ahead}'

            if behind > 0:
                status_str += f'  {uchr(0x2193)}{behind}'

            if status_str:
                item.setText(0, f'{item.text(0)}\t{status_str}')

    def git_action_async(
        self, action, args, kwarg=None, update_refs=False, remote_messages=False
    ):
        """Execute a git action in a background task"""
        if kwarg is None:
            kwarg = {}
        task = AsyncGitActionTask(self.git_helper, action, args, kwarg, update_refs)
        progress = standard.progress(
            N_('Executing action %s') % action, N_('Updating'), self
        )
        if remote_messages:
            result_handler = log.show_remote_messages(self.context, self)
        else:
            result_handler = None

        self.runtask.start(
            task,
            progress=progress,
            finish=self.git_action_completed,
            result=result_handler,
        )

    def git_action_completed(self, task):
        """Update the with the results of an async git action"""
        status, out, err = task.result
        self.git_helper.show_result(task.action, status, out, err)
        if task.update_refs:
            self.context.model.update_refs()

    def push_action(self):
        """Push the selected branch to its upstream remote"""
        context = self.context
        branch = self.selected_refname()
        remote_branch = gitcmds.tracked_branch(context, branch)
        context.settings.load()
        push_settings = context.settings.get_gui_state_by_name('push')
        remote_messages = push_settings.get('remote_messages', False)
        if remote_branch:
            remote, branch_name = gitcmds.parse_remote_branch(remote_branch)
            if remote and branch_name:
                # we assume that user wants to "Push" the selected local
                # branch to a remote with same name
                self.git_action_async(
                    'push',
                    [remote, branch_name],
                    update_refs=True,
                    remote_messages=remote_messages,
                )

    def rename_action(self):
        """Rename the selected branch"""
        branch = self.selected_refname()
        new_branch, ok = qtutils.prompt(
            N_('Enter New Branch Name'), title=N_('Rename branch'), text=branch
        )
        if ok and new_branch:
            self.git_action_async('rename', [branch, new_branch], update_refs=True)

    def pull_action(self):
        """Pull the selected branch into the current branch"""
        context = self.context
        branch = self.selected_refname()
        if not branch:
            return
        remote_branch = gitcmds.tracked_branch(context, branch)
        context.settings.load()
        pull_settings = context.settings.get_gui_state_by_name('pull')
        remote_messages = pull_settings.get('remote_messages', False)
        if remote_branch:
            remote, branch_name = gitcmds.parse_remote_branch(remote_branch)
            if remote and branch_name:
                self.git_action_async(
                    'pull',
                    [remote, branch_name],
                    update_refs=True,
                    remote_messages=remote_messages,
                )

    def delete_action(self):
        """Delete the selected branch"""
        branch = self.selected_refname()
        if not branch or branch == self.current_branch:
            return

        remote = False
        root = get_toplevel_item(self.selected_item())
        if not root:
            return
        if root.name == N_('Remote'):
            remote = True

        if remote:
            remote, branch = gitcmds.parse_remote_branch(branch)
            if remote and branch:
                cmds.do(cmds.DeleteRemoteBranch, self.context, remote, branch)
        else:
            cmds.do(cmds.DeleteBranch, self.context, branch)

    def merge_action(self):
        """Merge the selected branch into the current branch"""
        branch = self.selected_refname()
        if branch and branch != self.current_branch:
            self.git_action_async('merge', [branch])

    def checkout_action(self):
        """Checkout the selected branch"""
        branch = self.selected_refname()
        if branch and branch != self.current_branch:
            self.git_action_async('checkout', [branch], update_refs=True)

    def checkout_new_branch_action(self):
        """Checkout a new branch"""
        branch = self.selected_refname()
        if branch and branch != self.current_branch:
            _, new_branch = gitcmds.parse_remote_branch(branch)
            self.git_action_async(
                'checkout', ['-b', new_branch, branch], update_refs=True
            )

    def visualize_branch_action(self):
        """Visualize the selected branch"""
        branch = self.selected_refname()
        if branch:
            cmds.do(cmds.VisualizeRevision, self.context, branch)

    def selected_refname(self):
        return getattr(self.selected_item(), 'refname', None)


class BranchDetailsTask(qtutils.Task):
    """Lookup branch details in a background task"""

    def __init__(self, context, current_branch, git_helper):
        super().__init__()
        self.context = context
        self.current_branch = current_branch
        self.git_helper = git_helper

    def task(self):
        """Query git for branch details"""
        tracked_branch = gitcmds.tracked_branch(self.context, self.current_branch)
        ahead = 0
        behind = 0

        if self.current_branch and tracked_branch:
            origin = tracked_branch + '..' + self.current_branch
            our_commits = self.git_helper.log(origin)[STDOUT]
            ahead = our_commits.count('\n')
            if our_commits:
                ahead += 1

            origin = self.current_branch + '..' + tracked_branch
            their_commits = self.git_helper.log(origin)[STDOUT]
            behind = their_commits.count('\n')
            if their_commits:
                behind += 1

        return self.current_branch, tracked_branch, ahead, behind


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


class TreeEntry:
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
    # names in the branches, e.g. {'xxx': {'abc': {}, 'def': {}}}
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
    # names in the branches, e.g. {'xxx': {'abc': {}, 'def': {}}}
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
        if not parent.isExpanded():
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


class BranchesTreeHelper:
    """Save and restore the tree state"""

    def __init__(self, tree):
        self.tree = tree
        self.current_item = None

    def set_current_item(self):
        """Reset the current item"""
        if self.current_item is not None:
            self.tree.setCurrentItem(self.current_item)
        self.current_item = None

    def load_state(self, item, state):
        """Load expanded items from a dict"""
        if not state:
            return
        if state.get('expanded', False) and not item.isExpanded():
            item.setExpanded(True)
        if state.get('selected', False) and not item.isSelected():
            item.setSelected(True)
            self.current_item = item

        children_state = state.get('children', {})
        if not children_state:
            return
        for i in range(item.childCount()):
            child = item.child(i)
            self.load_state(child, children_state.get(child.name, {}))

    def save_state(self, item):
        """Save the selected and expanded item state into a dict"""
        expanded = item.isExpanded()
        selected = item.isSelected()
        children = {}
        entry = {
            'children': children,
            'expanded': expanded,
            'selected': selected,
        }
        result = {item.name: entry}
        for i in range(item.childCount()):
            child = item.child(i)
            children.update(self.save_state(child))

        return result


class GitHelper:
    def __init__(self, context):
        self.context = context
        self.git = context.git

    def log(self, origin):
        return self.git.log(origin, abbrev=7, pretty='format:%h', _readonly=True)

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
        self.text = text.LineEdit(parent=self, clear_button=True)
        self.text.setToolTip(hint)
        self.setFocusProxy(self.text)
        self._filter = None

        self.main_layout = qtutils.hbox(defs.no_margin, defs.spacing, self.text)
        self.setLayout(self.main_layout)

        self.text.textChanged.connect(self.apply_filter)
        self.tree.updated.connect(self.apply_filter, type=Qt.QueuedConnection)

    def apply_filter(self):
        value = get(self.text)
        if value == self._filter:
            return
        self._apply_bold(self._filter, False)
        self._filter = value
        if value:
            self._apply_bold(value, True)

    def _apply_bold(self, value, is_bold):
        match = Qt.MatchContains | Qt.MatchRecursive
        children = self.tree.findItems(value, match)

        for child in children:
            if child.childCount() == 0:
                font = child.font(0)
                font.setBold(is_bold)
                child.setFont(0, font)
