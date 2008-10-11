import os

from cola import utils
from cola import qtutils
from cola.qobserver import QObserver
from cola.views import CompareView
from cola.controllers.repobrowser import select_file_from_repo
from cola.controllers.util import choose_from_list

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

class CompareController(QObserver):
    def init (self, model, view, filename=None):
        self.filename = filename
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

        self.connect(self.view.compare_files,
                     'itemDoubleClicked(QTreeWidgetItem *, int)',
                     self.compare_revisions)

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
        qtutils.set_clipboard(self.model.get_param(revision_param))

    def compare_selected_file(self):
        tree_widget = self.view.compare_files
        id_num, selected = qtutils.get_selected_treeitem(tree_widget)
        if not selected:
            qtutils.information('Oops!', 'Please select a file to compare')
            return
        filename = self.model.get_compare_files()[id_num]
        self.__compare_file(filename)

    def compare_revisions(self, tree_item, column):
        idx = self.view.compare_files.indexOfTopLevelItem(tree_item)
        filename = self.model.get_compare_files()[idx]
        self.__compare_file(filename)

    def __compare_file(self, filename):
        git = self.model.git
        start = self.model.get_revision_start()
        end = self.model.get_revision_end()
        kwargs = git.transform_kwargs(no_prompt=True,
                                      tool=self.model.get_mergetool(),
                                      start=start,
                                      end=end)
        args = (['git', 'difftool'] + kwargs + ['--', filename])
        utils.fork(*args)
