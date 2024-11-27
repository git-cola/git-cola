import os

from qtpy import QtWidgets
from qtpy.QtCore import Qt

from . import cmds
from . import core
from . import gitcmds
from . import hotkeys
from . import icons
from . import qtutils
from . import utils
from .git import EMPTY_TREE_OID
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
    ):
        """Show files with differences and launch difftool"""

        standard.Dialog.__init__(self, parent=parent)

        self.context = context
        self.a = a
        self.b = b
        self.diff_expr = expr

        if title is None:
            title = N_('git-cola diff')

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
        difftool_launch(self.context, left=left, right=right, paths=[path])

    def diff(self, dir_diff=False):
        paths = self.tree.selected_filenames()
        left, right = self._left_right_args()
        difftool_launch(
            self.context, left=left, right=right, paths=paths, dir_diff=dir_diff
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


def diff_commits(context, parent, a, b):
    """Show a dialog for diffing two commits"""
    dlg = Difftool(context, parent, a=a, b=b)
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
    paths=None,
    staged=False,
    dir_diff=False,
    left_take_magic=False,
    left_take_parent=False,
):
    """Launches 'git difftool' with given parameters

    :param left: first argument to difftool
    :param right: second argument to difftool_args
    :param paths: paths to diff
    :param staged: activate `git difftool --staged`
    :param dir_diff: activate `git difftool --dir-diff`
    :param left_take_magic: whether to append the magic "^!" diff expression
    :param left_take_parent: whether to append the first-parent ~ for diffing

    """
    difftool_args = ['git', 'difftool', '--no-prompt']
    if staged:
        difftool_args.append('--cached')
    if dir_diff:
        difftool_args.append('--dir-diff')

    if left:
        original_left = left
        if left_take_parent or left_take_magic:
            suffix = '^!' if left_take_magic else '~'
            # Check root commit (no parents and thus cannot execute '~')
            git = context.git
            if left in (dag.STAGE, dag.WORKTREE):
                check_ref = 'HEAD'
            else:
                check_ref = left
            status, out, err = git.rev_list(
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
                # No parent, assume it's the root commit, so we have to diff
                # against the empty tree.
                left = EMPTY_TREE_OID
                if not right and left_take_magic:
                    right = left
        # Commit has a parent, so we can take its child as requested
        if original_left not in (dag.STAGE, dag.WORKTREE):
            difftool_args.append(left)

    if right and right not in (dag.STAGE, dag.WORKTREE):
        difftool_args.append(right)

    if paths:
        difftool_args.append('--')
        difftool_args.extend(paths)

    runtask = context.runtask
    if runtask:
        Interaction.async_command(N_('Difftool'), difftool_args, runtask)
    else:
        core.fork(difftool_args)
