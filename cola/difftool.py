from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtWidgets
from qtpy.QtCore import Qt

from . import cmds
from . import gitcmds
from . import hotkeys
from . import icons
from . import qtutils
from . import utils
from .i18n import N_
from .widgets import completion
from .widgets import defs
from .widgets import filetree
from .widgets import standard


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
            self.close_button,
            qtutils.STRETCH,
            self.edit_button,
            self.diff_all_button,
            self.diff_button,
        )

        self.main_layout = qtutils.vbox(
            defs.margin, defs.spacing, self.expr, self.tree, self.button_layout
        )
        self.setLayout(self.main_layout)

        # pylint: disable=no-member
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
        cmds.difftool_launch(self.context, left=left, right=right, paths=[path])

    def diff(self, dir_diff=False):
        paths = self.tree.selected_filenames()
        left, right = self._left_right_args()
        cmds.difftool_launch(
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
