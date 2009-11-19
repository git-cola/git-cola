"""This controller handles the search dialog."""


import os
import re
import time
from PyQt4 import QtGui

import cola
from cola import gitcmds
from cola import qtutils
from cola.qobserver import QObserver
from cola.models.search import SearchModel
from cola.views.search import SearchView

# Modes for this controller.
# Note: names correspond to radio button names for convenience
REVISION_ID    = 'radio_revision'
REVISION_RANGE = 'radio_range'
PATH           = 'radio_path'
MESSAGE        = 'radio_message'
DIFF           = 'radio_diff'
AUTHOR         = 'radio_author'
COMMITTER      = 'radio_committer'
DATE_RANGE     = 'radio_daterange'


def search(searchtype, browse=False):
    """Return a callback to handle various search actions."""
    def search_handler():
        search_commits(cola.model(),
                       QtGui.QApplication.instance().activeWindow(),
                       searchtype,
                       browse)
    return search_handler


class SearchEngine(object):
    def __init__(self, model):
        self.model = model

    def rev_args(self):
        max = self.model.max_results
        return { 'max-count': max, 'pretty': 'format:%H %aN - %s - %ar' }

    def common_args(self):
        return (self.model.query, self.rev_args())

    def search(self):
        if not self.validate():
            return
        return self.results()

    def validate(self):
        return len(self.model.query) > 1

    def revisions(self, *args, **kwargs):
        revlist = self.model.git.log(*args, **kwargs)
        return self.model.parse_rev_list(revlist)

    def results(self):
        pass

class RevisionSearch(SearchEngine):
    def results(self):
        query, args = self.common_args()
        expr = re.compile(query)
        revs = self.revisions(all=True, **args)
        return [ r for r in revs if expr.match(r[0]) ]

class RevisionRangeSearch(SearchEngine):
    def __init__(self, model):
        SearchEngine.__init__(self, model)
        self.RE = re.compile(r'[^.]*\.\..*')
    def validate(self):
        return bool(self.RE.match(self.model.query))
    def results(self):
        query, kwargs = self.common_args()
        return self.revisions(query, **kwargs)

class PathSearch(SearchEngine):
    def results(self):
        query, args = self.common_args()
        paths = ['--'] + query.split(':')
        return self.revisions(all=True, *paths, **args)

class MessageSearch(SearchEngine):
    def results(self):
        query, kwargs = self.common_args()
        return self.revisions(all=True, grep=query, **kwargs)

class AuthorSearch(SearchEngine):
    def results(self):
        query, kwargs = self.common_args()
        return self.revisions(all=True, author=query, **kwargs)

class CommitterSearch(SearchEngine):
    def results(self):
        query, kwargs = self.common_args()
        return self.revisions(all=True, committer=query, **kwargs)

class DiffSearch(SearchEngine):
    def results(self):
        query, kwargs = self.common_args()
        return self.model.parse_rev_list(
            self.model.git.log('-S'+query, all=True, **kwargs))

class DateRangeSearch(SearchEngine):
    def validate(self):
        return True
    def results(self):
        kwargs = self.rev_args()
        start_date = self.model.start_date
        end_date = self.model.end_date
        return self.revisions(date='iso',
                              all=True,
                              after=start_date,
                              before=end_date,
                              **kwargs)

# Each search type is handled by a distinct SearchEngine subclass
SEARCH_ENGINES = {
    REVISION_ID:    RevisionSearch,
    REVISION_RANGE: RevisionRangeSearch,
    PATH:           PathSearch,
    MESSAGE:        MessageSearch,
    DIFF:           DiffSearch,
    AUTHOR:         AuthorSearch,
    COMMITTER:      CommitterSearch,
    DATE_RANGE:     DateRangeSearch,
}

class SearchController(QObserver):
    def __init__(self, model, view):
        QObserver.__init__(self, model, view)
        self.add_observables('query',
                             'max_results',
                             'start_date',
                             'end_date')
        self.add_actions(max_results = self.search_callback,
                         start_date = self.search_callback,
                         end_date = self.search_callback)
        self.add_callbacks(
            # Standard buttons
            button_search     = self.search_callback,
            button_browse     = self.browse_callback,
            commit_list       = self.display_callback,
            button_export     = self.export_patch,
            button_cherrypick = self.cherry_pick,

            # Radio buttons trigger a search
            radio_revision  = self.search_callback,
            radio_range     = self.search_callback,
            radio_message   = self.search_callback,
            radio_path      = self.search_callback,
            radio_diff      = self.search_callback,
            radio_author    = self.search_callback,
            radio_committer = self.search_callback,
            radio_daterange = self.search_callback,
            )
        self.update_fonts()

    def update_fonts(self):
        font = self.model.cola_config('fontdiff')
        if font:
            qfont = QtGui.QFont()
            qfont.fromString(font)
            self.view.commit_text.setFont(qfont)

    def set_mode(self, mode):
        radio = getattr(self.view, mode)
        radio.setChecked(True)

    def radio_to_mode(self, radio_button):
        return str(radio_button.objectName())

    def mode(self):
        for name in SEARCH_ENGINES:
            radiobutton = getattr(self.view, name)
            if radiobutton.isChecked():
                return name

    def search_callback(self, *args):
        engineclass = SEARCH_ENGINES.get(self.mode())
        if not engineclass:
            print "mode: '%s' is currently unimplemented" % self.mode()
            return
        self.results = engineclass(self.model).search()
        if self.results:
            self.display_results()
        else:
            self.view.commit_list.clear()
            self.view.commit_text.setText('')

    def browse_callback(self):
        paths = QtGui.QFileDialog.getOpenFileNames(self.view,
                                                   self.tr("Choose Path(s)"))
        if not paths:
            return
        filepaths = []
        lenprefix = len(os.getcwd()) + 1
        for path in map(lambda x: unicode(x), paths):
            if not path.startswith(os.getcwd()):
                continue
            filepaths.append(path[lenprefix:])
        query = ':'.join(filepaths)
        self.model.set_query('')
        self.set_mode(PATH)
        self.model.set_query(query)

    def display_results(self):
        commit_list = map(lambda x: x[1], self.results)
        self.model.set_commit_list(commit_list)
        qtutils.set_listwidget_strings(self.view.commit_list, commit_list)

    def display_callback(self, *args):
        widget = self.view.commit_list
        row, selected = qtutils.selected_row(widget)
        if not selected or len(self.results) < row:
            return
        revision = self.results[row][0]
        qtutils.set_clipboard(revision)
        diff = gitcmds.commit_diff(revision)
        self.view.commit_text.setText(diff)

    def export_patch(self):
        widget = self.view.commit_list
        row, selected = qtutils.selected_row(widget)
        if not selected or len(self.results) < row:
            return
        revision = self.results[row][0]
        qtutils.log(*self.model.export_patchset(revision, revision))

    def cherry_pick(self):
        widget = self.view.commit_list
        row, selected = qtutils.selected_row(widget)
        if not selected or len(self.results) < row:
            return
        revision = self.results[row][0]
        qtutils.log(*self.model.git.cherry_pick(revision,
                                                with_stderr=True,
                                                with_status=True))

def search_commits(model, parent, mode, browse):
    def date(timespec):
        return '%04d-%02d-%02d' % time.localtime(timespec)[:3]

    # TODO subclass model for search only
    model = SearchModel(cwd=model.git.worktree())
    view = SearchView(parent)
    ctl = SearchController(model, view)
    ctl.set_mode(mode)
    model.set_start_date(date(time.time()-(87640*7)))
    model.set_end_date(date(time.time()+87640))
    view.show()
    if browse:
        ctl.browse_callback()
