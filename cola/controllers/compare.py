"""This controller handles the compare commits dialog."""

import os

from cola import utils
from cola import qtutils
from cola.qobserver import QObserver
from cola.views import CompareView
from cola.views import BranchCompareView
from cola.controllers.repobrowser import select_file_from_repo
from cola.controllers.util import choose_from_list

def compare_file(model, parent):
    filename = select_file_from_repo(model, parent)
    if not filename:
        return
    compare(model, parent, filename)

def compare(model, parent, filename=None):
    model = model.clone()
    model.create(descriptions_start=[], descriptions_end=[],
                 revisions_start=[], revisions_end=[],
                 revision_start='', revision_end='',
                 compare_files=[], num_results=100,
                 show_versions=False)
    view = CompareView(parent)
    ctl = CompareController(model, view, filename)
    view.show()

def branch_compare(model, parent):
    model = model.clone()
    model.create(left_combo=['Local', 'Remote'],
                 right_combo=['Local', 'Remote'],
                 left_combo_index=0,
                 right_combo_index=1,
                 left_list=[],
                 right_list=[],
                 left_list_index=-1,
                 right_list_index=-1,
                 left_list_selected=False,
                 right_list_selected=False,
                 diff_files=[])
    view = BranchCompareView(parent)
    ctl = BranchCompareController(model, view)
    view.show()

class BranchCompareController(QObserver):
    BRANCH_POINT = '*** Branch Point ***'
    SANDBOX      = '*** Sandbox ***'

    def init(self, model, view):
        self.add_observables('left_combo', 'right_combo',
                             'left_list', 'right_list',
                             'diff_files')

        self.add_callbacks(button_compare =
                                self.diff_files_doubleclick,
                           left_combo =
                                self.gen_update_combo_boxes(left=True),
                           right_combo =
                                self.gen_update_combo_boxes(left=False),
                           left_list =
                                self.update_diff_files,
                           right_list =
                                self.update_diff_files)
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
        if (not self.model.has_param('left_list_item') or
                not self.model.has_param('right_list_item')):
            return
        left_item = self.model.get_left_list_item()
        right_item = self.model.get_right_list_item()
        if (not left_item or not right_item or
                left_item == right_item):
            self.model.set_diff_files([])
            return
        left_item = self.get_remote_ref(left_item)
        right_item = self.get_remote_ref(right_item)

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

        self.start = left_item
        self.end = right_item

        files = self.model.get_diff_filenames(self.diff_arg)
        self.model.set_diff_files(files)
        icon = qtutils.get_icon('script.png')
        for idx in xrange(0, self.view.diff_files.topLevelItemCount()):
            item = self.view.diff_files.topLevelItem(idx)
            item.setIcon(0, icon)

    def get_diff_arg(self, start, end):
        if start == BranchCompareController.SANDBOX:
            return end
        elif end == BranchCompareController.SANDBOX:
            return start
        else:
            return '%s..%s' % (start, end)

    def get_remote_ref(self, branch):
        if branch == BranchCompareController.BRANCH_POINT:
            # Compare against the branch point so find the merge-base
            branch = self.model.get_currentbranch()
            remote = self.model.get_corresponding_remote_ref()
            return self.model.git.merge_base(branch, remote)
        else:
            # Compare against the remote branch
            return branch


    def gen_update_combo_boxes(self, left=False):
        """Returns a closure which modifies the listwidgets based on the
        combobox selection.
        """
        def update_combo_boxes(notused):
            if left:
                which = self.model.get_left_combo_item()
                param = 'left_list'
            else:
                which = self.model.get_right_combo_item()
                param = 'right_list'
            if not which:
                return
            if which == 'Local':
                new_list = ([BranchCompareController.SANDBOX]+
                            self.model.get_local_branches())
            else:
                new_list = ([BranchCompareController.BRANCH_POINT] +
                            self.model.get_remote_branches())
            # Update the list widget
            self.model.set_notify(True)
            self.model.set_param(param, new_list)

        return update_combo_boxes

    def diff_files_doubleclick(self):
        tree_widget = self.view.diff_files
        id_num, selected = qtutils.get_selected_treeitem(tree_widget)
        if not selected:
            qtutils.information('Oops!', 'Please select a file to compare')
            return
        filename = self.model.get_diff_files()[id_num]
        self.__compare_file(filename)

    def __compare_file(self, filename):
        git = self.model.git
        args = git.transform_kwargs(no_prompt=True,
                                    tool=self.model.get_mergetool())
        if self.use_sandbox:
            args.append(self.diff_arg)
        else:
            args.append('%s..%s' % (self.start, self.end))

        command = (['perl', utils.get_libexec('git-difftool')] +
                   args + ['--', filename])
        utils.fork(*command)


class CompareController(QObserver):
    """Drives the Commit->Compare Commits dialog.
    """
    def init (self, model, view, filename=None):
        self.filename = filename
        if self.filename:
            self.view.compare_files.hide()

        self.add_observables('descriptions_start', 'descriptions_end',
                             'revision_start', 'revision_end',
                             'compare_files', 'num_results',
                             'show_versions')

        self.add_actions(num_results = self.update_results)
        self.add_actions(show_versions = self.update_results)

        self.add_callbacks(descriptions_start =
                                self.gen_update_widgets(True),
                           descriptions_end =
                                self.gen_update_widgets(False),
                           button_compare =
                                self.compare_selected_file)
        self.refresh_view()
        revisions = self.update_results()
        last = len(revisions)
        # if we can, preselect the latest commit
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

    def get_distance_from_end(self, tree_widget):
        item_id, item_selected = qtutils.get_selected_treeitem(tree_widget)
        if item_selected:
            item_count = tree_widget.topLevelItemCount()
            item_delta = item_count - item_id
            return (item_selected, item_delta)
        else:
            return (item_selected, 0)

    def select_nth_item_from_end(self, tree_widget, delta):
        """selects an item relative to the end of the treeitem list.
        We select from the end to properly handle changes in the number of
        displayed commits."""
        count = self.view.descriptions_start.topLevelItemCount()
        idx = count - delta
        qtutils.set_selected_item(tree_widget, idx)

    def update_results(self, *args):

        tree_widget = self.view.descriptions_start
        start_selected, start_delta = self.get_distance_from_end(tree_widget)

        tree_widget = self.view.descriptions_end
        end_selected, end_delta = self.get_distance_from_end(tree_widget)

        self.model.set_notify(True)
        show_versions = self.model.get_show_versions()
        revs = self.model.update_revision_lists(filename=self.filename,
                                                show_versions=show_versions)
        if start_selected:
            tree_widget = self.view.descriptions_start
            self.select_nth_item_from_end(tree_widget, start_delta)

        if end_selected:
            tree_widget = self.view.descriptions_end
            self.select_nth_item_from_end(tree_widget, end_delta)

        return revs

    def gen_update_widgets(self, left=True):
        def update(*args):
            self.update_widgets(left=left)
        return update

    def update_widgets(self, left=True):
        if left:
            tree_widget = self.view.descriptions_start
            revisions_param = 'revisions_start'
            revision_param = 'revision_start'
        else:
            tree_widget = self.view.descriptions_end
            revisions_param = 'revisions_end'
            revision_param = 'revision_end'

        id_num, selected = qtutils.get_selected_treeitem(tree_widget)
        if not selected:
            return

        revisionlist = self.model.get_param(revisions_param)
        if id_num < len(revisionlist):
            revision = self.model.get_param(revisions_param)[id_num]
            self.model.set_param(revision_param, revision)

        # get the changed files list
        start = self.model.get_revision_start()
        end = self.model.get_revision_end()
        files = self.model.get_changed_files(start, end)

        # get the old name of any renamed files, and prune them
        # from the changes list
        renamed_files = self.model.get_renamed_files(start, end)
        for renamed in renamed_files:
            try:
                files.remove(renamed)
            except:
                pass
        self.model.set_compare_files(files)
        icon = qtutils.get_icon('script.png')
        for idx in xrange(0, self.view.compare_files.topLevelItemCount()):
            item = self.view.compare_files.topLevelItem(idx)
            item.setIcon(0, icon)
        qtutils.set_clipboard(self.model.get_param(revision_param))

    def compare_selected_file(self):
        tree_widget = self.view.compare_files
        id_num, selected = qtutils.get_selected_treeitem(tree_widget)
        if not selected and not self.filename:
            qtutils.information('Oops!', 'Please select a file to compare')
            return
        filename = self.filename or self.model.get_compare_files()[id_num]
        self.__compare_file(filename)

    def compare_files_doubleclick(self, tree_item, column):
        idx = self.view.compare_files.indexOfTopLevelItem(tree_item)
        filename = self.model.get_compare_files()[idx]
        self.__compare_file(filename)

    def __compare_file(self, filename):
        git = self.model.git
        start = self.model.get_revision_start()
        end = self.model.get_revision_end()
        args = git.transform_kwargs(no_prompt=True,
                                    tool=self.model.get_mergetool())
        args.append('%s..%s' % (start, end))
        command = (['perl', utils.get_libexec('git-difftool')] +
                   args + ['--', filename])
        utils.fork(*command)
