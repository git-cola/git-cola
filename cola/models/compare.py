from cola import core
from cola import git
from cola import gitcmds
from cola.models import observable



class CompareModel(observable.ObservableModel):
    """Provides custom model data for CompareController."""
    def __init__(self):
        observable.ObservableModel.__init__(self)
        self.git = git.instance()
        self.descriptions_start = []
        self.descriptions_end = []
        self.revisions_start = []
        self.revisions_end = []
        self.revision_start = ''
        self.revision_end = ''
        self.compare_files = []
        self.num_results = 100
        self.show_versions=False

    def update_revision_lists(self, filename=None, show_versions=False):
        num_results = self.num_results
        if filename:
            rev_list = self.git.log('--', filename,
                                    max_count=num_results,
                                    no_color=True,
                                    pretty='oneline')
        else:
            rev_list = self.git.log(max_count=num_results,
                                    no_color=True,
                                    pretty='oneline', all=True)

        commit_list = gitcmds.parse_rev_list(rev_list)
        commit_list.reverse()
        commits = map(lambda x: x[0], commit_list)
        descriptions = map(lambda x: core.decode(x[1]), commit_list)
        if show_versions:
            fancy_descr_list = map(lambda x: self.describe(*x), commit_list)
            self.set_descriptions_start(fancy_descr_list)
            self.set_descriptions_end(fancy_descr_list)
        else:
            self.set_descriptions_start(descriptions)
            self.set_descriptions_end(descriptions)

        self.set_revisions_start(commits)
        self.set_revisions_end(commits)

        return commits

    def describe(self, revid, descr):
        version = self.git.describe(revid, tags=True, always=True,
                                    abbrev=4)
        return version + ' - ' + descr


class BranchCompareModel(observable.ObservableModel):
    """Provides custom model data for BranchCompareController."""
    def __init__(self):
        observable.ObservableModel.__init__(self)
        self.git = git.instance()
        self.remote_branches = gitcmds.branch_list(remote=True)
        self.local_branches = gitcmds.branch_list(remote=False)
        self.left_combo = ['Local', 'Remote']
        self.right_combo = ['Local', 'Remote']
        self.left_combo_index = 0
        self.right_combo_index = 1
        self.left_list = []
        self.right_list = []
        self.left_list_index = -1
        self.right_list_index = -1
        self.left_list_selected = False
        self.right_list_selected = False
        self.diff_files = []
