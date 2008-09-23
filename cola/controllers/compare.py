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
                 display_text='', num_results=200)
    view = CompareView(parent)
    ctl = CompareController(model, view, filename)
    view.show()

class CompareController(QObserver):
    def init (self, model, view, filename=None):
        self.filename = filename
        self.add_observables('descriptions_start', 'descriptions_end',
                             'revision_start', 'revision_end',
                             'display_text', 'num_results')

        self.add_actions(num_results = self.update_results)

        self.add_callbacks(button_compare = self.compare_revisions,
                           descriptions_start =
                                self.gen_update_widgets(True),
                           descriptions_end =
                                self.gen_update_widgets(False))
        self.update_model()

    def update_model(self, *args):
        num_results = self.model.get_num_results()
        if self.filename:
            rev_list = self.model.git.log('--', self.filename,
                                          max_count=num_results,
                                          pretty='oneline')
        else:
            rev_list = self.model.git.log(max_count=num_results,
                                          pretty='oneline', all=True)

        commit_list = self.model.parse_rev_list(rev_list)
        commits = map(lambda x: x[0], commit_list)
        descriptions = map(lambda x: x[1], commit_list)

        self.model.set_descriptions_start(descriptions)
        self.model.set_descriptions_end(descriptions)

        self.model.set_revisions_start(commits)
        self.model.set_revisions_end(commits)

    def update_results(self, *args):
        self.model.set_notify(True)
        self.update_model()

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
        start = self.model.get_revision_start()
        end = self.model.get_revision_end()
        if not start or not end:
            qtutils.information('Error: Please select two revisions.')
            return
        zfiles_str = self.model.git.diff('%s..%s' % (start, end),
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

        git = self.model.git
        status, output, err = git.difftool('--', filename,
                                           no_prompt=True,
                                           tool=self.model.get_mergetool(),
                                           start=start, end=end,
                                           with_extended_output=True)
        qtutils.log(output+os.linesep+err)
        if status != 0 and output:
            qtutils.information('Oops!', output)
