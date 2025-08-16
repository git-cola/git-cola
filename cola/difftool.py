import os
from functools import partial

from qtpy import QtWidgets
from qtpy.QtCore import Qt

from . import cmds
from . import core
from . import git
from . import gitcmds
from . import hotkeys
from . import icons
from . import qtutils
from . import utils
from .i18n import N_
from .interaction import Interaction
from .models import dag
from .widgets import completion
from .widgets import defs
from .widgets import filetree
from .widgets import standard


class LaunchDifftool(cmds.ContextCommand):
    """Launch "git difftool" with the currently selected files"""

    @staticmethod
    def name():
        return N_('Launch Diff Tool')

    def do(self):
        s = self.selection.selection()
        if s.unmerged:
            paths = s.unmerged
            if utils.is_win32():
                core.fork(['git', 'mergetool', '--no-prompt', '--'] + paths)
            else:
                cfg = self.cfg
                cmd = cfg.terminal()
                argv = utils.shell_split(cmd)

                terminal = os.path.basename(argv[0])
                shellquote_terms = {'xfce4-terminal'}
                shellquote_default = terminal in shellquote_terms

                mergetool = ['git', 'mergetool', '--no-prompt', '--']
                mergetool.extend(paths)
                needs_shellquote = cfg.get(
                    'cola.terminalshellquote', shellquote_default
                )

                if needs_shellquote:
                    argv.append(core.list2cmdline(mergetool))
                else:
                    argv.extend(mergetool)

                core.fork(argv)
        else:
            difftool_run(self.context)


class Difftool(standard.Dialog):
    def __init__(
        self,
        context,
        parent,
        a=None,
        b=None,
        expr=None,
        title=None,
        hide_expr=False,
        focus_tree=False,
        detect_renames=False,
    ):
        """Show files with differences and launch difftool"""

        standard.Dialog.__init__(self, parent=parent)

        self.context = context
        self.a = a
        self.b = b
        self.diff_expr = expr
        self.detect_renames = detect_renames

        if title is None:
            title = N_('git cola diff')

        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModal)

        self.expr = completion.GitRefLineEdit(context, parent=self)
        if expr is not None:
            self.expr.setText(expr)

        if expr is None or hide_expr:
            self.expr.hide()

        self.tree = filetree.FileTree(parent=self)

        self.diff_button = qtutils.create_button(
            text=N_('Compare'), icon=icons.diff(), enabled=False, default=True
        )
        self.diff_button.setShortcut(hotkeys.DIFF)

        self.diff_all_button = qtutils.create_button(
            text=N_('Compare All'), icon=icons.diff()
        )
        self.edit_button = qtutils.edit_button()
        self.edit_button.setShortcut(hotkeys.EDIT)

        self.close_button = qtutils.close_button()

        self.button_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            qtutils.STRETCH,
            self.close_button,
            self.edit_button,
            self.diff_all_button,
            self.diff_button,
        )

        self.main_layout = qtutils.vbox(
            defs.margin, defs.spacing, self.expr, self.tree, self.button_layout
        )
        self.setLayout(self.main_layout)

        self.tree.itemSelectionChanged.connect(self.tree_selection_changed)
        self.tree.itemDoubleClicked.connect(self.tree_double_clicked)
        self.tree.up.connect(self.focus_input)

        self.expr.textChanged.connect(self.text_changed)

        self.expr.activated.connect(self.focus_tree)
        self.expr.down.connect(self.focus_tree)
        self.expr.enter.connect(self.focus_tree)

        qtutils.connect_button(self.diff_button, self.diff)
        qtutils.connect_button(self.diff_all_button, lambda: self.diff(dir_diff=True))
        qtutils.connect_button(self.edit_button, self.edit)
        qtutils.connect_button(self.close_button, self.close)

        qtutils.add_action(self, 'Focus Input', self.focus_input, hotkeys.FOCUS)
        qtutils.add_action(
            self,
            'Diff All',
            lambda: self.diff(dir_diff=True),
            hotkeys.CTRL_ENTER,
            hotkeys.CTRL_RETURN,
        )
        qtutils.add_close_action(self)

        self.init_state(None, self.resize_widget, parent)

        self.refresh()
        if focus_tree:
            self.focus_tree()

    def resize_widget(self, parent):
        """Set the initial size of the widget"""
        width, height = qtutils.default_size(parent, 720, 420)
        self.resize(width, height)

    def focus_tree(self):
        """Focus the files tree"""
        self.tree.setFocus()

    def focus_input(self):
        """Focus the expression input"""
        self.expr.setFocus()

    def text_changed(self, txt):
        self.diff_expr = txt
        self.refresh()

    def refresh(self):
        """Redo the diff when the expression changes"""
        if self.diff_expr is not None:
            self.diff_arg = utils.shell_split(self.diff_expr)
        elif self.b is None:
            self.diff_arg = [self.a]
        else:
            if self.b == dag.WORKTREE:
                if self.a == dag.STAGE:
                    self.diff_arg = []
                else:
                    self.diff_arg = [self.a]
            elif self.b == dag.STAGE:
                if self.a == dag.WORKTREE:
                    self.diff_arg = ['--cached']
                else:
                    self.diff_arg = ['--cached', self.a]
            elif self.a == dag.WORKTREE:
                self.diff_arg = [self.b]
            elif self.a == dag.STAGE:
                self.diff_arg = ['--cached', self.b]
            else:
                self.diff_arg = [self.a, self.b]
        self.refresh_filenames()

    def refresh_filenames(self):
        context = self.context
        if self.a and self.b is None:
            filenames = gitcmds.diff_index_filenames(context, self.a)
        else:
            filenames = gitcmds.diff(context, self.diff_arg)
        self.tree.set_filenames(filenames, select=True)

    def tree_selection_changed(self):
        has_selection = self.tree.has_selection()
        self.diff_button.setEnabled(has_selection)
        self.diff_all_button.setEnabled(has_selection)

    def tree_double_clicked(self, item, _column):
        path = filetree.filename_from_item(item)
        left, right = self._left_right_args()
        difftool_launch(
            self.context,
            left=left,
            right=right,
            paths=[path],
            detect_renames=self.detect_renames,
        )

    def diff(self, dir_diff=False):
        paths = self.tree.selected_filenames()
        left, right = self._left_right_args()
        difftool_launch(
            self.context,
            left=left,
            right=right,
            paths=paths,
            dir_diff=dir_diff,
            detect_renames=self.detect_renames,
        )

    def _left_right_args(self):
        if self.diff_arg:
            left = self.diff_arg[0]
        else:
            left = None
        if len(self.diff_arg) > 1:
            right = self.diff_arg[1]
        else:
            right = None
        return (left, right)

    def edit(self):
        paths = self.tree.selected_filenames()
        cmds.do(cmds.Edit, self.context, paths)


def diff_commits(context, parent, a, b, detect_renames=False):
    """Show a dialog for diffing two commits"""
    dlg = Difftool(context, parent, a=a, b=b, detect_renames=detect_renames)
    dlg.show()
    dlg.raise_()
    return dlg.exec_() == QtWidgets.QDialog.Accepted


def diff_expression(
    context, parent, expr, create_widget=False, hide_expr=False, focus_tree=False
):
    """Show a diff dialog for diff expressions"""
    dlg = Difftool(
        context, parent, expr=expr, hide_expr=hide_expr, focus_tree=focus_tree
    )
    if create_widget:
        return dlg
    dlg.show()
    dlg.raise_()
    return dlg.exec_() == QtWidgets.QDialog.Accepted


def difftool_run(context):
    """Start a default difftool session"""
    selection = context.selection
    files = selection.group()
    if not files:
        return
    s = selection.selection()
    head = context.model.head
    difftool_launch_with_head(context, files, bool(s.staged), head)


def difftool_launch_with_head(context, filenames, staged, head):
    """Launch difftool against the provided head"""
    if head == 'HEAD':
        left = None
    else:
        left = head
    difftool_launch(context, left=left, staged=staged, paths=filenames)


def difftool_launch(
    context,
    left=None,
    right=None,
    oid=None,
    paths=None,
    is_root_commit=False,
    staged=False,
    dir_diff=False,
    left_take_parent=False,
    detect_renames=False,
):
    """Interact with 'git difftool'.

    :param left: The first argument to difftool.
    :param right: The second argument to difftool.
    :param oid: The commit to display. Can be used instead of left + right.
    :param is_root_commit: Is the commit a root commit?
    :param paths: The paths to diff.
    :param staged: Activate `git difftool --staged`.
    :param dir_diff: Activate `git difftool --dir-diff`.
    :param left_take_parent: Append the first-parent ``~`` syntax to the left argument.
    """
    args = []
    kwargs = {
        'no_prompt': True,
        '_readonly': True,
    }
    if staged:
        kwargs['cached'] = True
    if dir_diff:
        kwargs['dir_diff'] = True
    if oid:
        left, right = _get_left_right_for_oid(context, oid, is_root_commit)

    _add_difftool_args(context, args, left, right, left_take_parent)

    if paths and len(paths) == 1:
        all_names = _get_renamed_paths(context, left, right, paths[0], detect_renames)
        if all_names:
            paths.extend(all_names)
    if paths:
        args.append('--')
        args.extend(paths)

    runtask = context.runtask
    if runtask:
        argv = ['git', 'difftool']
        argv.extend(git.transform_kwargs(**kwargs))
        argv.extend(args)
        # "cmd" is for display purposes only and only displayed when an error occurs.
        cmd = core.list2cmdline(argv)
        Interaction.async_task(
            N_('Difftool'), cmd, runtask, partial(context.git.difftool, *args, **kwargs)
        )
    else:
        context.git.difftool(*args, **kwargs)


def _get_left_right_for_oid(context, oid, is_root_commit):
    """Specify diff parameters for diffing a commit"""
    if is_root_commit:
        left = context.model.empty_tree_oid
        right = oid
    else:
        left = f'{oid}~'
        right = oid
    return left, right


def _add_difftool_args(context, args, left, right, left_take_parent):
    """Setup the first argument to difftool"""
    if left:
        original_left = left
        if left_take_parent:
            suffix = '~'
            # Check root commit (no parents and thus cannot execute '~')
            if left in (dag.STAGE, dag.WORKTREE):
                check_ref = 'HEAD'
            else:
                check_ref = left
            status, out, err = context.git.rev_list(
                check_ref, parents=True, n=1, _readonly=True
            )
            Interaction.log_status(status, out, err)
            if status:
                raise OSError(f'git rev-list {left} command failed')

            if len(out.split()) >= 2:
                # Commit has a parent, so we can take its child as requested
                if left not in (dag.STAGE, dag.WORKTREE):
                    left += suffix
            else:
                # No parent, assume it's the root commit. Diff against the empty tree.
                if not right:
                    right = left
                left = context.model.empty_tree_oid
        # Commit has a parent, so we can take its child as requested
        if original_left not in (dag.STAGE, dag.WORKTREE):
            args.append(left)

    if right and right not in (dag.STAGE, dag.WORKTREE):
        args.append(right)


def _get_renamed_paths(context, left, right, path, detect_renames):
    """Get filenames as they existed beyond a rename

    Use ``git log --follow --format= --name-only -- <path>`` to discover the
    filenames as they existed in older commits. This is a slow operation when the
    commit range is large.
    """
    all_names = set()
    if (
        detect_renames
        and left
        and right
        and left not in (dag.STAGE, dag.WORKTREE)
        and right not in (dag.STAGE, dag.WORKTREE)
    ):
        # We have to check in both left->right and right->left directions because we
        # may be performing either "Diff selected to this..." or
        # "Diff this to selected...", and left/right flips directions depending on which
        # is chosen. We have to log starting from the parent commit of the start range
        # in order to include the starting commit. The starting commit may be the only
        # commit that contains the original filename.
        for rev_arg in (
            f'{left}^..{right}',
            f'{right}^..{left}',
        ):
            status, out, _ = context.git.log(
                rev_arg,
                '--',
                path,
                follow=True,
                format='',
                name_only=True,
                z=True,
                _readonly=True,
            )
            if status == 0:
                out = out[:-1]  # Strip the final NULL terminator.
                if out:
                    all_names.update(out.split('\0'))
        try:
            all_names.remove(path)
        except KeyError:
            pass

    return all_names
