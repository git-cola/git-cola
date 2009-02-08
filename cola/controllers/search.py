#!/usr/bin/env python
"""This controller handles the search dialog."""


import os
import re
import time
from PyQt4 import QtGui

from cola.observer import Observer
from cola.qobserver import QObserver
from cola.views import SearchView
from cola import qtutils


class SearchEngine(object):
    def __init__(self, model):
        self.model = model
    def get_rev_args(self):
        max = self.model.get_max_results()
        return { 'max-count': max, 'pretty': 'format:%H %aN - %s - %ar' }
    def get_common_args(self):
        return (self.model.get_input(), self.get_rev_args())
    def search(self):
        if not self.validate():
            return
        return self.get_results()
    def validate(self):
        return len(self.model.get_input()) > 1
    def get_revisions(self, *args, **kwargs):
        revlist = self.model.git.log(*args, **kwargs)
        return self.model.parse_rev_list(revlist)
    def get_results(self):
        pass

class RevisionSearch(SearchEngine):
    def get_results(self):
        input, args = self.get_common_args()
        expr = re.compile(input)
        revs = self.get_revisions(all=True, **args)
        return [ r for r in revs if expr.match(r[0]) ]

class RevisionRangeSearch(SearchEngine):
    def __init__(self, model):
        SearchEngine.__init__(self, model)
        self.RE = re.compile(r'[^.]*\.\..*')
    def validate(self):
        return bool(self.RE.match(self.model.get_input()))
    def get_results(self):
        input, kwargs = self.get_common_args()
        return self.get_revisions(input, **kwargs)

class PathSearch(SearchEngine):
    def get_results(self):
        input, args = self.get_common_args()
        paths = ['--'] + input.split(':')
        return self.get_revisions(all=True, *paths, **args)

class MessageSearch(SearchEngine):
    def get_results(self):
        input, kwargs = self.get_common_args()
        return self.get_revisions(all=True, grep=input, **kwargs)

class AuthorSearch(SearchEngine):
    def get_results(self):
        input, kwargs = self.get_common_args()
        return self.get_revisions(all=True, author=input, **kwargs)

class CommitterSearch(SearchEngine):
    def get_results(self):
        input, kwargs = self.get_common_args()
        return self.get_revisions(all=True, committer=input, **kwargs)

class DiffSearch(SearchEngine):
    def get_results(self):
        input, kwargs = self.get_common_args()
        return self.model.parse_rev_list(
            self.model.git.log('-S'+input, all=True, **kwargs))

class DateRangeSearch(SearchEngine):
    def validate(self):
        return True
    def get_results(self):
        kwargs = self.get_rev_args()
        start_date = self.model.get_start_date()
        end_date = self.model.get_end_date()
        return self.get_revisions(date='iso',
                                  all=True,
                                  after=start_date,
                                  before=end_date,
                                  **kwargs)

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
        self.add_observables('input',
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
        font = self.model.get_cola_config('fontui')
        if font:
            qfont = QtGui.QFont()
            qfont.fromString(font)
            self.view.commit_list.setFont(qfont)
        font = self.model.get_cola_config('fontdiff')
        if font:
            qfont = QtGui.QFont()
            qfont.fromString(font)
            self.view.commit_text.setFont(qfont)

    def set_mode(self, mode):
        radio = getattr(self.view, mode)
        radio.setChecked(True)

    def radio_to_mode(self, radio_button):
        return str(radio_button.objectName())

    def get_mode(self):
        for name in SEARCH_ENGINES:
            radiobutton = getattr(self.view, name)
            if radiobutton.isChecked():
                return name

    def search_callback(self, *args):
        engineclass = SEARCH_ENGINES.get(self.get_mode())
        if not engineclass:
            print ("mode: '%s' is currently unimplemented"
                   % self.get_mode())
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
        input = ':'.join(filepaths)
        self.model.set_input('')
        self.set_mode(PATH)
        self.model.set_input(input)

    def display_results(self):
        commit_list = map(lambda x: x[1], self.results)
        self.model.set_commit_list(commit_list)
        qtutils.set_listwidget_strings(self.view.commit_list, commit_list)

    def display_callback(self, *args):
        widget = self.view.commit_list
        row, selected = qtutils.get_selected_row(widget)
        if not selected or len(self.results) < row:
            return
        revision = self.results[row][0]
        qtutils.set_clipboard(revision)
        diff = self.model.get_commit_diff(revision)
        self.view.commit_text.setText(diff)

    def export_patch(self):
        widget = self.view.commit_list
        row, selected = qtutils.get_selected_row(widget)
        if not selected or len(self.results) < row:
            return
        revision = self.results[row][0]
        qtutils.log(self.model.export_patchset(revision, revision),
                    doraise=True,
                    quiet=False)

    def cherry_pick(self):
        widget = self.view.commit_list
        row, selected = qtutils.get_selected_row(widget)
        if not selected or len(self.results) < row:
            return
        revision = self.results[row][0]
        qtutils.log(self.model.git.cherry_pick(revision),
                    doraise=True,
                    quiet=False)

def search_commits(model, parent, mode, browse):
    def get_date(timespec):
        return '%04d-%02d-%02d' % time.localtime(timespec)[:3]

    # TODO subclass model for search only
    model = model.clone()
    model.input = ''
    model.max_results = 500
    model.start_date = ''
    model.end_date = ''
    model.commit_list = []

    view = SearchView(parent)
    ctl = SearchController(model, view)
    ctl.set_mode(mode)
    model.set_start_date(get_date(time.time()-(87640*7)))
    model.set_end_date(get_date(time.time()+87640))
    view.show()
    if browse:
        ctl.browse_callback()
