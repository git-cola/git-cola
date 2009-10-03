"""This controller handles the compare commits dialog."""

import os

from PyQt4 import QtGui

import cola
from cola import utils
from cola import qtutils
from cola import difftool
from cola import gitcmds
from cola.qobserver import QObserver
from cola.models.compare import CompareModel
from cola.models.compare import BranchCompareModel
from cola.views import CompareView
from cola.views import BranchCompareView
from cola.controllers.repobrowser import select_file_from_repo

def compare_file():
    """Launches a dialog for comparing revisions touching a file path"""
    model = cola.model()
    parent = QtGui.QApplication.instance().activeWindow()
    filename = select_file_from_repo()
    if not filename:
        return
    compare(filename)

def compare(filename=None):
    """Launches a dialog for comparing a pair of commits"""
    parent = QtGui.QApplication.instance().activeWindow()
    model = CompareModel()
    view = CompareView(parent)
    ctl = CompareController(model, view, filename)
    view.show()

def branch_compare():
    """Launches a dialog for comparing a pair of branches"""
    model = BranchCompareModel()
    view = BranchCompareView(QtGui.QApplication.instance().activeWindow())
    ctl = BranchCompareController(model, view)
    view.show()

class BranchCompareController(QObserver):
    """Provides a dialog for comparing local and remote git branches"""

    BRANCH_POINT = '*** Branch Point ***'
    SANDBOX      = '*** Sandbox ***'
    LOCAL        = 'Local'

    def __init__(self, model, view):
        QObserver.__init__(self, model, view)
        self.add_observables('left_combo', 'right_combo',
                             'left_list', 'right_list',
                             'diff_files')

        # wire the compare button to the double-click action and
        # the combo boxes to the "update list of changed files" action
        self.add_callbacks(button_compare =
                                self.diff_files_doubleclick,
                           left_combo =
                               lambda x: self.update_combo_boxes(left=True),
                           right_combo =
                                lambda x: self.update_combo_boxes(left=False),
                           left_list =
                                self.update_diff_files,
                           right_list =
                                self.update_diff_files)
        # aka notify observers
        self.refresh_view()

        # Pre-select the 0th elements
        self.view.right_combo.setCurrentIndex(1)
        item = self.view.left_list.item(0)
        self.view.left_list.setCurrentItem(item)
        self.view.left_list.setItemSelected(item, True)

        item = self.view.right_list.item(0)
        self.view.right_list.setCurrentItem(item)
        self.view.right_list.setItemSelected(item, True)

    def update_diff_files(self, *rest):
        """Updates the list of files whenever the selection changes"""
        if (not self.model.has_param('left_list_item') or
                not self.model.has_param('right_list_item')):
            return
        # Left and Right refer to the comparison pair (l,r)
        left_item = self.model.left_list_item
        right_item = self.model.right_list_item
        if (not left_item or not right_item or
                left_item == right_item):
            self.model.set_diff_files([])
            return
        left_item = self.remote_ref(left_item)
        right_item = self.remote_ref(right_item)

        # If any of the selection includes sandbox then we
        # generate the same diff, regardless.  This means we don't
        # support reverse diffs against sandbox aka worktree.
        if (left_item == BranchCompareController.SANDBOX or
                right_item == BranchCompareController.SANDBOX):
            self.use_sandbox = True
            if left_item == BranchCompareController.SANDBOX:
                self.diff_arg = right_item
            else:
                self.diff_arg = left_item
        else:
            self.diff_arg = '%s..%s' % (left_item, right_item)
            self.use_sandbox = False

        # start and end as in 'git diff start end'
        self.start = left_item
        self.end = right_item

        # TODO leverage Qt's model/view architecture
        files = self.model.diff_filenames(self.diff_arg)
        self.model.set_diff_files(files)
        icon = qtutils.icon('script.png')
        for idx in xrange(0, self.view.diff_files.topLevelItemCount()):
            item = self.view.diff_files.topLevelItem(idx)
            item.setIcon(0, icon)

    def remote_ref(self, branch):
        """Returns the remote ref for 'git diff [local] [remote]'
        """
        if branch == BranchCompareController.BRANCH_POINT:
            # Compare against the branch point so find the merge-base
            branch = self.model.currentbranch
            remote = gitcmds.corresponding_remote_ref()
            return self.model.git.merge_base(branch, remote)
        else:
            # Compare against the remote branch
            return branch


    def update_combo_boxes(self, left=False):
        """Update listwidgets from the combobox selection

        Returns a closure to update either the left or right listwidgets
        to reflect the available items.
        """
        if left:
            which = self.model.left_combo_item
            param = 'left_list'
        else:
            which = self.model.right_combo_item
            param = 'right_list'
        if not which:
            return
        # If we're looking at "local" stuff then provide the
        # sandbox as a valid choice.  If we're looking at
        # "remote" stuff then also include the branch point.
        if which == self.LOCAL:
            new_list = ([BranchCompareController.SANDBOX]+
                        self.model.local_branches)
        else:
            new_list = ([BranchCompareController.BRANCH_POINT] +
                        self.model.remote_branches)
        # Update the list widget
        self.model.notification_enabled = True
        self.model.set_param(param, new_list)

    def diff_files_doubleclick(self):
        """Shows the diff for a specific file
        """
        tree_widget = self.view.diff_files
        id_num, selected = qtutils.selected_treeitem(tree_widget)
        if not selected:
            qtutils.information('Oops!', 'Please select a file to compare')
            return
        filename = self.model.diff_files[id_num]
        self._compare_file(filename)

    def _compare_file(self, filename):
        """Initiates the difftool session"""
        if self.use_sandbox:
            arg = self.diff_arg
        else:
            arg = '%s..%s' % (self.start, self.end)
        difftool.launch([arg, '--', filename])


class CompareController(QObserver):
    """Drives the "Commit->Compare..." dialog.
    """
    def __init__(self, model, view, filename=None):
        QObserver.__init__(self, model, view)
        self.filename = filename
        if self.filename:
            # If we've specified a filename up front then there's
            # no need to show the list of "changed files" since
            # we're only interested in the specified file.
            self.view.compare_files.hide()

        self.add_observables('descriptions_start', 'descriptions_end',
                             'revision_start', 'revision_end',
                             'compare_files', 'num_results',
                             'show_versions')

        # The spinbox and checkbox should both call the generic update method
        self.add_actions(num_results = self.update_results)
        self.add_actions(show_versions = self.update_results)

        # Clicking on a listwidget item should update the list of
        # "changed files".  Clicking on the "Compare" button should
        # initiate a difftool session.
        self.add_callbacks(descriptions_start =
                                lambda *x: self.update_widgets(left=True),
                           descriptions_end =
                                lambda *x: self.update_widgets(left=False),
                           button_compare =
                                self.compare_selected_file)
        self.refresh_view()

        # if we can, preselect the latest commit
        revisions = self.update_results()
        last = len(revisions)
        if (last > 1
                and self.view.descriptions_start.topLevelItemCount() > last-1
                and self.view.descriptions_end  .topLevelItemCount() > last-1):
            # select the 2nd item on the left treewidget
            startitem = self.view.descriptions_start.topLevelItem(last-2)
            self.view.descriptions_start.setCurrentItem(startitem)
            self.view.descriptions_start.setItemSelected(startitem, True)
            # select the 1st item on the right treewidget
            enditem = self.view.descriptions_end.topLevelItem(last-1)
            self.view.descriptions_end.setCurrentItem(enditem)
            self.view.descriptions_end.setItemSelected(enditem, True)

    def distance_from_end(self, tree_widget):
        """Returns  a (selected, end-index) tuple based on the selection
        """
        item_id, item_selected = qtutils.selected_treeitem(tree_widget)
        if item_selected:
            item_count = tree_widget.topLevelItemCount()
            item_delta = item_count - item_id
            return (item_selected, item_delta)
        else:
            return (item_selected, 0)

    def select_nth_item_from_end(self, tree_widget, delta):
        """Selects an item relative to the end of the treeitem list

        We select from the end to properly handle changes in the number of
        displayed commits.
        """
        count = self.view.descriptions_start.topLevelItemCount()
        idx = count - delta
        qtutils.set_selected_item(tree_widget, idx)

    def update_results(self, *args):
        """Updates the "changed files" list whenever selection changes
        """
        # We use "distance from end" since the number of entries can change
        tree_widget = self.view.descriptions_start
        start_selected, start_delta = self.distance_from_end(tree_widget)

        tree_widget = self.view.descriptions_end
        end_selected, end_delta = self.distance_from_end(tree_widget)

        # Notificaiton is disabled when inside action callbacks
        # TODO use setBlockSignals(True) on widgets instead?
        self.model.notification_enabled = True

        show_versions = self.model.show_versions
        revs = self.model.update_revision_lists(filename=self.filename,
                                                show_versions=show_versions)
        # Restore the previous selection
        if start_selected:
            tree_widget = self.view.descriptions_start
            self.select_nth_item_from_end(tree_widget, start_delta)

        if end_selected:
            tree_widget = self.view.descriptions_end
            self.select_nth_item_from_end(tree_widget, end_delta)

        return revs

    def update_widgets(self, left=True):
        """Updates the list of available revisions for comparison
        """
        # This callback can be triggered by either the 'start'
        # listwidget or the 'end' list widget.  The behavior
        # is identical; the only difference is the attribute names.
        if left:
            tree_widget = self.view.descriptions_start
            revisions_param = 'revisions_start'
            revision_param = 'revision_start'
        else:
            tree_widget = self.view.descriptions_end
            revisions_param = 'revisions_end'
            revision_param = 'revision_end'

        # Is anything selected?
        id_num, selected = qtutils.selected_treeitem(tree_widget)
        if not selected:
            return

        # Is this a valid revision?
        revisionlist = self.model.param(revisions_param)
        if id_num < len(revisionlist):
            revision = self.model.param(revisions_param)[id_num]
            self.model.set_param(revision_param, revision)

        # get the changed files list
        start = self.model.revision_start
        end = self.model.revision_end
        files = self.model.changed_files(start, end)

        # get the old name of any renamed files, and prune them
        # from the changes list
        renamed_files = self.model.renamed_files(start, end)
        for renamed in renamed_files:
            try:
                files.remove(renamed)
            except:
                pass
        # Sets the "changed files" list
        self.model.set_compare_files(files)

        # Updates the listwidget's icons
        icon = qtutils.icon('script.png')
        for idx in xrange(0, self.view.compare_files.topLevelItemCount()):
            item = self.view.compare_files.topLevelItem(idx)
            item.setIcon(0, icon)
        # Throw the selected SHA-1 into the clipboard
        qtutils.set_clipboard(self.model.param(revision_param))

    def compare_selected_file(self):
        """Compares the currently selected file
        """
        # When a filename was provided in the constructor then we
        # simply compare that file
        if self.filename:
            self._compare_file(self.filename)
            return
        # Otherwise, use the selection to choose the compared file
        tree_widget = self.view.compare_files
        id_num, selected = qtutils.selected_treeitem(tree_widget)
        if not selected:
            qtutils.information('Oops!', 'Please select a file to compare')
            return
        filename = self.model.compare_files[id_num]
        self._compare_file(filename)

    def compare_files_doubleclick(self, tree_item, column):
        """Compares a file when it is double-clicked
        """
        # Assumes the listwidget's indexes matches the model's index
        idx = self.view.compare_files.indexOfTopLevelItem(tree_item)
        filename = self.model.compare_files[idx]
        self._compare_file(filename)

    def _compare_file(self, filename):
        """Initiates a difftool session for a single file
        """
        arg = '%s..%s' % (self.model.revision_start,
                          self.model.revision_end)
        difftool.launch([arg, '--', filename])
