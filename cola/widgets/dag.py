import collections
import itertools
import math
from functools import partial

from qtpy.QtCore import Qt
from qtpy.QtCore import Signal
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

from ..compat import maxsize
from ..i18n import N_
from ..models import dag
from ..models import main
from ..models import prefs
from ..qtutils import get
from .. import core
from .. import cmds
from .. import difftool
from .. import gitcmds
from .. import guicmds
from .. import hotkeys
from .. import icons
from .. import qtcompat
from .. import qtutils
from .. import utils
from . import archive
from . import browse
from . import completion
from . import createbranch
from . import createtag
from . import defs
from . import diff
from . import filelist
from . import standard
from . import finder


def git_dag(context, args=None, existing_view=None, show=True):
    """Return a pre-populated git DAG widget."""
    model = context.model
    branch = model.currentbranch
    # disambiguate between branch names and filenames by using '--'
    branch_doubledash = (branch + ' --') if branch else ''
    params = dag.DAG(branch_doubledash, 1000)
    params.set_arguments(args)

    if existing_view is None:
        view = GitDAG(context, params)
    else:
        view = existing_view
        view.set_params(params)
    if show:
        view.show()
    if params.ref:
        view.display()
    return view


class FocusRedirectProxy:
    """Redirect actions from the main widget to child widgets"""

    def __init__(self, *widgets):
        """Provide proxied widgets; the default widget must be first"""
        self.widgets = widgets
        self.default = widgets[0]

    def __getattr__(self, name):
        return lambda *args, **kwargs: self._forward_action(name, *args, **kwargs)

    def _forward_action(self, name, *args, **kwargs):
        """Forward the captured action to the focused or default widget"""
        widget = QtWidgets.QApplication.focusWidget()
        if widget in self.widgets and hasattr(widget, name):
            func = getattr(widget, name)
        else:
            func = getattr(self.default, name)

        return func(*args, **kwargs)


class ViewerMixin:
    """Implementations must provide selected_items()"""

    def __init__(self):
        self.context = None  # provided by implementation
        self.selected = None
        self.clicked = None
        self.menu_actions = None  # provided by implementation

    def selected_item(self):
        """Return the currently selected item"""
        selected_items = self.selected_items()
        if not selected_items:
            return None
        return selected_items[0]

    def selected_oid(self):
        """Return the currently selected commit object ID"""
        item = self.selected_item()
        if item is None:
            result = None
        else:
            result = item.commit.oid
        return result

    def selected_oids(self):
        """Return the currently selected commit object IDs"""
        return [i.commit for i in self.selected_items()]

    def clicked_oid(self, filtered=True):
        """Return the clicked or selected commit object ID"""
        if self.clicked:
            oid = self.clicked.oid
        else:
            oid = self.selected_oid()
        if filtered and oid and oid in (dag.STAGE, dag.WORKTREE):
            oid = None
        return oid

    def clicked_commit(self, filtered=True):
        """Return the clicked or selected commit object"""
        if self.clicked:
            item = self.clicked
        else:
            item = self.selected_item()
        if item and hasattr(item, 'commit'):
            commit = item.commit
        else:
            commit = item
        if filtered and commit and commit.oid in (dag.STAGE, dag.WORKTREE):
            commit = None
        return commit

    def with_oid(self, func, filtered=True):
        """Run an operation with a commit object ID"""
        oid = self.clicked_oid(filtered=filtered)
        if oid:
            result = func(oid)
        else:
            result = None
        return result

    def with_oid_short(self, func):
        """Run an operation with a short commit object ID"""
        oid = self.clicked_oid()
        if oid:
            abbrev = prefs.abbrev(self.context)
            result = func(oid[:abbrev])
        else:
            result = None
        return result

    def with_selected_oid(self, func):
        """Run an operation with a commit object ID"""
        oid = self.selected_oid()
        if oid:
            result = func(oid)
        else:
            result = None
        return result

    def diff_selected_this(self):
        """Diff the selected commit against the clicked commit"""
        clicked_oid = self.clicked.oid
        selected_oid = self.selected.oid
        self.diff_commits.emit(selected_oid, clicked_oid)

    def diff_this_selected(self):
        """Diff the clicked commit against the selected commit"""
        clicked_oid = self.clicked.oid
        selected_oid = self.selected.oid
        self.diff_commits.emit(clicked_oid, selected_oid)

    def cherry_pick(self):
        """Cherry-pick a commit using git cherry-pick"""
        context = self.context
        self.with_oid(lambda oid: cmds.do(cmds.CherryPick, context, [oid]))

    def revert(self):
        """Revert a commit using git revert"""
        context = self.context
        self.with_oid(lambda oid: cmds.do(cmds.Revert, context, oid))

    def copy_to_clipboard(self):
        """Copy the current commit object ID to the clipboard"""
        self.with_oid(qtutils.set_clipboard)

    def copy_to_clipboard_short(self):
        """Copy the current commit object ID to the clipboard"""
        self.with_oid_short(qtutils.set_clipboard)

    def checkout_branch(self):
        """Checkout the clicked/selected branch"""
        branches = []
        clicked = self.clicked
        selected = self.selected_item()
        if clicked:
            branches.extend(clicked.branches)
        if selected:
            branches.extend(selected.commit.branches)
        if not branches:
            return
        guicmds.checkout_branch(self.context, default=branches[0])

    def create_branch(self):
        """Create a branch at the selected commit"""
        context = self.context
        create_new_branch = partial(createbranch.create_new_branch, context)
        self.with_oid(lambda oid: create_new_branch(revision=oid))

    def create_tag(self):
        """Create a tag at the selected commit"""
        context = self.context
        self.with_oid(lambda oid: createtag.create_tag(context, ref=oid))

    def create_tarball(self):
        """Create a tarball from the selected commit"""
        context = self.context
        self.with_oid(lambda oid: archive.show_save_dialog(context, oid, parent=self))

    def show_diff(self):
        """Show the diff for the selected commit"""
        commit = self.clicked_commit()
        if not commit:
            return
        is_root_commit = not commit.parents
        self.with_oid(
            lambda oid: _diff_expression(self.context, self, oid, is_root_commit),
            filtered=False,
        )

    def show_dir_diff(self):
        """Show a full directory diff for the selected commit"""
        context = self.context
        commit = self.clicked_commit()
        if not commit:
            return
        is_root_commit = not commit.parents
        self.with_oid(
            lambda oid: difftool.difftool_launch(
                context,
                oid=oid,
                is_root_commit=is_root_commit,
                dir_diff=True,
                staged=oid == dag.STAGE,
            ),
            filtered=False,
        )

    def rebase_to_commit(self):
        """Rebase the current branch to the selected commit"""
        context = self.context
        self.with_oid(lambda oid: cmds.do(cmds.Rebase, context, upstream=oid))

    def reset_mixed(self):
        """Reset the repository using git reset --mixed"""
        context = self.context
        self.with_oid(lambda oid: cmds.do(cmds.ResetMixed, context, ref=oid))

    def reset_keep(self):
        """Reset the repository using git reset --keep"""
        context = self.context
        self.with_oid(lambda oid: cmds.do(cmds.ResetKeep, context, ref=oid))

    def reset_merge(self):
        """Reset the repository using git reset --merge"""
        context = self.context
        self.with_oid(lambda oid: cmds.do(cmds.ResetMerge, context, ref=oid))

    def reset_soft(self):
        """Reset the repository using git reset --soft"""
        context = self.context
        self.with_oid(lambda oid: cmds.do(cmds.ResetSoft, context, ref=oid))

    def reset_hard(self):
        """Reset the repository using git reset --hard"""
        context = self.context
        self.with_oid(lambda oid: cmds.do(cmds.ResetHard, context, ref=oid))

    def restore_worktree(self):
        """Reset the worktree contents from the selected commit"""
        context = self.context
        self.with_oid(lambda oid: cmds.do(cmds.RestoreWorktree, context, ref=oid))

    def checkout_detached(self):
        """Checkout a commit using an anonymous detached HEAD"""
        context = self.context
        self.with_oid(lambda oid: cmds.do(cmds.Checkout, context, [oid]))

    def save_blob_dialog(self):
        """Save a file blob from the selected commit"""
        context = self.context
        self.with_oid(
            lambda oid: browse.BrowseBranch.browse(context, oid), filtered=False
        )

    def save_blob_from_parent_dialog(self):
        """Save a file blob from the parent of the selected commit"""
        self.with_oid(
            lambda oid: _save_blob_from_parent(self.context, oid), filtered=False
        )

    def search_line_range(self):
        """Open a dialog to select a range of lines from a file"""
        self.with_oid(lambda oid: self.search_line_range_in_oid.emit(oid))

    def update_menu_actions(self, event):
        """Update menu actions to reflect the selection state"""
        selected_items = self.selected_items()
        selected_item = self.selected_item()
        item = self.itemAt(event.pos())
        if item is None:
            self.clicked = commit = None
        else:
            self.clicked = commit = item.commit

        has_oid = commit and commit.oid not in (dag.WORKTREE, dag.STAGE)
        has_single_selection = len(selected_items) == 1
        has_single_selection_or_clicked = bool(has_single_selection or commit)
        has_selection = bool(selected_items)
        can_diff = bool(
            commit
            and has_single_selection
            and selected_items
            and commit is not selected_items[0].commit
        )
        has_branches = (
            has_single_selection
            and selected_item
            and bool(selected_item.commit.branches)
        ) or (self.clicked and bool(self.clicked.branches))

        if can_diff:
            self.selected = selected_items[0].commit
        else:
            self.selected = None

        self.menu_actions['diff_this_selected'].setEnabled(can_diff)
        self.menu_actions['diff_selected_this'].setEnabled(can_diff)
        self.menu_actions['diff_commit'].setEnabled(has_single_selection_or_clicked)
        self.menu_actions['diff_commit_all'].setEnabled(has_single_selection_or_clicked)
        self.menu_actions['checkout_branch'].setEnabled(bool(has_branches) and has_oid)
        self.menu_actions['checkout_detached'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['cherry_pick'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['copy'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['copy_short'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['create_branch'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['create_patch'].setEnabled(has_selection and has_oid)
        self.menu_actions['create_tag'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['create_tarball'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['rebase_to_commit'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['reset_mixed'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['reset_keep'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['reset_merge'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['reset_soft'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['reset_hard'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['restore_worktree'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['revert'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['save_blob'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )
        self.menu_actions['save_blob_from_parent'].setEnabled(
            has_single_selection_or_clicked
        )
        self.menu_actions['search_line_range'].setEnabled(
            has_single_selection_or_clicked and has_oid
        )

    def context_menu_event(self, event):
        """Build a context menu and execute it"""
        self.update_menu_actions(event)
        menu = qtutils.create_menu(N_('Actions'), self)
        menu.addAction(self.menu_actions['diff_this_selected'])
        menu.addAction(self.menu_actions['diff_selected_this'])
        menu.addAction(self.menu_actions['diff_commit'])
        menu.addAction(self.menu_actions['diff_commit_all'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['search_line_range'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['checkout_branch'])
        menu.addAction(self.menu_actions['create_branch'])
        menu.addAction(self.menu_actions['create_tag'])
        menu.addAction(self.menu_actions['rebase_to_commit'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['cherry_pick'])
        menu.addAction(self.menu_actions['revert'])
        menu.addAction(self.menu_actions['create_patch'])
        menu.addAction(self.menu_actions['create_tarball'])
        menu.addSeparator()
        reset_menu = menu.addMenu(N_('Reset'))
        reset_menu.addAction(self.menu_actions['reset_soft'])
        reset_menu.addAction(self.menu_actions['reset_mixed'])
        reset_menu.addAction(self.menu_actions['restore_worktree'])
        reset_menu.addSeparator()
        reset_menu.addAction(self.menu_actions['reset_keep'])
        reset_menu.addAction(self.menu_actions['reset_merge'])
        reset_menu.addAction(self.menu_actions['reset_hard'])
        menu.addAction(self.menu_actions['checkout_detached'])
        menu.addSeparator()
        menu.addAction(self.menu_actions['save_blob'])
        menu.addAction(self.menu_actions['save_blob_from_parent'])
        menu.addAction(self.menu_actions['copy_short'])
        menu.addAction(self.menu_actions['copy'])
        menu.exec_(self.mapToGlobal(event.pos()))


def _diff_expression(context, widget, oid, is_root_commit):
    """Launch difftool using the specified object ID"""
    if oid == dag.WORKTREE:
        ref = ''
    elif oid == dag.STAGE:
        ref = '--cached'
    elif is_root_commit:
        ref = f'{context.model.empty_tree_oid}..{oid}'
    else:
        ref = f'{oid}~..{oid}'
    return difftool.diff_expression(
        context, widget, ref, hide_expr=False, focus_tree=True
    )


def _save_blob_from_parent(context, oid):
    """Save a browse dialog to grab a file from the parent commit"""
    if oid in (dag.STAGE, dag.WORKTREE):
        ref = 'HEAD'
    else:
        ref = f'{oid}^'
    return browse.BrowseBranch.browse(context, ref)


def set_icon(icon, action):
    """ "Set the icon for an action and return the action"""
    action.setIcon(icon)
    return action


def viewer_actions(widget, proxy):
    """Return common actions across the tree and graph widgets"""
    return {
        'diff_this_selected': set_icon(
            icons.compare(),
            qtutils.add_action(
                widget, N_('Diff this -> selected'), proxy.diff_this_selected
            ),
        ),
        'diff_selected_this': set_icon(
            icons.compare(),
            qtutils.add_action(
                widget, N_('Diff selected -> this'), proxy.diff_selected_this
            ),
        ),
        'create_branch': set_icon(
            icons.branch(),
            qtutils.add_action(widget, N_('Create Branch'), proxy.create_branch),
        ),
        'create_patch': set_icon(
            icons.save(),
            qtutils.add_action(widget, N_('Create Patch'), proxy.create_patch),
        ),
        'create_tag': set_icon(
            icons.tag(),
            qtutils.add_action(widget, N_('Create Tag'), proxy.create_tag),
        ),
        'create_tarball': set_icon(
            icons.file_zip(),
            qtutils.add_action(
                widget, N_('Save As Tarball/Zip...'), proxy.create_tarball
            ),
        ),
        'cherry_pick': set_icon(
            icons.cherry_pick(),
            qtutils.add_action(widget, N_('Cherry Pick'), proxy.cherry_pick),
        ),
        'revert': set_icon(
            icons.undo(), qtutils.add_action(widget, N_('Revert'), proxy.revert)
        ),
        'diff_commit': set_icon(
            icons.diff(),
            qtutils.add_action(
                widget, N_('Launch Diff Tool'), proxy.show_diff, hotkeys.DIFF
            ),
        ),
        'diff_commit_all': set_icon(
            icons.diff(),
            qtutils.add_action(
                widget,
                N_('Launch Directory Diff Tool'),
                proxy.show_dir_diff,
                hotkeys.DIFF_SECONDARY,
            ),
        ),
        'checkout_branch': set_icon(
            icons.branch(),
            qtutils.add_action(widget, N_('Checkout Branch'), proxy.checkout_branch),
        ),
        'checkout_detached': qtutils.add_action(
            widget, N_('Checkout Detached HEAD'), proxy.checkout_detached
        ),
        'rebase_to_commit': set_icon(
            icons.play(),
            qtutils.add_action(
                widget, N_('Rebase to this commit'), proxy.rebase_to_commit
            ),
        ),
        'reset_soft': set_icon(
            icons.style_dialog_reset(),
            qtutils.add_action(widget, N_('Reset Branch (Soft)'), proxy.reset_soft),
        ),
        'reset_mixed': set_icon(
            icons.style_dialog_reset(),
            qtutils.add_action(
                widget, N_('Reset Branch and Stage (Mixed)'), proxy.reset_mixed
            ),
        ),
        'reset_keep': set_icon(
            icons.style_dialog_reset(),
            qtutils.add_action(
                widget,
                N_('Restore Worktree and Reset All (Keep Unstaged Edits)'),
                proxy.reset_keep,
            ),
        ),
        'reset_merge': set_icon(
            icons.style_dialog_reset(),
            qtutils.add_action(
                widget,
                N_('Restore Worktree and Reset All (Merge)'),
                proxy.reset_merge,
            ),
        ),
        'reset_hard': set_icon(
            icons.style_dialog_reset(),
            qtutils.add_action(
                widget,
                N_('Restore Worktree and Reset All (Hard)'),
                proxy.reset_hard,
            ),
        ),
        'restore_worktree': set_icon(
            icons.edit(),
            qtutils.add_action(widget, N_('Restore Worktree'), proxy.restore_worktree),
        ),
        'save_blob': set_icon(
            icons.save(),
            qtutils.add_action(widget, N_('Grab File...'), proxy.save_blob_dialog),
        ),
        'save_blob_from_parent': set_icon(
            icons.save(),
            qtutils.add_action(
                widget,
                N_('Grab File from Parent Commit...'),
                proxy.save_blob_from_parent_dialog,
            ),
        ),
        'search_line_range': set_icon(
            icons.search(),
            qtutils.add_action(
                widget,
                N_('Trace Evolution of Line Range...'),
                proxy.search_line_range,
            ),
        ),
        'copy': set_icon(
            icons.copy(),
            qtutils.add_action(
                widget,
                N_('Copy Commit'),
                proxy.copy_to_clipboard,
                hotkeys.COPY_COMMIT_ID,
            ),
        ),
        'copy_short': set_icon(
            icons.copy(),
            qtutils.add_action(
                widget,
                N_('Copy Commit (Short)'),
                proxy.copy_to_clipboard_short,
                hotkeys.COPY,
            ),
        ),
    }


class GitDagLineEdit(completion.GitLogLineEdit):
    """The text input field for specifying "git log" options"""

    def __init__(self, context):
        super().__init__(context)
        self._action_filter_to_current_author = qtutils.add_action(
            self, N_('Commits authored by me'), self._filter_to_current_author
        )
        self._action_pickaxe_search = qtutils.add_action(
            self, N_('Pickaxe search for changes containing text'), self._pickaxe_search
        )
        self._action_grep_search = qtutils.add_action(
            self,
            N_('Search commit messages'),
            self._grep_search,
        )
        self._action_no_merges = qtutils.add_action(
            self, N_('Ignore merge commits'), self._no_merges
        )
        self._action_filter_lines = qtutils.add_action(
            self, N_('Filter commits by line range'), self._filter_to_line_range
        )

    def contextMenuEvent(self, event):
        """Adds custom actions to the default context menu"""
        event_pos = event.pos()
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        actions = menu.actions()
        first_action = actions[0]
        menu.insertAction(first_action, self._action_pickaxe_search)
        menu.insertAction(first_action, self._action_filter_lines)
        menu.insertAction(first_action, self._action_filter_to_current_author)
        menu.insertAction(first_action, self._action_grep_search)
        menu.insertAction(first_action, self._action_no_merges)
        menu.insertSeparator(first_action)
        menu.exec_(self.mapToGlobal(event_pos))

    def insert(self, text):
        """Insert text at the beginning of the current text"""
        value = self.value()
        if value:
            text = f'{text} {value}'
        self.setText(text)
        self.close_popup()

    def _filter_to_current_author(self):
        """Filter to commits by the current author/user"""
        _, email = self.context.cfg.get_author()
        author_filter = '--author=' + email
        self.insert(author_filter)

    def _filter_to_line_range(self):
        """Filter to commits by line range expressions"""
        range_filter = '-L:funcname:filename'
        self.insert(range_filter)

    def _pickaxe_search(self):
        """Pickaxe search for changes containing text"""
        self.insert('-G"search"')
        start = len('-G"')
        length = len('search')
        self.setSelection(start, length)

    def _grep_search(self):
        """Pickaxe search for changes containing text"""
        self.insert('--grep="search"')
        start = len('--grep="')
        length = len('search')
        self.setSelection(start, length)

    def _no_merges(self):
        """Ignore merge commits"""
        self.insert('--no-merges')


class CommitTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    """Custom TreeWidgetItem used in to build the commit tree widget"""

    def __init__(self, commit, parent=None):
        QtWidgets.QTreeWidgetItem.__init__(self, parent)
        self.commit = commit
        self.setText(0, commit.summary)
        self.setText(1, commit.author)
        self.setText(2, commit.authdate)


class CommitTreeWidget(standard.TreeWidget, ViewerMixin):
    """Display commits using a flat treewidget in "list" mode"""

    commits_selected = Signal(object)
    diff_commits = Signal(object, object)
    search_line_range_in_oid = Signal(object)
    zoom_to_fit = Signal()

    def __init__(self, context, parent):
        standard.TreeWidget.__init__(self, parent)
        ViewerMixin.__init__(self)

        self.setSelectionMode(self.ExtendedSelection)
        self.setHeaderLabels([N_('Summary'), N_('Author'), N_('Date, Time')])
        self.header().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)

        self.context = context
        self.oidmap = {}
        self.menu_actions = None
        self.selecting = False
        self.commits = []
        self._columns_initialized = False
        self.action_up = qtutils.add_action(
            self, N_('Go Up'), self.go_up, hotkeys.MOVE_UP
        )

        self.action_down = qtutils.add_action(
            self, N_('Go Down'), self.go_down, hotkeys.MOVE_DOWN
        )

        self.zoom_to_fit_action = qtutils.add_action(
            self, N_('Zoom to Fit'), self.zoom_to_fit.emit, hotkeys.FIT
        )

        self.itemSelectionChanged.connect(
            self.selection_changed, type=Qt.QueuedConnection
        )

    def export_state(self):
        """Export the widget's state"""
        # The base class method is intentionally overridden because we only
        # care about the details below for this sub-widget.
        state = {}
        state['column_widths'] = self.column_widths()
        return state

    def apply_state(self, state):
        """Apply the exported widget state"""
        try:
            column_widths = state['column_widths']
        except (KeyError, ValueError):
            column_widths = None
        if column_widths:
            # We only care about the first two columns. This allows the final
            # column to stretch and shrink.
            self.set_column_widths(column_widths[:2])
            self._columns_initialized = True
        return True

    # Qt overrides
    def showEvent(self, event):
        """Override QWidget::showEvent() to size columns when we are shown"""
        standard.TreeWidget.showEvent(self, event)
        # Defer resizing columns until the widget has been shown so that width() returns
        # the correct value.
        if not self._columns_initialized:
            self._columns_initialized = True
            width = self.header().width()
            one_half = width // 2
            one_quarter = width // 4
            self.setColumnWidth(0, one_half)
            self.setColumnWidth(1, one_quarter)

    # ViewerMixin
    def go_up(self):
        """Select the item above the current item"""
        self.goto(self.itemAbove)

    def go_down(self):
        """Select the item below the current item"""
        self.goto(self.itemBelow)

    def goto(self, finder_fn):
        """Move the selection using a finder strategy"""
        items = self.selected_items()
        item = items[0] if items else None
        if item is None:
            return
        found = finder_fn(item)
        if found:
            self.select([found.commit.oid])

    def selected_commit_range(self):
        """Return a range of selected commits"""
        selected_items = self.selected_items()
        if not selected_items:
            return None, None
        return selected_items[-1].commit.oid, selected_items[0].commit.oid

    def set_selecting(self, selecting):
        """Record the  "are we selecting?" status"""
        self.selecting = selecting

    def selection_changed(self):
        """Respond to itemSelectionChanged notifications"""
        items = self.selected_items()
        if not items:
            self.set_selecting(True)
            self.commits_selected.emit([])
            self.set_selecting(False)
            return
        self.set_selecting(True)
        self.commits_selected.emit(sort_by_generation([i.commit for i in items]))
        self.set_selecting(False)

    def select_commits(self, commits):
        """Select commits that were selected by the sibling tree/graph widget"""
        if self.selecting:
            return
        with qtutils.BlockSignals(self):
            self.select([commit.oid for commit in commits])

    def select(self, oids):
        """Mark items as selected"""
        self.clearSelection()
        if not oids:
            return
        for oid in oids:
            try:
                item = self.oidmap[oid]
            except KeyError:
                continue
            self.scrollToItem(item)
            item.setSelected(True)

    def clear(self):
        """Clear the tree"""
        QtWidgets.QTreeWidget.clear(self)
        self.oidmap.clear()
        self.commits = []

    def add_commits(self, commits):
        """Add commits to the tree"""
        self.commits.extend(commits)
        items = []
        for c in reversed(commits):
            item = CommitTreeWidgetItem(c)
            items.append(item)
            self.oidmap[c.oid] = item
            for tag in c.tags:
                self.oidmap[tag] = item
        self.insertTopLevelItems(0, items)

    def create_patch(self):
        """Export a patch from the selected items"""
        items = self.selectedItems()
        if not items:
            return
        context = self.context
        oids = [item.commit.oid for item in reversed(items)]
        all_oids = [c.oid for c in self.commits]
        cmds.do(cmds.FormatPatch, context, oids, all_oids)

    # Qt overrides
    def contextMenuEvent(self, event):
        """Create a custom context menu and execute it"""
        self.context_menu_event(event)

    def mousePressEvent(self, event):
        """Intercept the right-click event to retain selection state"""
        item = self.itemAt(event.pos())
        if item is None:
            self.clicked = None
        else:
            self.clicked = item.commit
        if event.button() == Qt.RightButton:
            event.accept()
            return
        QtWidgets.QTreeWidget.mousePressEvent(self, event)


class GitDAG(standard.MainWindow):
    """The git-dag widget."""

    commits_selected = Signal(object)

    def __init__(self, context, params, parent=None):
        super().__init__(parent)

        self.setMinimumSize(420, 420)

        # change when widgets are added/removed
        self.widget_version = 2
        self.context = context
        self.params = params
        self.model = context.model

        self.commits = {}
        self.commit_list = []
        self.selection = []
        self.old_selection = []
        self.old_refs = set()
        self.old_oids = None
        self.old_count = 0
        self.old_display_status = None
        self.force_refresh = False
        self._widgets_initialized = False

        self.thread = None
        self.revtext = GitDagLineEdit(context)
        self.maxresults = standard.SpinBox(digits=None, maxi=9999999, wrap=True)

        self.zoom_out = qtutils.create_action_button(
            tooltip=N_('Zoom Out'), icon=icons.zoom_out()
        )

        self.zoom_in = qtutils.create_action_button(
            tooltip=N_('Zoom In'), icon=icons.zoom_in()
        )

        self.zoom_to_fit = qtutils.create_action_button(
            tooltip=N_('Zoom to Fit'), icon=icons.zoom_fit_best()
        )

        self.treewidget = CommitTreeWidget(context, self)
        self.diffwidget = diff.CommitDiffWidget(context, self, is_commit=True)
        self.filewidget = filelist.FileWidget(context, self)
        self.graphview = GraphView(context, self)

        self.treewidget.commits_selected.connect(
            self.commits_selected, type=Qt.QueuedConnection
        )
        self.graphview.commits_selected.connect(
            self.commits_selected, type=Qt.QueuedConnection
        )

        self.commits_selected.connect(self.select_commits, type=Qt.QueuedConnection)
        self.commits_selected.connect(
            self.diffwidget.commits_selected, type=Qt.QueuedConnection
        )
        self.commits_selected.connect(
            self.filewidget.commits_selected, type=Qt.QueuedConnection
        )
        self.commits_selected.connect(
            self.graphview.select_commits, type=Qt.QueuedConnection
        )
        self.commits_selected.connect(
            self.treewidget.select_commits, type=Qt.QueuedConnection
        )
        self.filewidget.files_selected.connect(
            self.diffwidget.files_selected, type=Qt.QueuedConnection
        )
        self.filewidget.difftool_selected.connect(
            self.difftool_selected, type=Qt.QueuedConnection
        )
        self.filewidget.histories_selected.connect(
            self.histories_selected, type=Qt.QueuedConnection
        )

        self.proxy = FocusRedirectProxy(
            self.treewidget, self.graphview, self.filewidget
        )

        self.treewidget.menu_actions = viewer_actions(self.treewidget, self.proxy)
        self.graphview.menu_actions = viewer_actions(self.graphview, self.proxy)
        self.diffwidget_copy_commit = set_icon(
            icons.copy(),
            qtutils.add_action(
                self.diffwidget.diff,
                N_('Copy Commit'),
                self.treewidget.copy_to_clipboard,
                hotkeys.COPY_COMMIT_ID,
            ),
        )
        self.diffwidget.diff.menu_actions.append(self.diffwidget_copy_commit)

        self.controls_layout = qtutils.hbox(
            defs.no_margin, defs.spacing, self.revtext, self.maxresults
        )
        self.controls_layout.setAlignment(self.maxresults, Qt.AlignTop)

        self.controls_widget = QtWidgets.QWidget()
        self.controls_widget.setLayout(self.controls_layout)

        self.log_dock = qtutils.create_dock(
            'Log', N_('Log'), self, stretch=False, hide_title=True
        )
        self.log_dock.setWidget(self.treewidget)
        log_dock_titlebar = self.log_dock.titleBarWidget()
        log_dock_titlebar.add_corner_widget(self.controls_widget)

        self.file_dock = qtutils.create_dock(
            'Files', N_('Files'), self, hide_title=True
        )
        self.file_dock.setWidget(self.filewidget)

        self.diff_panel = diff.DiffPanel(self.diffwidget, self.diffwidget.diff, self)
        self.diff_options = diff.Options(self.diffwidget)
        self.diffwidget.set_options(self.diff_options)
        self.diff_options.hide_advanced_options()
        self.diff_options.set_diff_type(main.Types.TEXT)

        self.diff_dock = qtutils.create_dock('Diff', N_('Diff'), self, hide_title=True)
        self.diff_dock.setWidget(self.diff_panel)

        diff_titlebar = self.diff_dock.titleBarWidget()
        diff_titlebar.add_title_widget(self.diff_options)

        self.graph_controls_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.zoom_out,
            self.zoom_in,
            self.zoom_to_fit,
            defs.spacing,
        )

        self.graph_controls_widget = QtWidgets.QWidget()
        self.graph_controls_widget.setLayout(self.graph_controls_layout)

        self.graphview_dock = qtutils.create_dock(
            'Graph', N_('Graph'), self, hide_title=True
        )
        self.graphview_dock.setWidget(self.graphview)
        graph_titlebar = self.graphview_dock.titleBarWidget()
        graph_titlebar.add_corner_widget(self.graph_controls_widget)

        self.display_status_action = qtutils.add_action_bool(
            self, N_('Display Worktree Status'), self._enable_worktree_status, False
        )
        self.lock_layout_action = qtutils.add_action_bool(
            self, N_('Lock Layout'), self.set_lock_layout, False
        )

        self.refresh_action = qtutils.add_action(
            self, N_('Refresh'), self.refresh, hotkeys.REFRESH
        )

        # Create the application menu
        self.menubar = QtWidgets.QMenuBar(self)
        self.setMenuBar(self.menubar)

        # View Menu
        self.view_menu = qtutils.add_menu(N_('View'), self.menubar)
        self.view_menu.addAction(self.refresh_action)
        self.view_menu.addAction(self.display_status_action)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.log_dock.toggleViewAction())
        self.view_menu.addAction(self.graphview_dock.toggleViewAction())
        self.view_menu.addAction(self.diff_dock.toggleViewAction())
        self.view_menu.addAction(self.file_dock.toggleViewAction())
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.lock_layout_action)

        left = Qt.LeftDockWidgetArea
        right = Qt.RightDockWidgetArea
        self.addDockWidget(left, self.log_dock)
        self.addDockWidget(left, self.diff_dock)
        self.addDockWidget(right, self.graphview_dock)
        self.addDockWidget(right, self.file_dock)

        # Also re-loads dag.* from the saved state
        self.init_state(context.settings, self.resize_to_desktop)

        qtutils.connect_button(self.zoom_out, self.graphview.zoom_out)
        qtutils.connect_button(self.zoom_in, self.graphview.zoom_in)
        qtutils.connect_button(self.zoom_to_fit, self.graphview.zoom_to_fit)

        self.treewidget.zoom_to_fit.connect(
            self.graphview.zoom_to_fit, type=Qt.QueuedConnection
        )
        self.treewidget.diff_commits.connect(
            self.diff_commits, type=Qt.QueuedConnection
        )
        self.treewidget.search_line_range_in_oid.connect(
            self.search_line_range_in_oid, type=Qt.QueuedConnection
        )
        self.graphview.diff_commits.connect(self.diff_commits, type=Qt.QueuedConnection)
        self.graphview.search_line_range_in_oid.connect(
            self.search_line_range_in_oid, type=Qt.QueuedConnection
        )
        self.filewidget.grab_file.connect(self.grab_file, type=Qt.QueuedConnection)
        self.filewidget.grab_file_from_parent.connect(
            self.grab_file_from_parent, type=Qt.QueuedConnection
        )
        self.filewidget.select_line_range_for_file.connect(
            self.search_line_range_for_file, type=Qt.QueuedConnection
        )
        self.maxresults.editingFinished.connect(self.display, type=Qt.QueuedConnection)
        self.revtext.textChanged.connect(self.text_changed, type=Qt.QueuedConnection)
        self.revtext.activated.connect(self.display, type=Qt.QueuedConnection)
        self.revtext.enter.connect(self.display, type=Qt.QueuedConnection)
        self.revtext.down.connect(self.focus_tree, type=Qt.QueuedConnection)
        # The model is updated in another thread so use
        # signals/slots to bring control back to the main GUI thread
        self.model.updated.connect(self.model_updated, type=Qt.QueuedConnection)

        qtutils.add_action(self, 'FocusInput', self.focus_input, hotkeys.FOCUS_INPUT)
        qtutils.add_action(self, 'FocusTree', self.focus_tree, hotkeys.FOCUS_TREE)
        qtutils.add_action(self, 'FocusDiff', self.focus_diff, hotkeys.FOCUS_DIFF)
        qtutils.add_close_action(self)

        self.set_params(params)

    def set_params(self, params):
        context = self.context
        self.params = params
        # Update fields affected by model
        self.revtext.setText(params.ref)
        self.maxresults.setValue(params.count)
        self.update_window_title()

        self._stop_reader_thread()
        self.thread = ReaderThread(context, params)
        self.thread.begin.connect(self.thread_begin, type=Qt.QueuedConnection)
        self.thread.status.connect(self.thread_status, type=Qt.QueuedConnection)
        self.thread.add.connect(self.add_commits, type=Qt.QueuedConnection)
        self.thread.end.connect(self.thread_end, type=Qt.QueuedConnection)

    def _stop_reader_thread(self):
        """Stop the reader thread if it is currently running"""
        if self.thread is not None and self.thread.isRunning():
            self.thread.requestInterruption()
            QtCore.QThread.currentThread().yieldCurrentThread()
            self.thread.wait(100)

    def _enable_worktree_status(self, enabled):
        """Enable and disable the display of the WORKTREE and STAGE pseudo-commits"""
        self.params.display_status = enabled
        self.display()

    def focus_input(self):
        """Focus the revision input field"""
        self.revtext.setFocus()

    def focus_tree(self):
        """Focus the revision tree list widget"""
        self.treewidget.setFocus()

    def focus_diff(self):
        """Focus the diff widget"""
        self.diffwidget.setFocus()

    def text_changed(self, txt):
        """Respond to changes to the revision input text"""
        self.params.ref = txt
        self.update_window_title()

    def update_window_title(self):
        """Update the window title to reflect the displayed ref"""
        project = self.model.project
        if self.params.ref:
            self.setWindowTitle(
                N_('%(project)s: %(ref)s - DAG')
                % {
                    'project': project,
                    'ref': self.params.ref,
                }
            )
        else:
            self.setWindowTitle(project + N_(' - DAG'))

    def export_state(self):
        """Store persistent GUI state"""
        state = standard.MainWindow.export_state(self)
        state['count'] = self.params.count
        state['display_status'] = self.params.display_status
        state['log'] = self.treewidget.export_state()
        state['word_wrap'] = self.diffwidget.options.enable_word_wrapping.isChecked()
        return state

    def apply_state(self, state):
        """Apply persistent GUI state"""
        result = standard.MainWindow.apply_state(self, state)
        try:
            count = state['count']
            if self.params.overridden('count'):
                count = self.params.count
        except (KeyError, TypeError, ValueError, AttributeError):
            count = self.params.count
            result = False
        self.params.set_count(count)

        display_status = state.get('display_status', True)
        self.params.set_display_status(display_status)
        with qtutils.BlockSignals(self.display_status_action):
            self.display_status_action.setChecked(display_status)

        self.lock_layout_action.setChecked(state.get('lock_layout', False))
        self.diffwidget.set_word_wrapping(state.get('word_wrap', False), update=True)

        try:
            log_state = state['log']
        except (KeyError, ValueError):
            log_state = None
        if log_state:
            self.treewidget.apply_state(log_state)

        return result

    def model_updated(self):
        """Refresh the view when the model is updated"""
        self.display()
        self.update_window_title()

    def refresh(self):
        """Unconditionally refresh the DAG"""
        # self.force_refresh triggers an Unconditional redraw
        self.force_refresh = True
        cmds.do(cmds.Refresh, self.context)

    def display(self):
        """Update the view when the Git refs change"""
        ref = get(self.revtext)
        count = get(self.maxresults)
        context = self.context
        model = self.model
        display_status = get(self.display_status_action)
        # The DAG tries to avoid updating when the object IDs have not
        # changed.  Without doing this the DAG constantly redraws itself
        # whenever inotify sends update events, which hurts usability.
        #
        # To minimize redraws we leverage `git rev-parse`.  The strategy is to
        # use `git rev-parse` on the input line, which converts each argument
        # into object IDs.  From there it's a simple matter of detecting when
        # the object IDs changed.
        #
        # In addition to object IDs, we also need to know when the set of
        # named references (branches, tags) changes so that an update is
        # triggered when new branches and tags are created.
        refs = set(model.local_branches + model.remote_branches + model.tags)
        argv = utils.shell_split(ref or 'HEAD')
        oids = gitcmds.parse_refs(context, argv)
        update = (
            self.force_refresh
            or count != self.old_count
            or oids != self.old_oids
            or refs != self.old_refs
            or display_status != self.old_display_status
        )
        if update:
            self._stop_reader_thread()
            self.params.set_ref(ref)
            self.params.set_count(count)
            self.params.set_display_status(display_status)
            self.thread.start()

        self.old_oids = oids
        self.old_count = count
        self.old_refs = refs
        self.old_display_status = self.params.display_status
        self.force_refresh = False

    def select_commits(self, commits):
        """Commits were selected"""
        self.selection = commits
        enabled = bool(commits)
        self.diffwidget_copy_commit.setEnabled(enabled)

    def clear(self):
        """Clear the view and the list of known commits"""
        self.commits.clear()
        self.commit_list = []
        self.graphview.clear()
        self.treewidget.clear()

    def add_commits(self, commits):
        """Add new commits from the reader thread"""
        self.commit_list.extend(commits)
        # Keep track of commits
        for commit_obj in commits:
            self.commits[commit_obj.oid] = commit_obj
            for tag in commit_obj.tags:
                self.commits[tag] = commit_obj
        # The treewidget is quick to update.  The graphview is slower when updating
        # incrementally so it is updated just once at thread_end() once all commits have
        # been gathered.
        self.treewidget.add_commits(commits)

    def thread_begin(self):
        """The reader thread has begun"""
        if self.selection:
            self.old_selection = self.selection
        self.clear()

    def thread_end(self):
        """The reader thread has completed"""
        self.graphview.add_commits(self.commit_list)
        self.restore_selection()

    def thread_status(self, successful):
        """Indicate an error when the revision input contains an invalid ref"""
        self.revtext.hint.set_error(not successful)

    def restore_selection(self):
        """Restore the selection before the display was refreshed"""
        # The selection can become empty when the widgets are cleared.
        selection = self.selection or self.old_selection
        try:
            commit_obj = self.commit_list[-1]
        except IndexError:
            # No commits, exist, early-out
            return

        new_commits = [self.commits.get(s.oid, None) for s in selection]
        new_commits = [c for c in new_commits if c is not None]
        if new_commits:
            # The old selection exists in the new state
            self.commits_selected.emit(sort_by_generation(new_commits))
        else:
            # The old selection is now empty.  Select the top-most commit
            self.commits_selected.emit([commit_obj])

        self.graphview.set_initial_view()

    def diff_commits(self, left, right):
        """React to diff_commits signals by displaying a difftool interface"""
        paths = self.params.paths()
        if paths:
            difftool.difftool_launch(self.context, left=left, right=right, paths=paths)
        else:
            difftool.diff_commits(self.context, self, left, right, detect_renames=True)

    def search_line_range_in_oid(self, oid):
        """Open a dialog for generating "git log -L" line range expressions"""
        all_paths = self.filewidget.selected_paths()
        if all_paths:
            paths = all_paths[0]
        else:
            paths = None
        widget = finder.new_finder(
            self.context,
            paths=paths,
            ref=oid,
            title=N_('Trace Evolution of Line Range'),
            ok_text=N_('Select Line Range'),
            parent=self,
        )
        widget.search()
        result = widget.exec_()
        if result != QtWidgets.QDialog.Accepted:
            return
        start, span = widget.selected_line_range()
        filename = widget.filename
        if not filename:
            return
        range_expression = f'-L{start},+{span}:{filename}'
        self.revtext.insert(range_expression)
        self.display()

    def histories_selected(self, histories):
        """Respond to file-based history selection from the files widget"""
        argv = [self.model.currentbranch, '--']
        argv.extend(histories)
        rev_text = core.list2cmdline(argv)
        self.revtext.setText(rev_text)
        self.display()

    def difftool_selected(self, files):
        """Launch difftool across a commit range"""
        bottom, top = self.treewidget.selected_commit_range()
        if not top:
            return
        difftool.difftool_launch(
            self.context, left=bottom, left_take_parent=True, right=top, paths=files
        )

    def grab_file(self, filename):
        """Save the selected file from the file list widget"""
        oid = self.treewidget.selected_oid()
        model = browse.BrowseModel(oid, filename=filename)
        browse.save_path(self.context, filename, model)

    def grab_file_from_parent(self, filename):
        """Save the selected file from parent commit in the file list widget"""
        oid = self.treewidget.selected_oid() + '^'
        model = browse.BrowseModel(oid, filename=filename)
        browse.save_path(self.context, filename, model)

    def search_line_range_for_file(self, filename):
        """Generate a line range expression for the specified filename"""
        oid = self.treewidget.selected_oid()
        if not oid or not filename:
            return
        self.search_line_range_in_oid(oid)

    # Qt overrides
    def closeEvent(self, event):
        """Ensure the revision text popup is closed"""
        self.revtext.close_popup()
        self._stop_reader_thread()
        standard.MainWindow.closeEvent(self, event)

    def showEvent(self, event):
        """Resize widgets once their sizes are known"""
        standard.MainWindow.showEvent(self, event)
        if not self._widgets_initialized:
            self._widgets_initialized = True
            self.maxresults.setMinimumHeight(self.revtext.height())


class ReaderThread(QtCore.QThread):
    begin = Signal()
    add = Signal(object)
    end = Signal()
    status = Signal(object)

    def __init__(self, context, params):
        super().__init__()
        self.context = context
        self.params = params

    def run(self):
        """Gather commits and emit them to the main thread"""
        context = self.context
        repo = dag.RepoReader(context, self.params)
        repo.reset()
        self.begin.emit()

        commits = []
        for commit in repo.get():
            if self.isInterruptionRequested():
                repo.reset()
                return
            commits.append(commit)
            if len(commits) >= 2048:
                self.add.emit(commits)
                commits = []

        stage, worktree = repo.get_worktree_commits()
        if stage:
            commits.append(stage)
        if worktree:
            commits.append(worktree)
        if commits:
            self.add.emit(commits)

        self.status.emit(repo.returncode == 0)
        self.end.emit()


class Cache:
    _label_font = None

    @classmethod
    def label_font(cls):
        font = cls._label_font
        if font is None:
            font = cls._label_font = QtWidgets.QApplication.font()
            font.setPointSize(6)
        return font


class Edge(QtWidgets.QGraphicsItem):
    item_type = qtutils.standard_item_type_value(1)

    def __init__(self, source, dest):
        QtWidgets.QGraphicsItem.__init__(self)

        self.setAcceptedMouseButtons(Qt.NoButton)
        self.source = source
        self.dest = dest
        self.commit = source.commit
        self.setZValue(-2)

        self.recompute_bound()
        self.path = None
        self.path_valid = False

        # Choose a new color for new branch edges
        if self.source.x() < self.dest.x():
            color = EdgeColor.cycle()
            line = Qt.SolidLine
        elif self.source.x() != self.dest.x():
            color = EdgeColor.current()
            line = Qt.SolidLine
        else:
            color = EdgeColor.current()
            line = Qt.SolidLine

        self.pen = QtGui.QPen(color, 2.0, line, Qt.SquareCap, Qt.RoundJoin)

    def recompute_bound(self):
        dest_pt = Commit.item_bbox.center()

        self.source_pt = self.mapFromItem(self.source, dest_pt)
        self.dest_pt = self.mapFromItem(self.dest, dest_pt)
        self.line = QtCore.QLineF(self.source_pt, self.dest_pt)

        width = self.dest_pt.x() - self.source_pt.x()
        height = self.dest_pt.y() - self.source_pt.y()
        rect = QtCore.QRectF(self.source_pt, QtCore.QSizeF(width, height))
        self.bound = rect.normalized()

    def commits_were_invalidated(self):
        self.recompute_bound()
        self.prepareGeometryChange()
        # The path should not be recomputed immediately because just small part
        # of DAG is actually shown at same time. It will be recomputed on
        # demand in course of 'paint' method.
        self.path_valid = False
        # Hence, just queue redrawing.
        self.update()

    # Qt overrides
    def type(self):
        return self.item_type

    def boundingRect(self):
        return self.bound

    def recompute_path(self):
        QRectF = QtCore.QRectF
        QPointF = QtCore.QPointF

        arc_rect = 10
        connector_length = 5

        path = QtGui.QPainterPath()

        if self.source.x() == self.dest.x():
            path.moveTo(self.source.x(), self.source.y())
            path.lineTo(self.dest.x(), self.dest.y())
        else:
            # Define points starting from the source.
            point1 = QPointF(self.source.x(), self.source.y())
            point2 = QPointF(point1.x(), point1.y() - connector_length)
            point3 = QPointF(point2.x() + arc_rect, point2.y() - arc_rect)

            # Define points starting from the destination.
            point4 = QPointF(self.dest.x(), self.dest.y())
            point5 = QPointF(point4.x(), point3.y() - arc_rect)
            point6 = QPointF(point5.x() - arc_rect, point5.y() + arc_rect)

            start_angle_arc1 = 180
            span_angle_arc1 = 90
            start_angle_arc2 = 90
            span_angle_arc2 = -90

            # If the destination is at the left of the source, then we need to
            # reverse some values.
            if self.source.x() > self.dest.x():
                point3 = QPointF(point2.x() - arc_rect, point3.y())
                point6 = QPointF(point5.x() + arc_rect, point6.y())

                span_angle_arc1 = 90

            path.moveTo(point1)
            path.lineTo(point2)
            path.arcTo(QRectF(point2, point3), start_angle_arc1, span_angle_arc1)
            path.lineTo(point6)
            path.arcTo(QRectF(point6, point5), start_angle_arc2, span_angle_arc2)
            path.lineTo(point4)

        self.path = path
        self.path_valid = True

    def paint(self, painter, _option, _widget):
        if not self.path_valid:
            self.recompute_path()
        painter.setPen(self.pen)
        painter.drawPath(self.path)


class EdgeColor:
    """An edge color factory"""

    current_color_index = 0
    colors = [
        QtGui.QColor(Qt.red),
        QtGui.QColor(Qt.cyan),
        QtGui.QColor(Qt.magenta),
        QtGui.QColor(Qt.green),
        # Orange; Qt.yellow is too low-contrast
        qtutils.rgba(0xFF, 0x66, 0x00),
    ]

    @classmethod
    def update_colors(cls, theme):
        """Update the colors based on the color theme"""
        if theme.is_dark or theme.is_palette_dark:
            cls.colors.extend([
                QtGui.QColor(Qt.red).lighter(),
                QtGui.QColor(Qt.cyan).lighter(),
                QtGui.QColor(Qt.magenta).lighter(),
                QtGui.QColor(Qt.green).lighter(),
                QtGui.QColor(Qt.yellow).lighter(),
            ])
        else:
            cls.colors.extend([
                QtGui.QColor(Qt.blue),
                QtGui.QColor(Qt.darkRed),
                QtGui.QColor(Qt.darkCyan),
                QtGui.QColor(Qt.darkMagenta),
                QtGui.QColor(Qt.darkGreen),
                QtGui.QColor(Qt.darkYellow),
                QtGui.QColor(Qt.darkBlue),
            ])

    @classmethod
    def cycle(cls):
        cls.current_color_index += 1
        cls.current_color_index %= len(cls.colors)
        color = cls.colors[cls.current_color_index]
        color.setAlpha(128)
        return color

    @classmethod
    def current(cls):
        return cls.colors[cls.current_color_index]

    @classmethod
    def reset(cls):
        cls.current_color_index = 0


class Commit(QtWidgets.QGraphicsItem):
    item_type = qtutils.standard_item_type_value(2)
    commit_radius = 12.0
    merge_radius = 18.0

    item_shape = QtGui.QPainterPath()
    item_shape.addRect(
        commit_radius / -2.0, commit_radius / -2.0, commit_radius, commit_radius
    )
    item_bbox = item_shape.boundingRect()

    inner_rect = QtGui.QPainterPath()
    inner_rect.addRect(
        commit_radius / -2.0 + 2.0,
        commit_radius / -2.0 + 2.0,
        commit_radius - 4.0,
        commit_radius - 4.0,
    )
    inner_rect = inner_rect.boundingRect()

    commit_color = QtGui.QColor(Qt.white)
    outline_color = commit_color.darker()
    merge_color = QtGui.QColor(Qt.lightGray)

    commit_selected_color = QtGui.QColor(Qt.green)
    selected_outline_color = commit_selected_color.darker()

    commit_pen = QtGui.QPen()
    commit_pen.setWidth(1)
    commit_pen.setColor(outline_color)

    def __init__(
        self,
        commit,
        selectable=QtWidgets.QGraphicsItem.ItemIsSelectable,
        cursor=Qt.PointingHandCursor,
        xpos=commit_radius / 2.0 + 1.0,
        cached_commit_color=commit_color,
        cached_merge_color=merge_color,
    ):
        QtWidgets.QGraphicsItem.__init__(self)

        self.commit = commit
        self.selected = False

        self.setZValue(0)
        self.setFlag(selectable)
        self.setCursor(cursor)
        self.setToolTip(commit.oid[:12] + ': ' + commit.summary)

        if commit.tags:
            self.label = label = Label(commit)
            label.setParentItem(self)
            label.setPos(xpos + 1, -self.commit_radius / 2.0)
        else:
            self.label = None

        if len(commit.parents) > 1:
            self.brush = cached_merge_color
        else:
            self.brush = cached_commit_color

        self.pressed = False
        self.dragged = False
        self.edges = {}

    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.ItemSelectedHasChanged:
            # Cache the pen for use in paint()
            if value:
                self.brush = self.commit_selected_color
                color = self.selected_outline_color
            else:
                if len(self.commit.parents) > 1:
                    self.brush = self.merge_color
                else:
                    self.brush = self.commit_color
                color = self.outline_color
            commit_pen = QtGui.QPen()
            commit_pen.setWidth(1)
            commit_pen.setColor(color)
            self.commit_pen = commit_pen

        return QtWidgets.QGraphicsItem.itemChange(self, change, value)

    def type(self):
        return self.item_type

    def boundingRect(self):
        return self.item_bbox

    def shape(self):
        return self.item_shape

    def paint(self, painter, option, _widget):
        # Do not draw outside the exposed rectangle.
        painter.setClipRect(option.exposedRect)

        # Draw ellipse
        painter.setPen(self.commit_pen)
        painter.setBrush(self.brush)
        painter.drawEllipse(self.inner_rect)

    def mousePressEvent(self, event):
        QtWidgets.QGraphicsItem.mousePressEvent(self, event)
        self.pressed = True
        self.selected = self.isSelected()

    def mouseMoveEvent(self, event):
        if self.pressed:
            self.dragged = True
        QtWidgets.QGraphicsItem.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        QtWidgets.QGraphicsItem.mouseReleaseEvent(self, event)
        if not self.dragged and self.selected and event.button() == Qt.LeftButton:
            return
        self.pressed = False
        self.dragged = False


class Label(QtWidgets.QGraphicsItem):
    item_type = qtutils.graphics_item_type_value(3)

    head_color = QtGui.QColor(Qt.green)
    other_color = QtGui.QColor(Qt.white)
    remote_color = QtGui.QColor(Qt.yellow)

    head_pen = QtGui.QPen()
    head_pen.setColor(QtGui.QColor(Qt.black))
    head_pen.setWidth(1)

    text_pen = QtGui.QPen()
    text_pen.setColor(QtGui.QColor(Qt.black))
    text_pen.setWidth(1)

    border = 1
    item_spacing = 8
    text_x_offset = 3
    text_y_offset = 0

    def __init__(self, commit):
        QtWidgets.QGraphicsItem.__init__(self)
        self.setZValue(-1)
        self.commit = commit

    def type(self):
        return self.item_type

    def boundingRect(self, cache=Cache):
        QPainterPath = QtGui.QPainterPath
        QRectF = QtCore.QRectF

        width = 72
        height = 18
        current_width = 0
        spacing = self.item_spacing
        border_x = self.border + self.text_x_offset
        border_y = self.border + self.text_y_offset

        font = cache.label_font()
        item_shape = QPainterPath()

        base_rect = QRectF(0, 0, width, height)
        base_rect = base_rect.adjusted(-border_x, -border_y, border_x, border_y)
        item_shape.addRect(base_rect)

        for tag in self.commit.tags:
            text_shape = QPainterPath()
            text_shape.addText(current_width, 0, font, tag)
            text_rect = text_shape.boundingRect()
            box_rect = text_rect.adjusted(-border_x, -border_y, border_x, border_y)
            item_shape.addRect(box_rect)
            current_width = item_shape.boundingRect().width() + spacing

        return item_shape.boundingRect()

    def paint(self, painter, _option, _widget, cache=Cache):
        # Draw tags and branches
        font = cache.label_font()
        painter.setFont(font)

        current_width = 3
        border = self.border
        x_offset = self.text_x_offset
        y_offset = self.text_y_offset
        spacing = self.item_spacing
        QRectF = QtCore.QRectF

        HEAD = 'HEAD'
        remotes_prefix = 'remotes/'
        tags_prefix = 'tags/'
        heads_prefix = 'heads/'
        remotes_len = len(remotes_prefix)
        tags_len = len(tags_prefix)
        heads_len = len(heads_prefix)

        for tag in self.commit.tags:
            if tag == HEAD:
                painter.setPen(self.text_pen)
                painter.setBrush(self.remote_color)
            elif tag.startswith(remotes_prefix):
                tag = tag[remotes_len:]
                painter.setPen(self.text_pen)
                painter.setBrush(self.other_color)
            elif tag.startswith(tags_prefix):
                tag = tag[tags_len:]
                painter.setPen(self.text_pen)
                painter.setBrush(self.remote_color)
            elif tag.startswith(heads_prefix):
                tag = tag[heads_len:]
                painter.setPen(self.head_pen)
                painter.setBrush(self.head_color)
            else:
                painter.setPen(self.text_pen)
                painter.setBrush(self.other_color)

            text_rect = painter.boundingRect(
                QRectF(current_width, 0, 0, 0), Qt.TextSingleLine, tag
            )
            box_rect = text_rect.adjusted(-x_offset, -y_offset, x_offset, y_offset)

            painter.drawRoundedRect(box_rect, border, border)
            painter.drawText(text_rect, Qt.TextSingleLine, tag)
            current_width += text_rect.width() + spacing


class GraphView(QtWidgets.QGraphicsView, ViewerMixin):
    commits_selected = Signal(object)
    diff_commits = Signal(object, object)
    search_line_range_in_oid = Signal(object)

    x_adjust = int(Commit.commit_radius * 4 / 3)
    y_adjust = int(Commit.commit_radius * 4 / 3)

    x_off = -18
    y_off = -20

    def __init__(self, context, parent):
        QtWidgets.QGraphicsView.__init__(self, parent)
        ViewerMixin.__init__(self)
        EdgeColor.update_colors(context.app.theme)

        theme = context.app.theme
        highlight = theme.selection_color()
        Commit.commit_selected_color = highlight
        Commit.selected_outline_color = highlight.darker()

        self.context = context
        self.columns = {}
        self.menu_actions = None
        self.commits = []
        self.items = {}
        self.mouse_start = [0, 0]
        self.saved_matrix = self.transform()
        self.max_column = 0
        self.min_column = 0
        self.frontier = {}
        self.tagged_cells = set()

        self.x_start = 24
        self.x_min = 24
        self.x_offsets = collections.defaultdict(lambda: self.x_min)

        self.is_panning = False
        self.pressed = False
        self.selecting = False
        self.last_mouse = [0, 0]
        self.zoom = 2
        self.setDragMode(self.RubberBandDrag)

        scene = QtWidgets.QGraphicsScene(self)
        scene.setItemIndexMethod(QtWidgets.QGraphicsScene.BspTreeIndex)
        scene.selectionChanged.connect(self.selection_changed, type=Qt.QueuedConnection)
        self.setScene(scene)

        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setViewportUpdateMode(self.SmartViewportUpdate)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheBackground)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)

        background_color = qtutils.css_color(context.app.theme.background_color_rgb())
        self.setBackgroundBrush(background_color)

        qtutils.add_action(
            self,
            N_('Zoom In'),
            self.zoom_in,
            hotkeys.ZOOM_IN,
            hotkeys.ZOOM_IN_SECONDARY,
        )

        qtutils.add_action(self, N_('Zoom Out'), self.zoom_out, hotkeys.ZOOM_OUT)

        qtutils.add_action(self, N_('Zoom to Fit'), self.zoom_to_fit, hotkeys.FIT)

        qtutils.add_action(
            self, N_('Select Parent'), self._select_parent, hotkeys.MOVE_DOWN_TERTIARY
        )

        qtutils.add_action(
            self,
            N_('Select Oldest Parent'),
            self._select_oldest_parent,
            hotkeys.MOVE_DOWN,
        )

        qtutils.add_action(
            self, N_('Select Child'), self._select_child, hotkeys.MOVE_UP_TERTIARY
        )

        qtutils.add_action(
            self, N_('Select Newest Child'), self._select_newest_child, hotkeys.MOVE_UP
        )

    def clear(self):
        EdgeColor.reset()
        self.scene().clear()
        self.scene().invalidate()
        self.items.clear()
        self.x_offsets.clear()
        self.x_min = 24
        self.commits = []

    # ViewerMixin interface
    def selected_items(self):
        """Return the currently selected items"""
        return self.scene().selectedItems()

    def zoom_in(self):
        self.scale_view(1.5)

    def zoom_out(self):
        self.scale_view(1.0 / 1.5)

    def selection_changed(self):
        # Broadcast selection to other widgets
        selected_items = self.scene().selectedItems()
        commits = sort_by_generation([item.commit for item in selected_items])
        self.set_selecting(True)
        self.commits_selected.emit(commits)
        self.set_selecting(False)

    def select_commits(self, commits):
        if self.selecting:
            return
        with qtutils.BlockSignals(self.scene()):
            self.select([commit.oid for commit in commits])

    def select(self, oids):
        """Select the item for the oids"""
        self.scene().clearSelection()
        for oid in oids:
            try:
                item = self.items[oid]
            except KeyError:
                continue
            item.setSelected(True)
            item_rect = item.sceneTransform().mapRect(item.boundingRect())
            self.ensureVisible(item_rect)

    def _get_item_by_generation(self, commits, criteria_func):
        """Return the item for the commit matching criteria"""
        if not commits:
            return None
        generation = None
        for commit in commits:
            if generation is None or criteria_func(generation, commit.generation):
                oid = commit.oid
                generation = commit.generation
        try:
            return self.items[oid]
        except KeyError:
            return None

    def _oldest_item(self, commits):
        """Return the item for the commit with the oldest generation number"""
        return self._get_item_by_generation(commits, lambda a, b: a > b)

    def _newest_item(self, commits):
        """Return the item for the commit with the newest generation number"""
        return self._get_item_by_generation(commits, lambda a, b: a < b)

    def create_patch(self):
        items = self.selected_items()
        if not items:
            return
        context = self.context
        selected_commits = sort_by_generation([n.commit for n in items])
        oids = [c.oid for c in selected_commits]
        all_oids = [c.oid for c in sort_by_generation(self.commits)]
        cmds.do(cmds.FormatPatch, context, oids, all_oids)

    def _select_parent(self):
        """Select the parent with the newest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        parent_item = self._newest_item(selected_item.commit.parents)
        if parent_item is None:
            return
        selected_item.setSelected(False)
        parent_item.setSelected(True)
        self.ensureVisible(parent_item.mapRectToScene(parent_item.boundingRect()))

    def _select_oldest_parent(self):
        """Select the parent with the oldest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        parent_item = self._oldest_item(selected_item.commit.parents)
        if parent_item is None:
            return
        selected_item.setSelected(False)
        parent_item.setSelected(True)
        scene_rect = parent_item.mapRectToScene(parent_item.boundingRect())
        self.ensureVisible(scene_rect)

    def _select_child(self):
        """Select the child with the oldest generation number"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        child_item = self._oldest_item(selected_item.commit.children)
        if child_item is None:
            return
        selected_item.setSelected(False)
        child_item.setSelected(True)
        scene_rect = child_item.mapRectToScene(child_item.boundingRect())
        self.ensureVisible(scene_rect)

    def _select_newest_child(self):
        """Select the Nth child with the newest generation number (N > 1)"""
        selected_item = self.selected_item()
        if selected_item is None:
            return
        if len(selected_item.commit.children) > 1:
            children = selected_item.commit.children[1:]
        else:
            children = selected_item.commit.children
        child_item = self._newest_item(children)
        if child_item is None:
            return
        selected_item.setSelected(False)
        child_item.setSelected(True)
        scene_rect = child_item.mapRectToScene(child_item.boundingRect())
        self.ensureVisible(scene_rect)

    def set_initial_view(self):
        items = []
        selected = self.selected_items()
        if selected:
            items.extend(selected)

        if not selected and self.commits:
            commit = self.commits[-1]
            items.append(self.items[commit.oid])

        bounds = self.scene().itemsBoundingRect()
        bounds.adjust(-64, 0, 0, 0)
        self.setSceneRect(bounds)
        self.fit_view_to_items(items)

    def zoom_to_fit(self):
        """Fit selected items into the viewport"""
        items = self.selected_items()
        self.fit_view_to_items(items)

    def fit_view_to_items(self, items):
        if not items:
            rect = self.scene().itemsBoundingRect()
        else:
            x_min = y_min = maxsize
            x_max = y_max = -maxsize

            for item in items:
                pos = item.pos()
                x_val = pos.x()
                y_val = pos.y()
                x_min = min(x_min, x_val)
                x_max = max(x_max, x_val)
                y_min = min(y_min, y_val)
                y_max = max(y_max, y_val)

            rect = QtCore.QRectF(x_min, y_min, abs(x_max - x_min), abs(y_max - y_min))

        x_adjust = abs(GraphView.x_adjust)
        y_adjust = abs(GraphView.y_adjust)

        count = max(2.0, 10.0 - len(items) / 2.0)
        y_offset = int(y_adjust * count)
        x_offset = int(x_adjust * count)
        rect.setX(rect.x() - x_offset // 2)
        rect.setY(rect.y() - y_adjust // 2)
        rect.setHeight(rect.height() + y_offset)
        rect.setWidth(rect.width() + x_offset)

        self.fitInView(rect, Qt.KeepAspectRatio)
        self.scene().invalidate()

    def handle_event(self, event_handler, event, update=True):
        event_handler(self, event)
        if update:
            self.update()

    def set_selecting(self, selecting):
        self.selecting = selecting

    def pan(self, event):
        pos = event.pos()
        x_offset = pos.x() - self.mouse_start[0]
        y_offset = pos.y() - self.mouse_start[1]

        if x_offset == 0 and y_offset == 0:
            return

        rect = QtCore.QRect(0, 0, abs(x_offset), abs(y_offset))
        delta = self.mapToScene(rect).boundingRect()

        x_translate = delta.width()
        if x_offset < 0.0:
            x_translate = -x_translate

        y_translate = delta.height()
        if y_offset < 0.0:
            y_translate = -y_translate

        matrix = self.transform()
        matrix.reset()
        matrix *= self.saved_matrix
        matrix.translate(x_translate, y_translate)

        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setTransform(matrix)

    def wheel_zoom(self, event):
        """Handle mouse wheel zooming."""
        delta = qtcompat.wheel_delta(event)
        zoom = math.pow(2.0, delta / 512.0)
        factor = (
            self.transform()
            .scale(zoom, zoom)
            .mapRect(QtCore.QRectF(0.0, 0.0, 1.0, 1.0))
            .width()
        )
        if factor < 0.014 or factor > 42.0:
            return
        self.setTransformationAnchor(QtWidgets.QGraphicsView.AnchorUnderMouse)
        self.zoom = zoom
        self.scale(zoom, zoom)

    def wheel_pan(self, event):
        """Handle mouse wheel panning."""
        unit = QtCore.QRectF(0.0, 0.0, 1.0, 1.0)
        factor = 1.0 / self.transform().mapRect(unit).width()
        tx, ty = qtcompat.wheel_translation(event)

        matrix = self.transform().translate(tx * factor, ty * factor)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setTransform(matrix)

    def scale_view(self, scale):
        factor = (
            self.transform()
            .scale(scale, scale)
            .mapRect(QtCore.QRectF(0, 0, 1, 1))
            .width()
        )
        if factor < 0.07 or factor > 100.0:
            return
        self.zoom = scale

        adjust_scrollbars = False
        scrollbar = self.verticalScrollBar()
        scrollbar_offset = 1.0
        if scrollbar:
            value = get(scrollbar)
            minimum = scrollbar.minimum()
            maximum = scrollbar.maximum()
            scrollbar_range = maximum - minimum
            distance = value - minimum
            nonzero_range = scrollbar_range > 0.1
            if nonzero_range:
                scrollbar_offset = distance / scrollbar_range
                adjust_scrollbars = True

        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.scale(scale, scale)

        scrollbar = self.verticalScrollBar()
        if scrollbar and adjust_scrollbars:
            minimum = scrollbar.minimum()
            maximum = scrollbar.maximum()
            scrollbar_range = maximum - minimum
            value = minimum + int(float(scrollbar_range) * scrollbar_offset)
            scrollbar.setValue(value)

    def add_commits(self, commits):
        """Traverse commits and add them to the view."""
        self.commits.extend(commits)
        scene = self.scene()
        for commit in commits:
            item = Commit(commit)
            self.items[commit.oid] = item
            for ref in commit.tags:
                self.items[ref] = item
            scene.addItem(item)

        self.layout_commits()
        self.link(commits)

    def link(self, commits):
        """Create edges linking commits with their parents"""
        scene = self.scene()
        for commit in commits:
            try:
                commit_item = self.items[commit.oid]
            except KeyError:
                continue  # The history is truncated.
            for parent in reversed(commit.parents):
                try:
                    parent_item = self.items[parent.oid]
                except KeyError:
                    continue  # The history is truncated.
                try:
                    edge = parent_item.edges[commit.oid]
                except KeyError:
                    edge = Edge(parent_item, commit_item)
                else:
                    continue
                parent_item.edges[commit.oid] = edge
                commit_item.edges[parent.oid] = edge
                scene.addItem(edge)

    def layout_commits(self):
        positions = self.position_nodes()

        # Each edge is accounted in two commits. Hence, accumulate invalid
        # edges to prevent double edge invalidation.
        invalid_edges = set()

        for oid, (x_val, y_val) in positions.items():
            item = self.items[oid]

            pos = item.pos()
            if pos != (x_val, y_val):
                item.setPos(x_val, y_val)

                for edge in item.edges.values():
                    invalid_edges.add(edge)

        for edge in invalid_edges:
            edge.commits_were_invalidated()

    # Commit node layout technique
    #
    # Nodes are aligned by a mesh. Columns and rows are distributed using
    # algorithms described below.
    #
    # Row assignment algorithm
    #
    # The algorithm aims consequent.
    #     1. A commit should be above all its parents.
    #     2. No commit should be at right side of a commit with a tag in same row.
    # This prevents overlapping of tag labels with commits and other labels.
    #     3. Commit density should be maximized.
    #
    #     The algorithm requires that all parents of a commit were assigned column.
    # Nodes must be traversed in generation ascend order. This guarantees that all
    # parents of a commit were assigned row. So, the algorithm may operate in
    # course of column assignment algorithm.
    #
    #    Row assignment uses frontier. A frontier is a dictionary that contains
    # minimum available row index for each column. It propagates during the
    # algorithm. Set of cells with tags is also maintained to meet second aim.
    #
    #    Initialization is performed by reset_rows method. Each new column should
    # be declared using declare_column method. Getting row for a cell is
    # implemented in alloc_cell method. Frontier must be propagated for any child
    # of fork commit which occupies different column. This meets first aim.
    #
    # Column assignment algorithm
    #
    #     The algorithm traverses nodes in generation ascend order. This guarantees
    # that a node will be visited after all its parents.
    #
    #     The set of occupied columns are maintained during work. Initially it is
    # empty and no node occupied a column. Empty columns are allocated on demand.
    # Free index for column being allocated is searched in following way.
    #     1. Start from desired column and look towards graph center (0 column).
    #     2. Start from center and look in both directions simultaneously.
    # Desired column is defaulted to 0. Fork node should set desired column for
    # children equal to its one. This prevents branch from jumping too far from
    # its fork.
    #
    #     Initialization is performed by reset_columns method. Column allocation is
    # implemented in alloc_column method. Initialization and main loop are in
    # recompute_grid method. The method also embeds row assignment algorithm by
    # implementation.
    #
    # Actions for each node are follow.
    #     1. If the node was not assigned a column then it is assigned empty one.
    #     2. Allocate row.
    #     3. Allocate columns for children.
    #     If a child have a column assigned then it should no be overridden. One of
    # children is assigned same column as the node. If the node is a fork then the
    # child is chosen in generation descent order. This is a heuristic and it only
    # affects resulting appearance of the graph. Other children are assigned empty
    # columns in same order. It is the heuristic too.
    #     4. If no child occupies column of the node then leave it.
    #     It is possible in consequent situations.
    #     4.1 The node is a leaf.
    #     4.2 The node is a fork and all its children are already assigned side
    # column. It is possible if all the children are merges.
    #     4.3 Single node child is a merge that is already assigned a column.
    #     5. Propagate frontier with respect to this node.
    #     Each frontier entry corresponding to column occupied by any node's child
    # must be gather than node row index. This meets first aim of the row
    # assignment algorithm.
    #     Note that frontier of child that occupies same row was propagated during
    # step 2. Hence, it must be propagated for children on side columns.

    def reset_columns(self):
        # Some children of displayed commits might not be accounted in
        # 'commits' list. It is common case during loading of big graph.
        # But, they are assigned a column that must be reset. Hence, use
        # depth-first traversal to reset all columns assigned.
        for node in self.commits:
            if node.column is None:
                continue
            stack = [node]
            while stack:
                node = stack.pop()
                node.column = None
                for child in node.children:
                    if child.column is not None:
                        stack.append(child)

        self.columns = {}
        self.max_column = 0
        self.min_column = 0

    def reset_rows(self):
        self.frontier = {}
        self.tagged_cells = set()

    def declare_column(self, column):
        if self.frontier:
            # Align new column frontier by frontier of nearest column. If all
            # columns were left then select maximum frontier value.
            if not self.columns:
                self.frontier[column] = max(self.frontier.values())
                return
            # This is heuristic that mostly affects roots. Note that the
            # frontier values for fork children will be overridden in course of
            # propagate_frontier.
            for offset in itertools.count(1):
                for value in (column + offset, column - offset):
                    if value not in self.columns:
                        # Column is not occupied.
                        continue
                    try:
                        frontier = self.frontier[value]
                    except KeyError:
                        # Column 'c' was never allocated.
                        continue

                    frontier -= 1
                    # The frontier of the column may be higher because of
                    # tag overlapping prevention performed for previous head.
                    try:
                        if self.frontier[column] >= frontier:
                            break
                    except KeyError:
                        pass

                    self.frontier[column] = frontier
                    break
                else:
                    continue
                break
        else:
            # First commit must be assigned 0 row.
            self.frontier[column] = 0

    def alloc_column(self, column=0):
        columns = self.columns
        # First, look for free column by moving from desired column to graph
        # center (column 0).
        for c in range(column, 0, -1 if column > 0 else 1):
            if c not in columns:
                if c > self.max_column:
                    self.max_column = c
                elif c < self.min_column:
                    self.min_column = c
                break
        else:
            # If no free column was found between graph center and desired
            # column then look for free one by moving from center along both
            # directions simultaneously.
            for c in itertools.count(0):
                if c not in columns:
                    if c > self.max_column:
                        self.max_column = c
                    break
                c = -c
                if c not in columns:
                    if c < self.min_column:
                        self.min_column = c
                    break
        self.declare_column(c)
        columns[c] = 1
        return c

    def alloc_cell(self, column, tags):
        # Get empty cell from frontier.
        cell_row = self.frontier[column]

        if tags:
            # Prevent overlapping of tag with cells already allocated a row.
            if self.x_off > 0:
                can_overlap = list(range(column + 1, self.max_column + 1))
            else:
                can_overlap = list(range(column - 1, self.min_column - 1, -1))
            for value in can_overlap:
                frontier = self.frontier[value]
                if frontier > cell_row:
                    cell_row = frontier

        # Avoid overlapping with tags of commits at cell_row.
        if self.x_off > 0:
            can_overlap = range(self.min_column, column)
        else:
            can_overlap = range(self.max_column, column, -1)
        for cell_row in itertools.count(cell_row):
            for value in can_overlap:
                if (value, cell_row) in self.tagged_cells:
                    # Overlapping. Try next row.
                    break
            else:
                # No overlapping was found.
                break
            # Note that all checks should be made for new cell_row value.

        if tags:
            self.tagged_cells.add((column, cell_row))

        # Propagate frontier.
        self.frontier[column] = cell_row + 1
        return cell_row

    def propagate_frontier(self, column, value):
        current = self.frontier[column]
        if current < value:
            self.frontier[column] = value

    def leave_column(self, column):
        count = self.columns[column]
        if count == 1:
            del self.columns[column]
        else:
            self.columns[column] = count - 1

    def recompute_grid(self):
        self.reset_columns()
        self.reset_rows()

        for node in sort_by_generation(list(self.commits)):
            if node.column is None:
                # Node is either root or its parent is not in items. This
                # happens when tree loading is in progress. Allocate new
                # columns for such nodes.
                node.column = self.alloc_column()

            node.row = self.alloc_cell(node.column, node.tags)

            # Allocate columns for children which are still without one. Also
            # propagate frontier for children.
            if node.is_fork():
                sorted_children = sorted(
                    node.children, key=lambda c: c.generation, reverse=True
                )
                citer = iter(sorted_children)
                for child in citer:
                    if child.column is None:
                        # Top most child occupies column of parent.
                        child.column = node.column
                        # Note that frontier is propagated in course of
                        # alloc_cell.
                        break
                    self.propagate_frontier(child.column, node.row + 1)
                else:
                    # No child occupies same column.
                    self.leave_column(node.column)
                    # Note that the loop below will pass no iteration.

                # Rest children are allocated new column.
                for child in citer:
                    if child.column is None:
                        child.column = self.alloc_column(node.column)
                    self.propagate_frontier(child.column, node.row + 1)
            elif node.children:
                child = node.children[0]
                if child.column is None:
                    child.column = node.column
                    # Note that frontier is propagated in course of alloc_cell.
                elif child.column != node.column:
                    # Child node have other parents and occupies column of one
                    # of them.
                    self.leave_column(node.column)
                    # But frontier must be propagated with respect to this
                    # parent.
                    self.propagate_frontier(child.column, node.row + 1)
            else:
                # This is a leaf node.
                self.leave_column(node.column)

    def position_nodes(self):
        self.recompute_grid()

        x_start = self.x_start
        x_min = self.x_min
        x_off = self.x_off
        y_off = self.y_off

        positions = {}

        for node in self.commits:
            x_val = x_start + node.column * x_off
            y_val = y_off + node.row * y_off

            positions[node.oid] = (x_val, y_val)
            x_min = min(x_min, x_val)

        self.x_min = x_min

        return positions

    # Qt overrides
    def contextMenuEvent(self, event):
        self.context_menu_event(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MidButton:
            pos = event.pos()
            self.mouse_start = [pos.x(), pos.y()]
            self.saved_matrix = self.transform()
            self.is_panning = True
            return
        if event.button() == Qt.RightButton:
            event.ignore()
            return
        if event.button() == Qt.LeftButton:
            self.pressed = True
        self.handle_event(QtWidgets.QGraphicsView.mousePressEvent, event)

    def mouseMoveEvent(self, event):
        if self.is_panning:
            self.pan(event)
            return
        pos = self.mapToScene(event.pos())
        self.last_mouse[0] = pos.x()
        self.last_mouse[1] = pos.y()
        self.handle_event(QtWidgets.QGraphicsView.mouseMoveEvent, event, update=False)

    def mouseReleaseEvent(self, event):
        self.pressed = False
        if event.button() == Qt.MidButton:
            self.is_panning = False
            return
        self.handle_event(QtWidgets.QGraphicsView.mouseReleaseEvent, event)
        self.viewport().repaint()

    def wheelEvent(self, event):
        """Handle Qt mouse wheel events."""
        if event.modifiers() & Qt.ControlModifier:
            self.wheel_zoom(event)
        else:
            self.wheel_pan(event)

    def fitInView(self, rect, flags=Qt.IgnoreAspectRatio):
        """Override fitInView to remove unwanted margins

        https://bugreports.qt.io/browse/QTBUG-42331 - based on QT sources

        """
        if self.scene() is None or rect.isNull():
            return
        unity = self.transform().mapRect(QtCore.QRectF(0, 0, 1, 1))
        self.scale(1.0 / unity.width(), 1.0 / unity.height())
        view_rect = self.viewport().rect()
        scene_rect = self.transform().mapRect(rect)
        xratio = view_rect.width() / scene_rect.width()
        yratio = view_rect.height() / scene_rect.height()
        if flags == Qt.KeepAspectRatio:
            xratio = yratio = min(xratio, yratio)
        elif flags == Qt.KeepAspectRatioByExpanding:
            xratio = yratio = max(xratio, yratio)
        self.scale(xratio, yratio)
        self.centerOn(rect.center())


def sort_by_generation(commits):
    """Sort commits by their generation. Ensures consistent diffs and patch exports"""
    if len(commits) <= 1:
        return commits
    commits.sort(key=lambda x: x.generation)
    return commits


# Glossary
# ========
# oid -- Git objects IDs (i.e. SHA-1 / SHA-256 IDs)
# ref -- Git references that resolve to a commit-ish (HEAD, branches, tags)
