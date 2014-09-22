"""Provides dialogs for comparing branches and commits."""
from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import qtutils
from cola import difftool
from cola import gitcmds
from cola.i18n import N_
from cola.qtutils import connect_button
from cola.widgets import defs
from cola.widgets import standard
from cola.compat import ustr


class FileItem(QtGui.QTreeWidgetItem):
    def __init__(self, path, icon):
        QtGui.QTreeWidgetItem.__init__(self, [path])
        self.path = path
        self.setIcon(0, icon)


def compare_branches():
    """Launches a dialog for comparing a pair of branches"""
    view = CompareBranchesDialog(qtutils.active_window())
    view.show()
    return view


class CompareBranchesDialog(standard.Dialog):


    def __init__(self, parent):
        standard.Dialog.__init__(self, parent=parent)

        self.BRANCH_POINT = N_('*** Branch Point ***')
        self.SANDBOX = N_('*** Sandbox ***')
        self.LOCAL = N_('Local')

        self.setWindowTitle(N_('Branch Diff Viewer'))

        self.remote_branches = gitcmds.branch_list(remote=True)
        self.local_branches = gitcmds.branch_list(remote=False)

        self.top_widget = QtGui.QWidget()
        self.bottom_widget = QtGui.QWidget()

        self.left_combo = QtGui.QComboBox()
        self.left_combo.addItem(N_('Local'))
        self.left_combo.addItem(N_('Remote'))
        self.left_combo.setCurrentIndex(0)

        self.right_combo = QtGui.QComboBox()
        self.right_combo.addItem(N_('Local'))
        self.right_combo.addItem(N_('Remote'))
        self.right_combo.setCurrentIndex(1)

        self.left_list = QtGui.QListWidget()
        self.right_list = QtGui.QListWidget()

        self.button_spacer = QtGui.QSpacerItem(1, 1,
                                               QtGui.QSizePolicy.Expanding,
                                               QtGui.QSizePolicy.Minimum)

        self.button_compare = QtGui.QPushButton()
        self.button_compare.setText(N_('Compare'))

        self.button_close = QtGui.QPushButton()
        self.button_close.setText(N_('Close'))

        self.diff_files = standard.TreeWidget()
        self.diff_files.headerItem().setText(0, N_('File Differences'))

        self.top_grid_layout = qtutils.grid(
                defs.no_margin, defs.spacing,
                (self.left_combo, 0, 0, 1, 1),
                (self.left_list, 1, 0, 1, 1),
                (self.right_combo, 0, 1, 1, 1),
                (self.right_list, 1, 1, 1, 1))
        self.top_widget.setLayout(self.top_grid_layout)

        self.bottom_grid_layout = qtutils.grid(
                defs.no_margin, defs.spacing,
                (self.diff_files, 0, 0, 1, 4),
                (self.button_spacer, 1, 1, 1, 1),
                (self.button_compare, 1, 2, 1, 1),
                (self.button_close, 1, 3, 1, 1))
        self.bottom_widget.setLayout(self.bottom_grid_layout)

        self.splitter = qtutils.splitter(Qt.Vertical,
                                         self.top_widget, self.bottom_widget)

        self.main_layout = qtutils.vbox(defs.margin, defs.spacing, self.splitter)
        self.setLayout(self.main_layout)
        self.resize(658, 350)

        connect_button(self.button_close, self.accept)
        connect_button(self.button_compare, self.compare)

        self.connect(self.diff_files,
                     SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self.compare)

        self.connect(self.left_combo,
                     SIGNAL('currentIndexChanged(int)'),
                     lambda x: self.update_combo_boxes(left=True))

        self.connect(self.right_combo,
                     SIGNAL('currentIndexChanged(int)'),
                     lambda x: self.update_combo_boxes(left=False))

        self.connect(self.left_list,
                     SIGNAL('itemSelectionChanged()'), self.update_diff_files)

        self.connect(self.right_list,
                     SIGNAL('itemSelectionChanged()'), self.update_diff_files)

        self.update_combo_boxes(left=True)
        self.update_combo_boxes(left=False)

        # Pre-select the 0th elements
        item = self.left_list.item(0)
        if item:
            self.left_list.setCurrentItem(item)
            self.left_list.setItemSelected(item, True)

        item = self.right_list.item(0)
        if item:
            self.right_list.setCurrentItem(item)
            self.right_list.setItemSelected(item, True)

    def selection(self):
        left_item = self.left_list.currentItem()
        if left_item and left_item.isSelected():
            left_item = ustr(left_item.text())
        else:
            left_item = None
        right_item = self.right_list.currentItem()
        if right_item and right_item.isSelected():
            right_item = ustr(right_item.text())
        else:
            right_item = None
        return (left_item, right_item)


    def update_diff_files(self, *rest):
        """Updates the list of files whenever the selection changes"""
        # Left and Right refer to the comparison pair (l,r)
        left_item, right_item = self.selection()
        if (not left_item or not right_item or
                left_item == right_item):
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

        if len(self.diff_arg) == 1:
            files = gitcmds.diff_index_filenames(self.diff_arg[0])
        else:
            files = gitcmds.diff_filenames(*self.diff_arg)

        self.set_diff_files(files)

    def set_diff_files(self, files):
        mk = FileItem
        icon = qtutils.icon('script.png')
        self.diff_files.clear()
        self.diff_files.addTopLevelItems([mk(f, icon) for f in files])

    def remote_ref(self, branch):
        """Returns the remote ref for 'git diff [local] [remote]'
        """
        if branch == self.BRANCH_POINT:
            # Compare against the branch point so find the merge-base
            branch = gitcmds.current_branch()
            tracked_branch = gitcmds.tracked_branch()
            if tracked_branch:
                return gitcmds.merge_base(branch, tracked_branch)
            else:
                remote_branches = gitcmds.branch_list(remote=True)
                remote_branch = 'origin/%s' % branch
                if remote_branch in remote_branches:
                    return gitcmds.merge_base(branch, remote_branch)

                elif 'origin/master' in remote_branches:
                    return gitcmds.merge_base(branch, 'origin/master')
                else:
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
            which = ustr(self.left_combo.currentText())
            widget = self.left_list
        else:
            which = ustr(self.right_combo.currentText())
            widget = self.right_list
        if not which:
            return
        # If we're looking at "local" stuff then provide the
        # sandbox as a valid choice.  If we're looking at
        # "remote" stuff then also include the branch point.
        if which == self.LOCAL:
            new_list = ([self.SANDBOX]+ self.local_branches)
        else:
            new_list = ([self.BRANCH_POINT] + self.remote_branches)

        widget.clear()
        widget.addItems(new_list)
        if new_list:
            item = widget.item(0)
            widget.setCurrentItem(item)
            widget.setItemSelected(item, True)

    def compare(self, *args):
        """Shows the diff for a specific file
        """
        tree_widget = self.diff_files
        item = tree_widget.currentItem()
        if item and item.isSelected():
            self.compare_file(item.path)

    def compare_file(self, filename):
        """Initiates the difftool session"""
        if self.use_sandbox:
            arg = self.diff_arg
        else:
            arg = (self.start, self.end)
        difftool.launch(arg + ('--', filename))
