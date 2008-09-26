import os

from cola import utils
from cola import qtutils
from cola.qobserver import QObserver
from cola.views import CompareView
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
                 display_text='', num_results=96,
                 show_versions=False)
    view = CompareView(parent)
    ctl = CompareController(model, view, filename)
    view.show()

class CompareController(QObserver):
    def init (self, model, view, filename=None):
        self.filename = filename
        self.add_observables('descriptions_start', 'descriptions_end',
                             'revision_start', 'revision_end',
                             'display_text', 'num_results',
                             'show_versions')

        self.add_actions(num_results = self.update_results)
        self.add_actions(show_versions = self.update_results)

        self.add_callbacks(button_compare = self.compare_revisions,
                           descriptions_start =
                                self.gen_update_widgets(True),
                           descriptions_end =
                                self.gen_update_widgets(False))
        self.refresh_view()
        self.update_results()

    def update_results(self, *args):
        self.model.set_notify(True)
        show_versions = self.model.get_show_versions()
        self.model.update_revision_lists(filename=self.filename,
                                         show_versions=show_versions)

    def gen_update_widgets(self, left=True):
        def update(*args):
            self.update_widgets(left=left)
        return update

    def update_widgets(self, left=True):
        if left:
            list_widget = self.view.descriptions_start
            revisions_param = 'revisions_start'
            revision_param = 'revision_start'
        else:
            list_widget = self.view.descriptions_end
            revisions_param = 'revisions_end'
            revision_param = 'revision_end'
        row, selected = qtutils.get_selected_row(list_widget)
        if not selected:
            return
        revision = self.model.get_param(revisions_param)[row]
        self.model.set_param(revision_param, revision)

        if self.filename:
            revrange = '%s^..%s' % (revision, revision)
            log = self.model.git.log(revrange) + '\n\n'
            diff = log + self.model.git.diff(revrange, '--', self.filename)
        else:
            diff = self.model.get_commit_diff(revision)

        self.model.set_display_text(diff)
        qtutils.set_clipboard(self.model.get_param(revision_param))

    def compare_revisions(self):
        model = self.model
        git = model.git
        start = model.get_revision_start()
        end = model.get_revision_end()
        if not start or not end:
            qtutils.information('Error: Please select two revisions.')
            return
        zfiles_str = model.git.diff('%s..%s' % (start, end),
                                    name_only=True, z=True)
        if not zfiles_str:
            qtutils.information('Nothing to do',
                                'git-cola did not find any changes.')
            return

        if self.filename:
            filename = self.filename
        else:
            files = zfiles_str.split('\0')
            filename = choose_from_list('Select File', self.view, files)
            if not filename:
                return

        args = (['git', 'difftool']
                + git.transform_kwargs(no_prompt=True,
                                       tool=self.model.get_mergetool(),
                                       start=start, end=end)
                + ['--', filename])

        utils.fork(*args)
