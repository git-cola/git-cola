"""Provides dialogs for comparing branches and commits."""
from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import cmds
from .. import gitcmds
from .. import icons
from .. import qtutils
from ..i18n import N_
from ..qtutils import connect_button
from . import defs
from . import standard


class FileItem(QtWidgets.QTreeWidgetItem):
    def __init__(self, path, icon):
        QtWidgets.QTreeWidgetItem.__init__(self, [path])
        self.path = path
        self.setIcon(0, icon)


def compare_branches(context):
    """Launches a dialog for comparing a pair of branches"""
    view = CompareBranchesDialog(context, qtutils.active_window())
    view.show()
    return view


class CompareBranchesDialog(standard.Dialog):
    def __init__(self, context, parent):
        standard.Dialog.__init__(self, parent=parent)

        self.context = context
        self.BRANCH_POINT = N_('*** Branch Point ***')
        self.SANDBOX = N_('*** Sandbox ***')
        self.LOCAL = N_('Local')
        self.diff_arg = ()
        self.use_sandbox = False
        self.start = None
        self.end = None

        self.setWindowTitle(N_('Branch Diff Viewer'))

        self.remote_branches = gitcmds.branch_list(context, remote=True)
        self.local_branches = gitcmds.branch_list(context, remote=False)

        self.top_widget = QtWidgets.QWidget()
        self.bottom_widget = QtWidgets.QWidget()

        self.left_combo = QtWidgets.QComboBox()
        self.left_combo.addItem(N_('Local'))
        self.left_combo.addItem(N_('Remote'))
        self.left_combo.setCurrentIndex(0)

        self.right_combo = QtWidgets.QComboBox()
        self.right_combo.addItem(N_('Local'))
        self.right_combo.addItem(N_('Remote'))
        self.right_combo.setCurrentIndex(1)

        self.left_list = QtWidgets.QListWidget()
        self.right_list = QtWidgets.QListWidget()

        Expanding = QtWidgets.QSizePolicy.Expanding
        Minimum = QtWidgets.QSizePolicy.Minimum
        self.button_spacer = QtWidgets.QSpacerItem(1, 1, Expanding, Minimum)

        self.button_compare = qtutils.create_button(
            text=N_('Compare'), icon=icons.diff()
        )
        self.button_close = qtutils.close_button()

        self.diff_files = standard.TreeWidget()
        self.diff_files.headerItem().setText(0, N_('File Differences'))

        self.top_grid_layout = qtutils.grid(
            defs.no_margin,
            defs.spacing,
            (self.left_combo, 0, 0, 1, 1),
            (self.left_list, 1, 0, 1, 1),
            (self.right_combo, 0, 1, 1, 1),
            (self.right_list, 1, 1, 1, 1),
        )
        self.top_widget.setLayout(self.top_grid_layout)

        self.bottom_grid_layout = qtutils.grid(
            defs.no_margin,
            defs.button_spacing,
            (self.diff_files, 0, 0, 1, 4),
            (self.button_spacer, 1, 1, 1, 1),
            (self.button_close, 1, 0, 1, 1),
            (self.button_compare, 1, 3, 1, 1),
        )
        self.bottom_widget.setLayout(self.bottom_grid_layout)

        self.splitter = qtutils.splitter(
            Qt.Vertical, self.top_widget, self.bottom_widget
        )

        self.main_layout = qtutils.vbox(defs.margin, defs.spacing, self.splitter)
        self.setLayout(self.main_layout)

        connect_button(self.button_close, self.accept)
        connect_button(self.button_compare, self.compare)

        # pylint: disable=no-member
        self.diff_files.itemDoubleClicked.connect(lambda _: self.compare())
        self.left_combo.currentIndexChanged.connect(
            lambda x: self.update_combo_boxes(left=True)
        )
        self.right_combo.currentIndexChanged.connect(
            lambda x: self.update_combo_boxes(left=False)
        )

        self.left_list.itemSelectionChanged.connect(self.update_diff_files)
        self.right_list.itemSelectionChanged.connect(self.update_diff_files)

        self.update_combo_boxes(left=True)
        self.update_combo_boxes(left=False)

        # Pre-select the 0th elements
        item = self.left_list.item(0)
        if item:
            self.left_list.setCurrentItem(item)
            item.setSelected(True)

        item = self.right_list.item(0)
        if item:
            self.right_list.setCurrentItem(item)
            item.setSelected(True)

        self.init_size(parent=parent)

    def selection(self):
        left_item = self.left_list.currentItem()
        if left_item and left_item.isSelected():
            left_item = left_item.text()
        else:
            left_item = None
        right_item = self.right_list.currentItem()
        if right_item and right_item.isSelected():
            right_item = right_item.text()
        else:
            right_item = None
        return (left_item, right_item)

    def update_diff_files(self):
        """Updates the list of files whenever the selection changes"""
        # Left and Right refer to the comparison pair (l,r)
        left_item, right_item = self.selection()
        if not left_item or not right_item or left_item == right_item:
            self.set_diff_files([])
            return
        left_item = self.remote_ref(left_item)
        right_item = self.remote_ref(right_item)

        # If any of the selection includes sandbox then we
        # generate the same diff, regardless.  This means we don't
        # support reverse diffs against sandbox aka worktree.
        if self.SANDBOX in (left_item, right_item):
            self.use_sandbox = True
            if left_item == self.SANDBOX:
                self.diff_arg = (right_item,)
            else:
                self.diff_arg = (left_item,)
        else:
            self.diff_arg = (left_item, right_item)
            self.use_sandbox = False

        # start and end as in 'git diff start end'
        self.start = left_item
        self.end = right_item

        context = self.context
        if len(self.diff_arg) == 1:
            files = gitcmds.diff_index_filenames(context, self.diff_arg[0])
        else:
            files = gitcmds.diff_filenames(context, *self.diff_arg)

        self.set_diff_files(files)

    def set_diff_files(self, files):
        mk = FileItem
        icon = icons.file_code()
        self.diff_files.clear()
        self.diff_files.addTopLevelItems([mk(f, icon) for f in files])

    def remote_ref(self, branch):
        """Returns the remote ref for 'git diff [local] [remote]'"""
        context = self.context
        if branch == self.BRANCH_POINT:
            # Compare against the branch point so find the merge-base
            branch = gitcmds.current_branch(context)
            tracked_branch = gitcmds.tracked_branch(context)
            if tracked_branch:
                return gitcmds.merge_base(context, branch, tracked_branch)
            else:
                remote_branches = gitcmds.branch_list(context, remote=True)
                remote_branch = 'origin/%s' % branch
                if remote_branch in remote_branches:
                    return gitcmds.merge_base(context, branch, remote_branch)

                if 'origin/main' in remote_branches:
                    return gitcmds.merge_base(context, branch, 'origin/main')

                if 'origin/master' in remote_branches:
                    return gitcmds.merge_base(context, branch, 'origin/master')

                return 'HEAD'
        else:
            # Compare against the remote branch
            return branch

    def update_combo_boxes(self, left=False):
        """Update listwidgets from the combobox selection

        Update either the left or right listwidgets
        to reflect the available items.
        """
        if left:
            which = self.left_combo.currentText()
            widget = self.left_list
        else:
            which = self.right_combo.currentText()
            widget = self.right_list
        if not which:
            return
        # If we're looking at "local" stuff then provide the
        # sandbox as a valid choice.  If we're looking at
        # "remote" stuff then also include the branch point.
        if which == self.LOCAL:
            new_list = [self.SANDBOX] + self.local_branches
        else:
            new_list = [self.BRANCH_POINT] + self.remote_branches

        widget.clear()
        widget.addItems(new_list)
        if new_list:
            item = widget.item(0)
            widget.setCurrentItem(item)
            item.setSelected(True)

    def compare(self):
        """Shows the diff for a specific file"""
        tree_widget = self.diff_files
        item = tree_widget.currentItem()
        if item and item.isSelected():
            self.compare_file(item.path)

    def compare_file(self, filename):
        """Initiates the difftool session"""
        if self.use_sandbox:
            left = self.diff_arg[0]
            if len(self.diff_arg) > 1:
                right = self.diff_arg[1]
            else:
                right = None
        else:
            left, right = self.start, self.end
        context = self.context
        cmds.difftool_launch(context, left=left, right=right, paths=[filename])
