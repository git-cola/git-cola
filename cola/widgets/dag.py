from __future__ import annotations
import collections
import enum
import itertools
import math
from dataclasses import dataclass
from functools import partial

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import cmds
from .. import core
from .. import difftool
from .. import guicmds
from .. import hotkeys
from .. import icons
from .. import qtcompat
from .. import qtutils
from ..compat import maxsize
from ..i18n import N_
from ..interaction import Interaction
from ..models import dag
from ..models import graph
from ..models import main
from ..models import prefs
from ..models.graph import GraphRowColor
from ..qtutils import get
from . import archive
from . import browse
from . import completion
from . import createbranch
from . import createtag
from . import defs
from . import diff
from . import diff_intraline
from . import filelist
from . import finder
from . import standard


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


def _confirm_detached_checkout(context, commit):
    """Warn before a checkout that would leave HEAD detached"""
    oid = commit.oid[: prefs.abbrev(context)]
    return Interaction.confirm(
        N_('Checkout Detached HEAD?'),
        N_('Commit %s is not the tip of a branch.') % oid,
        N_(
            'Checking out this commit detaches HEAD. New commits will not belong '
            'to any branch and can be lost when you switch away.\n'
            'Use "Create Branch" if you want to keep working here.'
        ),
        N_('Checkout Detached HEAD'),
        default=False,
        icon=icons.branch(),
    )


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

    def checkout_commit(self, commit):
        """Go to the branch at `commit`, or to the commit itself after a warning

        A commit that is the tip of exactly one local branch is what the user
        means by "take me to that branch", so it is checked out by name. Several
        branches at the same commit are ambiguous and go through the existing
        Checkout Branch dialog. Anything else would detach HEAD, which is a state
        the user has to opt into.
        """
        if commit is None or commit.oid in (dag.STAGE, dag.WORKTREE):
            return
        context = self.context
        branches = list(commit.branches)
        if context.model.currentbranch in branches:
            return
        if len(branches) == 1:
            cmds.do(cmds.CheckoutBranch, context, branches[0])
            return
        if branches:
            guicmds.checkout_branch(context, default=branches[0])
            return
        if 'HEAD' in commit.tags:
            return
        if not _confirm_detached_checkout(context, commit):
            return
        cmds.do(cmds.Checkout, context, [commit.oid])

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

        has_oid = bool(commit and commit.oid not in (dag.WORKTREE, dag.STAGE))
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


class ColumnInitState:
    """State machine states for initialization of column widths"""

    NONE = 0
    SHOW_EVENT = 1
    GRAPH = 2
    COMPLETE = 3


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


class GitDagLineEdit(completion.GitLogLineEdit):  # type: ignore[misc, valid-type]
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


GRAPH_ROW_ROLE = Qt.UserRole + 1
GRAPH_PREV_ROW_ROLE = Qt.UserRole + 2
COMMIT_ROLE = Qt.UserRole + 3

_REMOTES_PREFIX = 'remotes/'
_TAGS_PREFIX = 'tags/'
_HEADS_PREFIX = 'heads/'


class RefType(enum.Enum):
    LOCAL = 'local'
    REMOTE = 'remote'
    TAG = 'tag'
    OTHER = 'other'


def _parse_ref(ref: str) -> tuple[str, str | None, str | None, RefType]:
    """Return display properties for a decorated ref:

    - display_text - full text to display
    - condensed_text - what will be displayed in condensed mode (optional)
    - branch_name - the branch or tag name ref refers to (optional)
    - ref_type - RefType enum
    """
    if ref.startswith(_REMOTES_PREFIX):
        display_text = ref[len(_REMOTES_PREFIX) :]
        slash = display_text.find('/')
        remote_name = display_text[:slash]
        branch_name = display_text[slash + 1 :] if slash >= 0 else None
        return display_text, f'{remote_name}/\u2026', branch_name, RefType.REMOTE
    if ref.startswith(_TAGS_PREFIX):
        name = ref[len(_TAGS_PREFIX) :]
        return name, name, name, RefType.TAG
    if ref.startswith(_HEADS_PREFIX):
        name = ref[len(_HEADS_PREFIX) :]
        return name, name, name, RefType.LOCAL
    return ref, ref, None, RefType.OTHER


def _prepare_labels(refs: list[str]) -> list[tuple[str, str, str | None]]:
    """Decide which labels to condense and return (ref, display_text, condensed_text).

    Refs are grouped into groups with the same branch name. Local branch (if any)
    is placed last. All refs within the group except the last are condensed to
    "remote/\u2026" (horizontal ellipsis).
    """

    # branch name -> (ref, is_local, display, condensed)
    groups: dict[
        str, list[tuple[str, bool, str, str | None]]
    ] = collections.defaultdict(list)

    non_group: list[tuple[str, str]] = []
    for ref in refs:
        if ref == 'HEAD':
            continue

        display, condensed, branch_name, ref_type = _parse_ref(ref)
        if ref_type in (RefType.OTHER, RefType.TAG) or branch_name is None:
            non_group.append((ref, display))
            continue
        groups[branch_name].append((ref, ref_type == RefType.LOCAL, display, condensed))

    # non grouped special refs go first
    result: list[tuple[str, str, str | None]] = []
    for ref, display in non_group:
        result.append((ref, display, None))

    for branch_name in sorted(groups.keys()):
        remotes = groups.get(branch_name, [])
        # sort by is_local, display -> local branch will always be last
        remotes.sort(key=lambda item: (item[1], item[2]))
        condense_count = len(remotes) - 1

        for i, (ref, _, display, condensed) in enumerate(remotes):
            result.append((ref, display, condensed if i < condense_count else None))

    return result


@dataclass(frozen=True)
class InlineGraphStyle:
    """Palette-derived colors for the inline commit graph."""

    normal_fill: QtGui.QColor
    merge_fill: QtGui.QColor
    head_fill: QtGui.QColor
    head_accent: QtGui.QColor
    outline: QtGui.QColor
    text: QtGui.QColor
    selected_text: QtGui.QColor
    chip_text: QtGui.QColor
    chip_text_candidates: tuple[QtGui.QColor, ...]
    chip_other: QtGui.QColor
    chip_remote: QtGui.QColor
    chip_head: QtGui.QColor
    lane_colors: tuple[QtGui.QColor, ...]


def _opaque_color(color, fallback_value=0.5):
    """Return a valid opaque copy, synthesizing only for an invalid color."""
    if not color.isValid():
        return QtGui.QColor.fromHsvF(0.0, 0.0, fallback_value, 1.0)
    result = QtGui.QColor(color)
    result.setAlphaF(1.0)
    return result


def _mix_color(first, second, second_weight):
    """Return an opaque palette color blended towards another palette color."""
    first = _opaque_color(first)
    second = _opaque_color(second)
    first_weight = 1.0 - second_weight
    return QtGui.QColor.fromRgbF(
        first.redF() * first_weight + second.redF() * second_weight,
        first.greenF() * first_weight + second.greenF() * second_weight,
        first.blueF() * first_weight + second.blueF() * second_weight,
        1.0,
    )


def _color_luminance(color):
    channels = []
    for value in (color.redF(), color.greenF(), color.blueF()):
        if value <= 0.04045:
            channels.append(value / 12.92)
        else:
            channels.append(((value + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _color_contrast(first, second):
    lighter, darker = sorted(
        (_color_luminance(first), _color_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def _best_contrast(candidates, backgrounds):
    candidates = tuple(_opaque_color(color) for color in candidates)
    if not candidates:
        candidates = (_opaque_color(QtGui.QColor()),)
    backgrounds = tuple(_opaque_color(color) for color in backgrounds)
    if not backgrounds:
        return candidates[0]
    return max(
        candidates,
        key=lambda color: min(_color_contrast(color, bg) for bg in backgrounds),
    )


def _lane_colors(palette):
    base_colors = tuple(
        _opaque_color(color)
        for color in (
            palette.base().color(),
            palette.alternateBase().color(),
            palette.highlight().color(),
        )
    )
    palette_colors = base_colors + tuple(
        _opaque_color(color)
        for color in (palette.text().color(), palette.highlightedText().color())
    )
    hsv = [color.getHsvF() for color in palette_colors]
    hues = [hue for hue, _saturation, _value, _alpha in hsv if hue >= 0.0]
    hue = hues[0] if hues else 0.0
    palette_saturation = max(saturation for _hue, saturation, _value, _alpha in hsv)
    palette_value = max(value for _hue, _saturation, value, _alpha in hsv)
    saturations = (
        max(0.12, palette_saturation * 0.35),
        max(0.38, palette_saturation * 0.65),
        max(0.68, palette_saturation),
    )
    values = (0.16, 0.34, 0.56, max(0.78, palette_value), 1.0)

    result = []
    used = set()
    for shift in (0.0, 0.21, 0.43, 0.67, 0.83):
        shifted_hue = (hue + shift) % 1.0
        candidates = [
            QtGui.QColor.fromHsvF(shifted_hue, saturation, value, 1.0)
            for saturation in saturations
            for value in values
        ]
        seed = QtGui.QColor.fromHsvF(shifted_hue, saturations[-1], values[0], 1.0)
        for foreground in palette_colors:
            candidates.extend(
                _mix_color(seed, foreground, weight) for weight in (0.35, 0.55, 0.72)
            )
        distinct_candidates = {
            candidate.rgba(): candidate
            for candidate in candidates
            if candidate.rgba() not in used
        }
        lane = _best_contrast(distinct_candidates.values(), base_colors)
        result.append(lane)
        used.add(lane.rgba())

    # QColor quantizes channels, so validate uniqueness after all HSV fallbacks.
    if len({color.rgba() for color in result}) != len(result):
        raise AssertionError('lane color fallback did not produce distinct colors')
    return tuple(result)


def _distinct_chip_backgrounds(colors, palette_colors):
    """Return three semantic chip colors, expanding collapsed palette roles."""
    colors = tuple(_opaque_color(color) for color in colors)
    if len({color.rgba() for color in colors}) == len(colors):
        return colors
    hsv = [color.getHsvF() for color in palette_colors]
    hues = [hue for hue, _saturation, _value, _alpha in hsv if hue >= 0.0]
    hue = hues[0] if hues else 0.0
    saturation = max(0.58, max(value[1] for value in hsv))
    average_luminance = sum(_color_luminance(color) for color in palette_colors) / len(
        palette_colors
    )
    value = 0.34 if average_luminance > 0.45 else 0.76
    return tuple(
        QtGui.QColor.fromHsvF((hue + shift) % 1.0, saturation, value, 1.0)
        for shift in (0.0, 0.34, 0.67)
    )


def inline_graph_style(palette):
    """Build inline graph colors from the current widget palette without caching."""
    base = _opaque_color(palette.base().color())
    alternate = _opaque_color(palette.alternateBase().color())
    text = _opaque_color(palette.text().color())
    highlight = _opaque_color(palette.highlight().color())
    highlighted_text = _opaque_color(palette.highlightedText().color())
    chip_other, chip_remote, chip_head = _distinct_chip_backgrounds(
        (
            _mix_color(base, alternate, 0.72),
            _mix_color(alternate, highlight, 0.38),
            _mix_color(highlight, base, 0.24),
        ),
        (base, alternate, highlight, text, highlighted_text),
    )
    neutral_low = QtGui.QColor.fromHsvF(0.0, 0.0, 0.0, 1.0)
    neutral_high = QtGui.QColor.fromHsvF(0.0, 0.0, 1.0, 1.0)
    chip_text_candidates = (text, highlighted_text, neutral_low, neutral_high)
    raw_highlight = palette.highlight().color()
    raw_highlighted_text = palette.highlightedText().color()
    if (
        raw_highlight.isValid()
        and raw_highlight.alpha() == 255
        and raw_highlighted_text.isValid()
        and raw_highlighted_text.alpha() == 255
        and _color_contrast(highlighted_text, highlight) >= 4.5
    ):
        selected_text = highlighted_text
    else:
        selected_text = _best_contrast(
            chip_text_candidates, (highlight, base, alternate)
        )
    chip_text = _best_contrast(
        chip_text_candidates, (chip_other, chip_remote, chip_head)
    )
    return InlineGraphStyle(
        normal_fill=_mix_color(base, text, 0.18),
        merge_fill=_mix_color(alternate, highlight, 0.44),
        head_fill=_mix_color(highlight, base, 0.16),
        head_accent=_mix_color(highlight, highlighted_text, 0.52),
        outline=_mix_color(text, base, 0.18),
        text=text,
        selected_text=selected_text,
        chip_text=chip_text,
        chip_text_candidates=chip_text_candidates,
        chip_other=chip_other,
        chip_remote=chip_remote,
        chip_head=chip_head,
        lane_colors=_lane_colors(palette),
    )


class GraphDelegate(QtWidgets.QStyledItemDelegate):
    LANE_WIDTH = 18
    DOT_RADIUS = 5
    EDGE_WIDTH = 3
    ROW_HEIGHT = 26

    LABEL_BORDER = 3
    LABEL_SPACING = 4
    LABEL_TEXT_OFFSET = 2
    ANIMATION_DURATION = 50

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hover_item: object | None = None
        self._hover_label_idx: int = -1
        self._expand_progress: float = 0.0
        self._animation = QtCore.QVariantAnimation(self)
        self._animation.setDuration(self.ANIMATION_DURATION)
        self._animation.valueChanged.connect(self._on_animation_value)
        self._animation.finished.connect(self._on_animation_finished)

    def _on_animation_value(self, value):
        self._expand_progress = value
        parent = self.parent()
        if parent is not None:
            parent.viewport().update()

    def _on_animation_finished(self) -> None:
        if self._expand_progress == 0.0:
            self._hover_item = None
            self._hover_label_idx = -1

    def set_hover(self, item: object | None, label_idx: int) -> None:
        if item == self._hover_item and label_idx == self._hover_label_idx:
            return
        self._animation.stop()
        if label_idx >= 0 and item is not None:
            self._hover_item = item
            self._hover_label_idx = label_idx
            self._animation.setStartValue(0.0)
            self._animation.setEndValue(1.0)
            self._animation.start()
        else:
            self._animation.setStartValue(self._expand_progress)
            self._animation.setEndValue(0.0)
            self._animation.start()

    def paint(self, painter, option, index):
        style = inline_graph_style(option.palette)
        row = index.data(GRAPH_ROW_ROLE)
        prev_row = index.data(GRAPH_PREV_ROW_ROLE)

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setClipRect(option.rect)

        rect = option.rect
        mid_y = rect.center().y()
        top_y = rect.top()
        # +1 to connect to the next row (FlatCap ends lines exactly at the endpoint)
        bottom_y = rect.bottom() + 1
        lane_w = self.LANE_WIDTH

        selected = bool(option.state & QtWidgets.QStyle.State_Selected)
        if selected:
            painter.fillRect(rect, option.palette.highlight())

        # Draw the graph if we have graph data.
        if row is not None or prev_row is not None:
            pen = QtGui.QPen()
            pen.setWidth(self.EDGE_WIDTH)
            pen.setCapStyle(Qt.FlatCap)

            # Top half: edges from the previous row arrive vertically.
            if prev_row is not None:
                for edge in prev_row.edges_to_parent:
                    color = style.lane_colors[edge.color_index % len(style.lane_colors)]
                    pen.setColor(color)
                    painter.setPen(pen)
                    to_x = rect.left() + edge.to_column * lane_w + lane_w // 2
                    painter.drawLine(to_x, top_y, to_x, mid_y)

            # Bottom half: straight or spline depending on diagonal.
            if row is not None:
                for edge in row.edges_to_parent:
                    color = style.lane_colors[edge.color_index % len(style.lane_colors)]
                    pen.setColor(color)
                    painter.setPen(pen)
                    from_x = rect.left() + edge.from_column * lane_w + lane_w // 2
                    to_x = rect.left() + edge.to_column * lane_w + lane_w // 2
                    if edge.from_column == edge.to_column:
                        painter.drawLine(from_x, mid_y, to_x, bottom_y)
                    else:
                        path = QtGui.QPainterPath()
                        path.moveTo(from_x, mid_y)
                        path.cubicTo(
                            from_x,
                            bottom_y,
                            to_x,
                            mid_y,
                            to_x,
                            bottom_y,
                        )
                        painter.drawPath(path)

            if row is not None:
                cx = rect.left() + row.commit_column * lane_w + lane_w // 2
                color_map = {
                    GraphRowColor.NORMAL: style.normal_fill,
                    GraphRowColor.MERGE: style.merge_fill,
                    GraphRowColor.HEAD: style.head_fill,
                }
                if row.color == GraphRowColor.HEAD:
                    accent_pen = QtGui.QPen(style.head_accent)
                    accent_pen.setWidth(2)
                    painter.setPen(accent_pen)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(
                        QtCore.QPointF(cx, mid_y),
                        self.DOT_RADIUS + 2,
                        self.DOT_RADIUS + 2,
                    )
                outline_pen = QtGui.QPen(style.outline)
                outline_pen.setWidth(2)
                painter.setPen(outline_pen)
                painter.setBrush(color_map[row.color])
                painter.drawEllipse(
                    QtCore.QPointF(cx, mid_y), self.DOT_RADIUS, self.DOT_RADIUS
                )

        commit = index.data(COMMIT_ROLE)

        label_x = rect.left() + self._graph_width(row, prev_row) + 8
        labels_width = 0

        if commit and commit.tags:
            painter.setFont(option.font)
            tree = self.parent()
            item = tree.itemFromIndex(index) if tree else None
            labels_width = self._draw_labels(
                painter,
                mid_y,
                commit.tags,
                label_x,
                option.fontMetrics,
                item,
                style,
                style.selected_text if selected else None,
            )

        text = index.data(Qt.DisplayRole)
        if text:
            text_x = int(label_x + labels_width + 8)
            text_rect = rect.adjusted(text_x - rect.left(), 0, 0, 0)
            painter.setPen(style.selected_text if selected else style.text)
            painter.drawText(
                text_rect,
                Qt.AlignLeft | Qt.AlignVCenter,
                text,
            )

        painter.restore()

    def _get_spacing(self, condensed_text: str | None) -> int:
        if condensed_text is not None:
            return 0
        return self.LABEL_SPACING

    def _draw_labels(
        self,
        painter: QtGui.QPainter | None,
        y: int,
        tags: list[str],
        start_x: int,
        font_metrics: QtGui.QFontMetrics,
        item: object | None,
        style: InlineGraphStyle | None = None,
        selected_text: QtGui.QColor | None = None,
    ):
        """Draw branch/tag labels and return total width used."""
        current_x = start_x
        x_offset = self.LABEL_TEXT_OFFSET
        y_offset = 0

        for i, (tag, display_text, condensed_text) in enumerate(_prepare_labels(tags)):
            if painter is not None:
                brush = style.chip_other
                if tag == 'HEAD' or tag.startswith(_TAGS_PREFIX):
                    brush = style.chip_remote
                elif tag.startswith(_HEADS_PREFIX):
                    brush = style.chip_head
                candidates = style.chip_text_candidates
                if selected_text is not None:
                    candidates = (_opaque_color(selected_text),) + candidates
                chip_text = _best_contrast(candidates, (brush,))
                painter.setPen(QtGui.QPen(chip_text))
                painter.setBrush(brush)

            shown, text_width = self._label_shown_text(
                condensed_text, display_text, font_metrics, item, i
            )
            text_height = font_metrics.height()

            text_rect = QtCore.QRectF(
                current_x, y - text_height / 2, text_width, text_height
            )

            box_rect = text_rect.adjusted(-x_offset, -y_offset, x_offset, y_offset)

            if painter is not None:
                painter.drawRoundedRect(box_rect, self.LABEL_BORDER, self.LABEL_BORDER)
                painter.save()
                painter.setClipRect(box_rect)
                painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, shown)
                painter.restore()

            current_x += text_width + x_offset * 2 + self._get_spacing(condensed_text)

        return current_x - start_x

    def _labels_width(self, font_metrics: QtGui.QFontMetrics, tags: list[str]):
        """Calculate total width needed for all labels."""
        return self._draw_labels(None, 0, tags, 0, font_metrics, None)

    def _label_shown_text(
        self,
        condensed_text: str | None,
        display_text: str,
        font_metrics: QtGui.QFontMetrics,
        item: object | None,
        label_idx: int,
    ) -> tuple[str, int]:
        """Return (text_to_draw, pixel_width) for a label"""
        if not condensed_text:
            return display_text, font_metrics.horizontalAdvance(display_text)
        is_hovered = (
            item is not None
            and item is self._hover_item
            and label_idx == self._hover_label_idx
        )
        if not is_hovered or self._expand_progress == 0.0:
            return condensed_text, font_metrics.horizontalAdvance(condensed_text)
        condensed_w = font_metrics.horizontalAdvance(condensed_text)
        full_w = font_metrics.horizontalAdvance(display_text)
        width = condensed_w + (full_w - condensed_w) * self._expand_progress
        return display_text, width

    def _graph_width(self, row, prev_row):
        """Calculate the width needed for the graph."""
        if row is None and prev_row is None:
            return 0
        max_col = 0
        if row is not None:
            max_col = max(max_col, row.commit_column)
            for edge in row.edges_to_parent:
                max_col = max(max_col, edge.from_column, edge.to_column)
        if prev_row is not None:
            for edge in prev_row.edges_to_parent:
                max_col = max(max_col, edge.from_column, edge.to_column)
        return (max_col + 1) * self.LANE_WIDTH

    def sizeHint(self, option, index):
        graph_row = index.data(GRAPH_ROW_ROLE)
        prev_row = index.data(GRAPH_PREV_ROW_ROLE)
        graph_width = self._graph_width(graph_row, prev_row)

        commit = index.data(COMMIT_ROLE)

        labels_width = 0
        if commit and commit.tags:
            labels_width = self._labels_width(option.fontMetrics, commit.tags)

        # Add space for text if present.
        text = index.data(Qt.DisplayRole)
        if text:
            text_width = option.fontMetrics.horizontalAdvance(text) + 16
        else:
            text_width = 0

        total_width = graph_width + 8 + labels_width + 8 + text_width
        total_width = max(total_width, self.LANE_WIDTH * 4)
        height = max(self.ROW_HEIGHT, option.fontMetrics.height() + 4)
        return QtCore.QSize(total_width, height)

    def _label_hit_test(
        self,
        pos,
        rect: QtCore.QRectF,
        font_metrics: QtGui.QFontMetrics,
        index: int,
        item: object | None,
    ) -> tuple[int, bool]:
        """Return (index, is_condensed) if pos is over a label, else (-1, False)."""
        commit = index.data(COMMIT_ROLE)
        if not commit or not commit.tags:
            return -1, False
        row = index.data(GRAPH_ROW_ROLE)
        prev_row = index.data(GRAPH_PREV_ROW_ROLE)
        x_offset = self.LABEL_TEXT_OFFSET
        current_x = rect.left() + self._graph_width(row, prev_row) + 8
        mid_y = rect.center().y()
        text_height = font_metrics.height()
        for i, (_, display_text, condensed_text) in enumerate(
            _prepare_labels(commit.tags)
        ):
            _, text_width = self._label_shown_text(
                condensed_text, display_text, font_metrics, item, i
            )
            box_left = current_x - x_offset
            box_right = current_x + text_width + x_offset
            box_top = mid_y - text_height / 2
            box_bottom = mid_y + text_height / 2
            if box_left <= pos.x() <= box_right and box_top <= pos.y() <= box_bottom:
                return i, condensed_text is not None
            current_x += text_width + x_offset * 2 + self._get_spacing(condensed_text)
        return -1, False

    def update_label_hover(
        self,
        pos,
        rect: QtCore.QRectF,
        font_metrics: QtGui.QFontMetrics,
        index: int,
        item: object | None,
    ) -> None:
        if item is None:
            self.set_hover(None, -1)
            return
        label_idx, is_condensed = self._label_hit_test(
            pos, rect, font_metrics, index, item
        )
        if label_idx >= 0 and is_condensed is not None:
            self.set_hover(item, label_idx)
        else:
            self.set_hover(None, -1)


class CommitTreeWidgetItem(QtWidgets.QTreeWidgetItem):
    """Custom TreeWidgetItem used in to build the commit tree widget"""

    SUMMARY = 0
    AUTHOR = 1
    DATE = 2

    def __init__(self, commit, parent=None):
        QtWidgets.QTreeWidgetItem.__init__(self, parent)
        self.commit = commit
        self.setText(self.SUMMARY, commit.summary)
        self.setText(self.AUTHOR, commit.author)
        self.setText(self.DATE, commit.authdate)


class CommitTreeWidget(standard.TreeWidget, ViewerMixin):
    """Display commits using a flat treewidget in "list" mode"""

    commits_selected = Signal(object)
    diff_commits = Signal(object, object)
    search_line_range_in_oid = Signal(object)
    zoom_to_fit = Signal()

    def __init__(self, context, parent):
        standard.TreeWidget.__init__(self, parent)
        ViewerMixin.__init__(self)

        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setHeaderLabels([N_('Summary'), N_('Author'), N_('Date, Time')])
        self.header().setSectionResizeMode(
            CommitTreeWidgetItem.DATE, QtWidgets.QHeaderView.Stretch
        )

        self.graph_delegate = GraphDelegate(self)
        self.context = context
        self.oidmap = {}
        self.menu_actions = None
        self.selecting = False
        self.commits = []
        self._column_init_state = ColumnInitState.NONE
        self.action_up = qtutils.add_action(
            self, N_('Go Up'), self.go_up, hotkeys.MOVE_UP
        )

        self.action_down = qtutils.add_action(
            self, N_('Go Down'), self.go_down, hotkeys.MOVE_DOWN
        )

        self.zoom_to_fit_action = qtutils.add_action(
            self, N_('Zoom to Fit'), self.zoom_to_fit.emit, hotkeys.FIT
        )

        self.setMouseTracking(True)
        self.viewport().setMouseTracking(True)

        self.itemSelectionChanged.connect(
            self.selection_changed, type=Qt.QueuedConnection
        )
        self.itemDoubleClicked.connect(self._commit_double_clicked)

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
            # Skip both the showEvent default resize AND the post-graph-load
            # resizeColumnToContents() so that user-picked widths stick across
            # restarts.
            self._column_init_state = ColumnInitState.GRAPH
        return True

    # Qt overrides
    def showEvent(self, event):
        """Override QWidget::showEvent() to size columns when we are shown"""
        standard.TreeWidget.showEvent(self, event)
        # Defer resizing columns until the widget has been shown so that width() returns
        # the correct value.
        if self._column_init_state < ColumnInitState.SHOW_EVENT:
            self._column_init_state = ColumnInitState.SHOW_EVENT
            width = self.header().width()
            summary_width = int(width * 0.70)
            author_width = int(width * 0.15)
            # Set initial SUMMARY column width; it will be adjusted when graph loads.
            self.setColumnWidth(CommitTreeWidgetItem.SUMMARY, summary_width)
            self.setColumnWidth(CommitTreeWidgetItem.AUTHOR, author_width)

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.PaletteChange:
            self.viewport().update()
        super().changeEvent(event)

    def display_inline_graph(self, enabled):
        """Enable and disable the display of inline graph in the commit list"""
        if enabled:
            delegate = self.graph_delegate
        else:
            delegate = None
        self.setItemDelegateForColumn(CommitTreeWidgetItem.SUMMARY, delegate)

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

    def add_commits(self, commits, graph_result):
        """Add commits and their precomputed graph rows to the tree."""
        self.commits.extend(commits)
        items = []
        for commit in reversed(commits):
            item = CommitTreeWidgetItem(commit)
            items.append(item)
            self.oidmap[commit.oid] = item
            for tag in commit.tags:
                self.oidmap[tag] = item

        self.insertTopLevelItems(0, items)
        self.apply_graph_result(graph_result)

    def apply_graph_result(self, graph_result) -> None:
        oid_to_index: dict[str, int] = {}
        for i, row in enumerate(graph_result.rows):
            oid_to_index[row.commit_oid] = i
        rows = graph_result.rows
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if item is None:
                continue
            row_idx = oid_to_index.get(item.commit.oid)
            if row_idx is None:
                continue
            item.setData(CommitTreeWidgetItem.SUMMARY, GRAPH_ROW_ROLE, rows[row_idx])
            item.setData(CommitTreeWidgetItem.SUMMARY, COMMIT_ROLE, item.commit)
            if row_idx > 0:
                item.setData(
                    CommitTreeWidgetItem.SUMMARY,
                    GRAPH_PREV_ROW_ROLE,
                    rows[row_idx - 1],
                )
        # Resize column to fit content after graph data is loaded.
        if self._column_init_state < ColumnInitState.GRAPH:
            self._column_init_state = ColumnInitState.GRAPH
            self.resizeColumnToContents(CommitTreeWidgetItem.SUMMARY)

    def create_patch(self):
        """Export a patch from the selected items"""
        items = self.selectedItems()
        if not items:
            return
        context = self.context
        oids = [item.commit.oid for item in reversed(items)]
        all_oids = [commit.oid for commit in self.commits]
        cmds.do(cmds.FormatPatch, context, oids, all_oids)

    def _commit_double_clicked(self, item, _column):
        'A double-click means "take me to that branch".'
        self.checkout_commit(getattr(item, 'commit', None))

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

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        pos = event.pos()
        item = self.itemAt(pos)
        rect = self.visualItemRect(item) if item is not None else QtCore.QRectF()
        index = (
            self.indexFromItem(item, CommitTreeWidgetItem.SUMMARY)
            if item is not None
            else -1
        )
        self.graph_delegate.update_label_hover(
            pos, rect, self.fontMetrics(), index, item
        )
        QtWidgets.QTreeWidget.mouseMoveEvent(self, event)

    def leaveEvent(self, event):
        self.graph_delegate.set_hover(None, -1)
        QtWidgets.QTreeWidget.leaveEvent(self, event)


@dataclass(frozen=True)
class _HistoryCacheMetadata:
    oids: tuple[str, ...]
    refs: frozenset[str]
    count: int
    display_status: bool
    generation: int = 0


class CommitHistoryWidget(QtWidgets.QWidget):
    """Reusable commit history controls, tree, and loading state."""

    commits_selected = Signal(object)
    commits_loaded = Signal(object)
    controls_changed = Signal(object)

    def __init__(
        self,
        context,
        ref='--all',
        count=1000,
        display_status=False,
        parent=None,
        display_inline_graph=False,
        display_files=False,
    ):
        super().__init__(parent)
        self.context = context
        self.model = context.model

        self.commits = {}
        self.commit_list = []
        self.selection = []
        self.old_selection = []
        self.old_refs = set()
        self.old_oids = None
        self.old_count = 0
        self.old_display_status = None
        self.last_successful_cache_key = None
        self.force_refresh = False
        self.repository_generation = 0
        self.successful_repository_generation = -1

        self.active_thread = None
        self.active_request = None
        self.active_run_id = None
        self.active_result = None
        self.active_cache_metadata = None
        self.pending_request = None
        self.pending_cache_metadata = None
        self._next_run_id = 1
        self.stopping = False
        self.loading = False
        self.error_status = None
        self._widgets_initialized = False
        self._files_dirty = False
        self._files_timer = QtCore.QTimer(self)
        self._files_timer.setSingleShot(True)
        self._files_timer.setInterval(100)
        self._files_timer.timeout.connect(self._load_pending_files)

        self.revtext = GitDagLineEdit(context)
        self.revtext.setText(ref)
        self.maxresults = standard.SpinBox(digits=None, maxi=9999999, wrap=True)
        self.maxresults.setValue(count)
        self.history_error_status = QtWidgets.QLabel()
        self.history_error_status.setObjectName('HistoryErrorStatus')
        self.history_error_status.setStyleSheet('QLabel { color: #c01c28; }')
        self.history_error_status.hide()
        self.treewidget = CommitTreeWidget(context, self)

        self.display_inline_graph_action = qtutils.add_action_bool(
            self,
            N_('Display Inline Graph'),
            self.treewidget.display_inline_graph,
            display_inline_graph,
        )
        self.treewidget.display_inline_graph(display_inline_graph)
        self.display_status_action = qtutils.add_action_bool(
            self,
            N_('Display Worktree Status'),
            self._display_worktree_status,
            display_status,
        )

        self.filewidget = filelist.FileWidget(context, self)
        self.filewidget.setVisible(display_files)
        self.files_splitter = qtutils.splitter(
            Qt.Horizontal, self.treewidget, self.filewidget
        )
        self.files_splitter.setChildrenCollapsible(False)
        self.files_splitter.setStretchFactor(0, 3)
        self.files_splitter.setStretchFactor(1, 1)

        self.display_files_action = qtutils.add_action_bool(
            self,
            N_('Display Commit Files'),
            self.display_files,
            display_files,
        )

        controls_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.revtext,
            self.history_error_status,
            self.maxresults,
        )
        controls_layout.setAlignment(self.maxresults, Qt.AlignTop)
        controls_widget = QtWidgets.QWidget(self)
        controls_widget.setLayout(controls_layout)
        layout = qtutils.vbox(
            defs.no_margin, defs.spacing, controls_widget, self.files_splitter
        )
        # Pin the controls row to its natural height; give the splitter the
        # remaining vertical space.
        layout.setStretchFactor(controls_widget, 0)
        layout.setStretchFactor(self.files_splitter, 1)
        self.setLayout(layout)

        self.treewidget.commits_selected.connect(self.select_commits)
        self.maxresults.editingFinished.connect(self.display, type=Qt.QueuedConnection)
        self.revtext.activated.connect(self.display, type=Qt.QueuedConnection)
        self.revtext.enter.connect(self.display, type=Qt.QueuedConnection)
        self.revtext.down.connect(self.focus_tree, type=Qt.QueuedConnection)
        self.model.updated.connect(self.model_updated, type=Qt.QueuedConnection)

    def current_request(self):
        """Return an immutable snapshot of the current history controls."""
        return dag.HistoryRequest(
            self._next_run_id,
            get(self.revtext),
            get(self.maxresults),
            get(self.display_status_action),
        )

    def set_values(self, ref, count, display_status):
        """Set all history controls from an external parameter snapshot."""
        self.revtext.setText(ref)
        self.maxresults.setValue(count)
        with qtutils.BlockSignals(self.display_status_action):
            self.display_status_action.setChecked(display_status)

    def request_history(
        self, ref=None, count=None, display_status=None, cache_metadata=None
    ):
        """Request a serialized history load from an immutable UI snapshot."""
        if self.stopping:
            return False
        if ref is None and count is None and display_status is None:
            snapshot = self.current_request()
            ref = snapshot.ref
            count = snapshot.count
            display_status = snapshot.display_status
        else:
            if ref is None:
                ref = get(self.revtext)
            if count is None:
                count = get(self.maxresults)
            if display_status is None:
                display_status = get(self.display_status_action)
        key = (ref, count, display_status)
        if self.active_request and key == self.active_request.cache_key:
            same_snapshot = (
                cache_metadata is None or cache_metadata == self.active_cache_metadata
            )
            if same_snapshot:
                self.pending_request = None
                self.pending_cache_metadata = None
                result = self.active_result
                if result is not None:
                    self.thread_result(result)
                return False
        if self.pending_request and key == self.pending_request.cache_key:
            if cache_metadata is not None:
                self.pending_cache_metadata = cache_metadata
            return False

        request = dag.HistoryRequest(self._next_run_id, ref, count, display_status)
        self._next_run_id += 1
        if self.active_thread is not None:
            self.pending_request = request
            self.pending_cache_metadata = cache_metadata
        else:
            self._start_request(request, cache_metadata)
        return True

    def _start_request(self, request, cache_metadata=None):
        if self.stopping:
            return
        thread = ReaderThread(self.context, request)
        self.active_thread = thread
        self.active_request = request
        self.active_run_id = request.run_id
        self.active_result = None
        self.active_cache_metadata = cache_metadata
        self.loading = True
        thread.result.connect(self.thread_result, type=Qt.QueuedConnection)
        thread.finished.connect(
            partial(self._thread_finished, thread), type=Qt.QueuedConnection
        )
        thread.start()

    def _finalize_thread(self, thread):
        """Finalize the active thread exactly once."""
        if thread is not self.active_thread:
            return False
        self.active_thread = None
        self.active_request = None
        self.active_run_id = None
        self.active_result = None
        self.active_cache_metadata = None
        thread.deleteLater()
        return True

    def _thread_finished(self, thread):
        if not self._finalize_thread(thread):
            return
        if self.stopping:
            self.loading = False
            return
        pending = self.pending_request
        pending_metadata = self.pending_cache_metadata
        self.pending_request = None
        self.pending_cache_metadata = None
        if pending is not None:
            self._start_request(pending, pending_metadata)
        else:
            self.loading = False

    def _set_error_status(self, status):
        self.error_status = status
        text = status or ''
        self.history_error_status.setText(text)
        self.history_error_status.setToolTip(text)
        self.history_error_status.setVisible(bool(status))
        self.revtext.setToolTip(text)
        self.revtext.hint.set_error(bool(status))

    def thread_result(self, result):
        if self.stopping or result.run_id != self.active_run_id:
            return
        if self.pending_request is not None:
            self.active_result = result
            return
        self.active_result = None
        self.loading = False
        if not result.successful:
            self._set_error_status(
                f"returncode {result.returncode}: {result.error or ''}"
            )
            return
        if result.graph is None and result.commits:
            self._set_error_status('successful history result is missing graph data')
            return
        graph_result = result.graph or graph.GraphResult(rows=[], max_columns=0)
        self._set_error_status(None)
        self.apply_result(result.commits, graph_result)
        request = self.active_request
        if request is None:
            return
        self.last_successful_cache_key = request.cache_key
        metadata = self.active_cache_metadata
        if metadata is not None:
            self.old_oids = list(metadata.oids)
            self.old_refs = set(metadata.refs)
            self.old_count = metadata.count
            self.old_display_status = metadata.display_status
            self.successful_repository_generation = metadata.generation

    def apply_result(self, commits, graph_result):
        """Atomically apply a complete successful history result."""
        previous_oids = [commit.oid for commit in self.selection or self.old_selection]
        commit_list = list(commits)
        commit_map = {}
        for commit_obj in commit_list:
            commit_map[commit_obj.oid] = commit_obj
            for tag in commit_obj.tags:
                commit_map[tag] = commit_obj
        selection = [commit_map[oid] for oid in previous_oids if oid in commit_map]
        if not selection and commit_list:
            selection = [commit_list[-1]]
        selection = sort_by_generation(selection)

        with qtutils.BlockSignals(self.treewidget):
            self.clear()
            self.commit_list = commit_list
            self.commits.update(commit_map)
            self.treewidget.add_commits(commit_list, graph_result)

        self.selection = list(selection)
        self.old_selection = list(selection)
        self.treewidget.select_commits(selection)
        self.commits_loaded.emit(list(commit_list))
        self.commits_selected.emit(list(selection))
        self._schedule_files()

    def stop_and_wait(self):
        """Stop scheduling work and wait fully for the active worker."""
        if self.stopping:
            return
        self.stopping = True
        self.pending_request = None
        self.pending_cache_metadata = None
        thread = self.active_thread
        if thread is not None:
            if thread.isRunning():
                thread.requestInterruption()
                thread.wait()
            self._finalize_thread(thread)
        self.loading = False
        self._files_timer.stop()

    def _display_worktree_status(self, _enabled):
        """Reload after toggling WORKTREE and STAGE pseudo-commits."""
        self.display()

    def focus_input(self):
        self.revtext.setFocus()

    def focus_tree(self):
        self.treewidget.setFocus()

    def model_updated(self):
        self.load_if_stale()

    def refresh(self):
        """Unconditionally refresh the history."""
        self.force_refresh = True
        cmds.do(cmds.Refresh, self.context)

    def load_if_stale(self):
        """Mark repository data stale and use the serialized display pipeline."""
        self.repository_generation += 1
        self.display()

    def display(self):
        """Update history from GUI/model snapshots without resolving Git refs."""
        ref = get(self.revtext)
        count = get(self.maxresults)
        display_status = get(self.display_status_action)
        refs = frozenset(
            self.model.local_branches + self.model.remote_branches + self.model.tags
        )
        key = (ref, count, display_status)
        update = (
            self.force_refresh
            or key != self.last_successful_cache_key
            or refs != frozenset(self.old_refs)
            or self.repository_generation != self.successful_repository_generation
        )
        self.controls_changed.emit(key)
        if update:
            metadata = _HistoryCacheMetadata(
                (), refs, count, display_status, self.repository_generation
            )
            self.request_history(ref, count, display_status, metadata)
        self.force_refresh = False

    def select_commits(self, commits):
        """Apply and publicly relay a complete selection snapshot."""
        self.selection = list(commits)
        self.treewidget.select_commits(commits)
        self.commits_selected.emit(list(commits))
        self._schedule_files()

    def display_files(self, enabled=None):
        """Toggle the embedded commit file panel and reload the current selection."""
        if enabled is None:
            enabled = self.display_files_action.isChecked()
        self.filewidget.setVisible(bool(enabled))
        if enabled and self.selection:
            self._schedule_files()
        else:
            self._files_timer.stop()
            self._files_dirty = False
            self.filewidget.clear()

    def _schedule_files(self):
        """Debounce a file list refresh keyed to the current selection."""
        if self.stopping:
            return
        if not self.filewidget.isVisible():
            # Defer until the panel becomes visible again.
            self._files_dirty = True
            return
        self._files_dirty = False
        self._files_timer.start()

    def _load_pending_files(self):
        """Drive the file widget with the current selection, respecting visibility."""
        if self.stopping:
            return
        if not self.selection or not self.filewidget.isVisible():
            self._files_dirty = False
            return
        self._files_dirty = False
        self.filewidget.commits_selected(self.selection)

    def refresh_files(self):
        """Apply a selection that was skipped while the panel was hidden."""
        if self._files_dirty and self.filewidget.isVisible():
            self._files_timer.stop()
            self._load_pending_files()

    def clear(self):
        """Clear the tree and all applied history state."""
        self.commits.clear()
        self.commit_list = []
        self.selection = []
        self.old_selection = []
        self.treewidget.clear()
        self.filewidget.clear()

    def export_state(self):
        """Export history-child state independently of any main window."""
        log_state = self.treewidget.export_state()
        log_state['column_widths'] = log_state['column_widths'][:2]
        return {
            'ref': get(self.revtext),
            'count': get(self.maxresults),
            'display_inline_graph': self.display_inline_graph_action.isChecked(),
            'display_status': self.display_status_action.isChecked(),
            'display_files': self.display_files_action.isChecked(),
            'files_sizes': get(self.files_splitter),
            'log': log_state,
        }

    @staticmethod
    def is_valid_state(state):
        """Return whether state can be applied without coercion."""
        if not isinstance(state, dict):
            return False
        ref = state.get('ref', '')
        count = state.get('count')
        display_status = state.get('display_status', False)
        display_inline_graph = state.get('display_inline_graph', False)
        if not (
            isinstance(ref, str)
            and isinstance(count, int)
            and not isinstance(count, bool)
            and 1 <= count <= 9_999_999
            and isinstance(display_status, bool)
            and isinstance(display_inline_graph, bool)
        ):
            return False
        display_files = state.get('display_files', False)
        if not isinstance(display_files, bool):
            return False
        files_sizes = state.get('files_sizes')
        if files_sizes is not None and not (
            isinstance(files_sizes, (list, tuple))
            and all(
                isinstance(size, int) and not isinstance(size, bool)
                for size in files_sizes
            )
        ):
            return False
        log_state = state.get('log')
        if log_state is None:
            return True
        if not isinstance(log_state, dict):
            return False
        column_widths = log_state.get('column_widths')
        return isinstance(column_widths, (list, tuple)) and all(
            isinstance(width, int) and not isinstance(width, bool)
            for width in column_widths
        )

    def apply_state(self, state):
        """Validate and atomically apply history-child state."""
        if not self.is_valid_state(state):
            return False

        ref = state.get('ref', get(self.revtext))
        count = state['count']
        display_status = state.get(
            'display_status', self.display_status_action.isChecked()
        )
        display_inline_graph = state.get('display_inline_graph', True)
        display_files = state.get(
            'display_files', self.display_files_action.isChecked()
        )
        files_sizes = state.get('files_sizes')
        log_state = state.get('log')

        self.set_values(ref, count, display_status)
        self.treewidget.display_inline_graph(display_inline_graph)
        with qtutils.BlockSignals(self.display_inline_graph_action):
            self.display_inline_graph_action.setChecked(display_inline_graph)
        self.display_files(display_files)
        with qtutils.BlockSignals(self.display_files_action):
            self.display_files_action.setChecked(display_files)
        if files_sizes:
            self.files_splitter.setSizes(list(files_sizes))
        if log_state is not None:
            self.treewidget.apply_state(log_state)
        return True

    def close_popup(self):
        self.revtext.close_popup()

    def insert_ref_expression(self, expression):
        self.revtext.insert(expression)
        self.display()

    def set_ref(self, ref):
        self.revtext.setText(ref)
        self.display()

    def event(self, event):
        if event.type() == QtCore.QEvent.DeferredDelete:
            self.close_popup()
            self.stop_and_wait()
        return super().event(event)

    def closeEvent(self, event):
        self.close_popup()
        self.stop_and_wait()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._widgets_initialized:
            self._widgets_initialized = True
            # Use sizeHint() rather than height() so the controls row is sized
            # from its natural geometry, not whatever the splitter assigned.
            self.maxresults.setMinimumHeight(self.revtext.sizeHint().height())
        self.refresh_files()


class GitDAG(standard.MainWindow):
    """Standalone DAG window composed from a reusable history widget."""

    commits_selected = Signal(object)

    def __init__(self, context, params, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 420)
        self.widget_version = 2
        self.context = context
        self.params = params
        self.model = context.model

        self.historywidget = CommitHistoryWidget(
            context,
            ref=params.ref,
            count=params.count,
            display_status=params.display_status,
            parent=self,
        )
        self.diffwidget = diff.CommitDiffWidget(context, self, is_commit=True)
        self.filewidget = filelist.FileWidget(context, self)
        self.graphview = GraphView(context, self)

        self.zoom_out = qtutils.create_action_button(
            tooltip=N_('Zoom Out'), icon=icons.zoom_out()
        )
        self.zoom_in = qtutils.create_action_button(
            tooltip=N_('Zoom In'), icon=icons.zoom_in()
        )
        self.zoom_to_fit = qtutils.create_action_button(
            tooltip=N_('Zoom to Fit'), icon=icons.zoom_fit_best()
        )

        history = self.historywidget
        tree = history.treewidget
        history.commits_loaded.connect(self._history_loaded)
        history.commits_selected.connect(self._history_selection_changed)
        history.controls_changed.connect(self._history_controls_changed)
        self.graphview.commits_selected.connect(history.select_commits)
        self.commits_selected.connect(self.diffwidget.commits_selected)
        self.commits_selected.connect(self.filewidget.commits_selected)
        self.commits_selected.connect(self.graphview.select_commits)
        self.filewidget.files_selected.connect(
            self.diffwidget.files_selected, type=Qt.QueuedConnection
        )
        # Ein wiederverwendetes Fenster fuer beide Dateilisten dieses Fensters:
        # das file_dock und das (standardmaessig verborgene) Panel im History-Widget.
        self.commit_file_diff_window = None
        for file_widget in (self.filewidget, self.historywidget.filewidget):
            file_widget.file_diff_requested.connect(
                self._show_commit_file_diff, type=Qt.QueuedConnection
            )

        self.filewidget.difftool_selected.connect(
            self.difftool_selected, type=Qt.QueuedConnection
        )
        self.filewidget.histories_selected.connect(
            self.histories_selected, type=Qt.QueuedConnection
        )

        self.proxy = FocusRedirectProxy(tree, self.graphview, self.filewidget)
        tree.menu_actions = viewer_actions(tree, self.proxy)
        self.graphview.menu_actions = viewer_actions(self.graphview, self.proxy)
        self.diffwidget_copy_commit = set_icon(
            icons.copy(),
            qtutils.add_action(
                self.diffwidget.diff,
                N_('Copy Commit'),
                tree.copy_to_clipboard,
                hotkeys.COPY_COMMIT_ID,
            ),
        )
        self.diffwidget.diff.menu_actions.append(self.diffwidget_copy_commit)

        self.log_dock = qtutils.create_dock(
            'Log', N_('Log'), self, stretch=False, hide_title=True
        )
        self.log_dock.setWidget(history)
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
        self.diff_dock.titleBarWidget().add_title_widget(self.diff_options)

        graph_controls_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.zoom_out,
            self.zoom_in,
            self.zoom_to_fit,
            defs.spacing,
        )
        graph_controls_widget = QtWidgets.QWidget()
        graph_controls_widget.setLayout(graph_controls_layout)
        self.graphview_dock = qtutils.create_dock(
            'Graph', N_('Graph'), self, hide_title=True
        )
        self.graphview_dock.setWidget(self.graphview)
        self.graphview_dock.titleBarWidget().add_corner_widget(graph_controls_widget)

        self.lock_layout_action = qtutils.add_action_bool(
            self, N_('Lock Layout'), self.set_lock_layout, False
        )
        self.refresh_action = qtutils.add_action(
            self, N_('Refresh'), history.refresh, hotkeys.REFRESH
        )
        self.menubar = QtWidgets.QMenuBar(self)
        self.setMenuBar(self.menubar)
        self.view_menu = qtutils.add_menu(N_('View'), self.menubar)
        self.view_menu.addAction(self.refresh_action)
        self.view_menu.addAction(history.display_inline_graph_action)
        self.view_menu.addAction(history.display_status_action)
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
        self.init_state(context.settings, self.resize_to_desktop)

        qtutils.connect_button(self.zoom_out, self.graphview.zoom_out)
        qtutils.connect_button(self.zoom_in, self.graphview.zoom_in)
        qtutils.connect_button(self.zoom_to_fit, self.graphview.zoom_to_fit)
        tree.zoom_to_fit.connect(self.graphview.zoom_to_fit, type=Qt.QueuedConnection)
        tree.diff_commits.connect(self.diff_commits, type=Qt.QueuedConnection)
        tree.search_line_range_in_oid.connect(
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

        qtutils.add_action(self, 'FocusInput', history.focus_input, hotkeys.FOCUS_INPUT)
        qtutils.add_action(self, 'FocusTree', history.focus_tree, hotkeys.FOCUS_TREE)
        qtutils.add_action(self, 'FocusDiff', self.focus_diff, hotkeys.FOCUS_DIFF)
        qtutils.add_close_action(self)
        self.set_params(params)

    def set_params(self, params):
        self.params = params
        self.historywidget.set_values(params.ref, params.count, params.display_status)
        self.update_window_title()

    def _history_controls_changed(self, values):
        ref, count, display_status = values
        self.params.set_ref(ref)
        self.params.set_count(count)
        self.params.set_display_status(display_status)
        self.update_window_title()

    def _history_loaded(self, commits):
        """Apply one complete commit list to the window-only graph view."""
        with qtutils.BlockSignals(self.graphview.scene()):
            self.graphview.clear()
            self.graphview.add_commits(commits)
        if commits:
            self.graphview.set_initial_view()

    def _history_selection_changed(self, commits):
        self.diffwidget_copy_commit.setEnabled(bool(commits))
        if not commits:
            self.diffwidget.oid = None
            self.diffwidget.oid_start = None
            self.diffwidget.oid_end = None
        self.commits_selected.emit(list(commits))

    def focus_diff(self):
        self.diffwidget.setFocus()

    def update_window_title(self):
        project = self.model.project
        ref = get(self.historywidget.revtext)
        if ref:
            self.setWindowTitle(
                N_('%(project)s: %(ref)s - DAG') % {'project': project, 'ref': ref}
            )
        else:
            self.setWindowTitle(project + N_(' - DAG'))

    def _show_commit_file_diff(self, commits, filename):
        """Zeigt den Diff der doppelgeklickten Datei in einem eigenen Fenster"""
        self.commit_file_diff_window = diff.show_commit_file_diff(
            self.context,
            self,
            commits,
            filename,
            window=self.commit_file_diff_window,
        )

    def export_state(self):
        """Store persistent window state plus canonical nested history state."""
        state = standard.MainWindow.export_state(self)
        state['history'] = self.historywidget.export_state()
        state['word_wrap'] = self.diffwidget.options.enable_word_wrapping.isChecked()
        state['intraline_diff_preset'] = self.diffwidget.options.intraline_diff_preset()
        state[
            'intraline_diff_timing'
        ] = self.diffwidget.options.intraline_diff_timing.isChecked()
        return state

    def apply_state(self, state):
        """Atomically apply window state and migrated history state."""
        if not isinstance(state, dict):
            return False
        if 'history' in state:
            nested_history = state['history']
            if not isinstance(nested_history, dict):
                return False
            history_state = dict(nested_history)
        else:
            history_keys = (
                'ref',
                'count',
                'display_inline_graph',
                'display_status',
                'log',
            )
            history_state = {key: state[key] for key in history_keys if key in state}

        if not self.historywidget.is_valid_state(history_state):
            return False
        if self.params.overridden('count'):
            history_state['count'] = self.params.count
        if self.params.overridden('ref'):
            history_state['ref'] = self.params.ref
        history_state.setdefault('display_status', True)
        if not self.historywidget.is_valid_state(history_state):
            return False

        string_fields = ('geometry', 'windowstate', 'intraline_diff_preset')
        bool_fields = (
            'lock_layout',
            'word_wrap',
            'intraline_diff_timing',
        )
        numeric_fields = ('width', 'height', 'x', 'y')
        if any(
            key in state and not isinstance(state[key], str) for key in string_fields
        ):
            return False
        if any(
            key in state and not isinstance(state[key], bool) for key in bool_fields
        ):
            return False
        if any(
            key in state
            and state[key] is not None
            and not isinstance(state[key], (int, str))
            for key in numeric_fields
        ):
            return False

        window_keys = (
            'geometry',
            'width',
            'height',
            'x',
            'y',
            'windowstate',
            'lock_layout',
        )
        apply_window = any(key in state for key in window_keys)
        previous_window_state = standard.MainWindow.export_state(self)
        previous_lock_action = self.lock_layout_action.isChecked()
        previous_history_state = self.historywidget.export_state()
        previous_params = (
            self.params.ref,
            self.params.count,
            self.params.display_status,
        )
        previous_word_wrap = self.diffwidget.options.enable_word_wrapping.isChecked()
        previous_intraline_preset = self.diffwidget.options.intraline_diff_preset()
        previous_intraline_timing = (
            self.diffwidget.options.intraline_diff_timing.isChecked()
        )

        def rollback():
            if apply_window:
                standard.MainWindow.apply_state(self, previous_window_state)
            self.historywidget.apply_state(previous_history_state)
            self.params.set_ref(previous_params[0])
            self.params.set_count(previous_params[1])
            self.params.set_display_status(previous_params[2])
            self.diffwidget.set_word_wrapping(previous_word_wrap, update=True)
            self.diffwidget.set_intraline_diff_preset(
                previous_intraline_preset, update=True
            )
            self.set_intraline_diff_timing(previous_intraline_timing, update=True)
            self.lock_layout_action.setChecked(previous_lock_action)

        try:
            if apply_window and not standard.MainWindow.apply_state(self, state):
                rollback()
                return False

            word_wrap = state.get('word_wrap', False)
            intraline_diff_preset = state.get(
                'intraline_diff_preset',
                diff_intraline.INTRALINE_DIFF_PRESET_DEFAULT_ID,
            )
            intraline_diff_timing = state.get('intraline_diff_timing', False)
            self.diffwidget.set_word_wrapping(word_wrap, update=True)
            self.diffwidget.set_intraline_diff_preset(
                intraline_diff_preset, update=True
            )
            self.set_intraline_diff_timing(intraline_diff_timing, update=True)

            if not self.historywidget.apply_state(history_state):
                rollback()
                return False
            ref = get(self.historywidget.revtext)
            self.params.set_ref(ref)
            self.params.set_count(get(self.historywidget.maxresults))
            self.params.set_display_status(
                get(self.historywidget.display_status_action)
            )
            self.lock_layout_action.setChecked(self.lock_layout)
        except Exception:
            rollback()
            return False
        return True

    def set_intraline_diff_preset(self, preset_id, update=False):
        self.diffwidget.set_intraline_diff_preset(preset_id, update=update)

    def set_intraline_diff_timing(self, enabled, update=False):
        self.diffwidget.set_intraline_diff_timing(enabled, update=update)

    def model_updated(self):
        self.historywidget.model_updated()
        self.update_window_title()

    def refresh(self):
        return self.historywidget.refresh()

    def display(self):
        return self.historywidget.display()

    def request_history(self, *args, **kwargs):
        return self.historywidget.request_history(*args, **kwargs)

    def select_commits(self, commits):
        self.historywidget.select_commits(commits)

    def clear(self):
        self.historywidget.clear()
        self._history_loaded([])

    def diff_commits(self, left, right):
        paths = self.params.paths()
        if paths:
            difftool.difftool_launch(self.context, left=left, right=right, paths=paths)
        else:
            difftool.diff_commits(self.context, self, left, right, detect_renames=True)

    def search_line_range_in_oid(self, oid):
        all_paths = self.filewidget.selected_paths()
        paths = all_paths[0] if all_paths else None
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
        self.historywidget.insert_ref_expression(f'-L{start},+{span}:{filename}')

    def histories_selected(self, histories):
        argv = [self.model.currentbranch, '--']
        argv.extend(histories)
        self.historywidget.set_ref(core.list2cmdline(argv))

    def difftool_selected(self, files):
        bottom, top = self.historywidget.treewidget.selected_commit_range()
        if not top:
            return
        difftool.difftool_launch(
            self.context, left=bottom, left_take_parent=True, right=top, paths=files
        )

    def grab_file(self, filename):
        oid = self.historywidget.treewidget.selected_oid()
        model = browse.BrowseModel(oid, filename=filename)
        browse.save_path(self.context, filename, model)

    def grab_file_from_parent(self, filename):
        oid = self.historywidget.treewidget.selected_oid() + '^'
        model = browse.BrowseModel(oid, filename=filename)
        browse.save_path(self.context, filename, model)

    def search_line_range_for_file(self, filename):
        oid = self.historywidget.treewidget.selected_oid()
        if not oid or not filename:
            return
        self.search_line_range_in_oid(oid)

    def closeEvent(self, event):
        if self.commit_file_diff_window is not None:
            self.commit_file_diff_window.close()
        self.historywidget.close_popup()
        self.historywidget.stop_and_wait()
        standard.MainWindow.closeEvent(self, event)


class ReaderThread(QtCore.QThread):
    result = Signal(object)

    def __init__(self, context, request):
        super().__init__()
        self.context = context
        self.request = request

    def run(self):
        """Gather a complete immutable history result in the worker thread."""
        request = self.request
        commits = []
        graph_result = None
        repo = None
        successful = False
        returncode = -1
        error = ''
        try:
            params = dag.DAG(request.ref, request.count)
            params.set_display_status(request.display_status)
            repo = dag.RepoReader(self.context, params)
            interrupted = False
            for commit in repo.get():
                if self.isInterruptionRequested():
                    interrupted = True
                    break
                commits.append(commit)
            if self.isInterruptionRequested():
                interrupted = True

            if not interrupted and repo.returncode == 0:
                stage, worktree = repo.get_worktree_commits()
                if self.isInterruptionRequested():
                    interrupted = True
                else:
                    if stage:
                        commits.append(stage)
                    if worktree:
                        commits.append(worktree)
            if not interrupted and repo.returncode == 0:
                head_oid = next(
                    (commit.oid for commit in commits if 'HEAD' in commit.tags), None
                )
                graph_result = graph.build_graph(
                    [
                        (commit.oid, [parent.oid for parent in commit.parents])
                        for commit in commits
                    ],
                    head_oid=head_oid,
                )
                if self.isInterruptionRequested():
                    interrupted = True
                    graph_result = None
            successful = repo.returncode == 0 and not interrupted
            returncode = repo.returncode if not interrupted else -1
            error = repo.error
        except Exception as exc:  # noqa: BLE001 - worker exception barrier
            commits = []
            successful = False
            returncode = -1
            error = repo.error if repo is not None and repo.error else str(exc)
        if not successful:
            commits = []
            graph_result = None
        self.result.emit(
            dag.HistoryResult(
                request.run_id,
                successful,
                returncode,
                error,
                tuple(commits),
                graph_result,
            )
        )


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
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)

        scene = QtWidgets.QGraphicsScene(self)
        scene.setItemIndexMethod(QtWidgets.QGraphicsScene.BspTreeIndex)
        scene.selectionChanged.connect(self.selection_changed, type=Qt.QueuedConnection)
        self.setScene(scene)

        self.setRenderHint(QtGui.QPainter.Antialiasing)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.SmartViewportUpdate)
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

    def refresh_appearance(self) -> None:
        """Update palette-derived colors after a system appearance change."""
        background_color = qtutils.css_color(
            self.context.app.theme.background_color_rgb()
        )
        self.setBackgroundBrush(background_color)
        self.viewport().update()

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.PaletteChange:
            self.refresh_appearance()
        super().changeEvent(event)

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
        oids = [commit.oid for commit in selected_commits]
        all_oids = [commit.oid for commit in sort_by_generation(self.commits)]
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
        for col in range(column, 0, -1 if column > 0 else 1):
            if col not in columns:
                if col > self.max_column:
                    self.max_column = col
                elif col < self.min_column:
                    self.min_column = col
                break
        else:
            # If no free column was found between graph center and desired
            # column then look for free one by moving from center along both
            # directions simultaneously.
            for col in itertools.count(0):
                if col not in columns:
                    if col > self.max_column:
                        self.max_column = col
                    break
                col = -col
                if col not in columns:
                    if col < self.min_column:
                        self.min_column = col
                    break
        self.declare_column(col)
        columns[col] = 1
        return col

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
# oid -- Git objects IDs (i.e. SHA-1 / SHA-256 IDs)
# ref -- Git references that resolve to a commit-ish (HEAD, branches, tags)
