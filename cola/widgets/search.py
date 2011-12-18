"""Provides the SearchView class."""
import os
import re
import time
import subprocess

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

from cola import gitcmds
from cola import utils
from cola import qtutils
from cola.git import git
from cola.prefs import diff_font
from cola.qt import DiffSyntaxHighlighter
from cola.qtutils import connect_button
from cola.views import standard
from cola.widgets import defs

REVISION_ID    = 'revision'
REVISION_RANGE = 'range'
PATH           = 'path'
MESSAGE        = 'message'
DIFF           = 'diff'
AUTHOR         = 'author'
COMMITTER      = 'committer'
DATE_RANGE     = 'daterange'


def mkdate(timespec):
    return '%04d-%02d-%02d' % time.localtime(timespec)[:3]


class SearchOptions(object):
    def __init__(self):
        self.query = ''
        self.max_results = 500
        self.start_date = ''
        self.end_date = ''


class SearchWidget(standard.Dialog):
    def __init__(self, parent):
        super(SearchWidget, self).__init__(parent)
        self.setWindowTitle(self.tr('Search'))
        self.main_layout = QtGui.QVBoxLayout()
        self.setLayout(self.main_layout)
        self.resize(600, self.parent().height())

        self.top_grid_layout = QtGui.QGridLayout()

        self.radio_range = QtGui.QRadioButton()
        self.radio_range.setText(self.tr('Revision Range Expression'))
        self.top_grid_layout.addWidget(self.radio_range, 0, 0, 1, 2)

        self.radio_path = QtGui.QRadioButton()
        self.radio_path.setText(self.tr('Commits Touching Paths'))
        self.top_grid_layout.addWidget(self.radio_path, 0, 2, 1, 1)

        self.radio_author = QtGui.QRadioButton()
        self.radio_author.setText(self.tr('Author'))
        self.top_grid_layout.addWidget(self.radio_author, 0, 3, 1, 1)

        self.radio_committer = QtGui.QRadioButton()
        self.radio_committer.setText(self.tr('Committer'))
        self.top_grid_layout.addWidget(self.radio_committer, 0, 4, 1, 1)

        self.radio_revision = QtGui.QRadioButton()
        self.radio_revision.setText(self.tr('Revision ID'))
        self.top_grid_layout.addWidget(self.radio_revision, 1, 0, 1, 2)

        self.radio_message = QtGui.QRadioButton()
        self.radio_message.setText(self.tr('Commit Messages'))
        self.top_grid_layout.addWidget(self.radio_message, 1, 2, 1, 1)

        self.radio_daterange = QtGui.QRadioButton()
        self.radio_daterange.setText(self.tr('Date Range (Start / End)'))
        self.top_grid_layout.addWidget(self.radio_daterange, 1, 3, 1, 2)

        self.maxresults_label = QtGui.QLabel()
        self.maxresults_label.setText(self.tr('Max Results'))
        self.top_grid_layout.addWidget(self.maxresults_label, 2, 0, 1, 1)

        self.max_results = QtGui.QSpinBox()
        self.max_results.setMinimum(5)
        self.max_results.setMaximum(9995)
        self.max_results.setSingleStep(5)
        self.max_results.setProperty('value', QtCore.QVariant(500))
        self.top_grid_layout.addWidget(self.max_results, 2, 1, 1, 1)

        self.radio_diff = QtGui.QRadioButton()
        self.radio_diff.setText(self.tr('Diff Content'))
        self.top_grid_layout.addWidget(self.radio_diff, 2, 2, 1, 1)

        self.start_date = QtGui.QDateEdit()
        self.start_date.setCurrentSection(QtGui.QDateTimeEdit.YearSection)
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat(self.tr('yyyy-MM-dd'))
        self.top_grid_layout.addWidget(self.start_date, 2, 3, 1, 1)

        self.end_date = QtGui.QDateEdit()
        self.end_date.setCurrentSection(QtGui.QDateTimeEdit.YearSection)
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat(self.tr('yyyy-MM-dd'))
        self.top_grid_layout.addWidget(self.end_date, 2, 4, 1, 1)

        self.button_search = QtGui.QPushButton()
        self.button_search.setText(self.tr('Search'))
        self.button_search.setShortcut(self.tr('Return'))
        self.top_grid_layout.addWidget(self.button_search, 3, 0, 1, 1)

        self.query = QtGui.QLineEdit()
        self.top_grid_layout.addWidget(self.query, 3, 1, 1, 3)

        self.button_browse = QtGui.QPushButton()
        self.button_browse.setText(self.tr('Browse'))
        self.top_grid_layout.addWidget(self.button_browse, 3, 4, 1, 1)
        self.main_layout.addLayout(self.top_grid_layout)

        self.splitter = QtGui.QSplitter()
        self.splitter.setHandleWidth(defs.handle_width)
        self.splitter.setOrientation(QtCore.Qt.Vertical)

        self.commit_list = QtGui.QListWidget(self.splitter)
        self.commit_list.setMinimumSize(QtCore.QSize(1, 1))
        self.commit_list.setAlternatingRowColors(True)
        self.commit_list.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)

        self.commit_text = QtGui.QTextEdit(self.splitter)
        self.commit_text.setMinimumSize(QtCore.QSize(1, 1))
        self.commit_text.setTabChangesFocus(True)
        self.commit_text.setReadOnly(True)
        self.commit_text.setAcceptRichText(False)
        self.commit_text.setFont(diff_font())
        self._syntax = DiffSyntaxHighlighter(self.commit_text.document(),
                                             whitespace=False)
        self.main_layout.addWidget(self.splitter)

        self._button_grid_layt = QtGui.QGridLayout()

        self.button_export = QtGui.QPushButton()
        self.button_export.setText(self.tr('Export Patches'))
        self._button_grid_layt.addWidget(self.button_export, 0, 0, 1, 1)

        self.button_cherrypick = QtGui.QPushButton()
        self.button_cherrypick.setText(self.tr('Cherry Pick'))
        self._button_grid_layt.addWidget(self.button_cherrypick, 0, 1, 1, 1)

        self._button_spacer = QtGui.QSpacerItem(111, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self._button_grid_layt.addItem(self._button_spacer, 0, 2, 1, 1)

        self.button_close = QtGui.QPushButton()
        self.button_close.setText(self.tr('Close'))
        self._button_grid_layt.addWidget(self.button_close, 0, 3, 1, 1)
        self.main_layout.addLayout(self._button_grid_layt)


def search():
    """Return a callback to handle various search actions."""
    search_commits(qtutils.active_window())


class SearchEngine(object):
    def __init__(self, model):
        self.model = model

    def rev_args(self):
        max_count = self.model.max_results
        return {
            'no_color': True,
            'max-count': max_count,
            'pretty': 'format:%H %aN - %s - %ar',
        }

    def common_args(self):
        return (self.model.query, self.rev_args())

    def search(self):
        if not self.validate():
            return
        return self.results()

    def validate(self):
        return len(self.model.query) > 1

    def revisions(self, *args, **kwargs):
        revlist = git.log(*args, **kwargs)
        return gitcmds.parse_rev_list(revlist)

    def results(self):
        pass

class RevisionSearch(SearchEngine):
    def results(self):
        query, args = self.common_args()
        expr = re.compile(query)
        revs = self.revisions(all=True, **args)
        return [r for r in revs if expr.match(r[0])]

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
        paths = ['--'] + utils.shell_split(query)
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
        return gitcmds.parse_rev_list(
            git.log('-S'+query, all=True, **kwargs))


class DateRangeSearch(SearchEngine):
    def validate(self):
        return self.model.start_date < self.model.end_date

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

class Search(SearchWidget):
    def __init__(self, model, parent):
        super(Search, self).__init__(parent)
        self.model = model
        self.radiobuttons = {
                REVISION_ID: self.radio_revision,
                REVISION_RANGE: self.radio_range,
                PATH: self.radio_path,
                MESSAGE: self.radio_message,
                DIFF: self.radio_diff,
                AUTHOR: self.radio_author,
                COMMITTER: self.radio_committer,
                DATE_RANGE: self.radio_daterange,
        }

        self.radiobuttons_to_mode = {}
        for k, v in self.radiobuttons.items():
            self.radiobuttons_to_mode[v] = k

        connect_button(self.button_search, self.search_callback)
        connect_button(self.button_browse, self.browse_callback)
        connect_button(self.button_export, self.export_patch)
        connect_button(self.button_cherrypick, self.cherry_pick)
        connect_button(self.button_close, self.accept)

        self.connect(self.commit_list,
                     SIGNAL('itemSelectionChanged()'),
                     self.display)

        self.set_start_date(mkdate(time.time()-(87640*31)))
        self.set_end_date(mkdate(time.time()+87640))
        self.set_mode(REVISION_ID)

        self.query.setFocus()

    def set_commit_list(self, commits):
        widget = self.commit_list
        widget.clear()
        widget.addItems(commits)

    def set_start_date(self, datestr):
        self.set_date(self.start_date, datestr)

    def set_end_date(self, datestr):
        self.set_date(self.end_date, datestr)

    def set_date(self, widget, datestr):
        fmt = QtCore.Qt.ISODate
        date = QtCore.QDate.fromString(datestr, fmt)
        if date:
            widget.setDate(date)

    def set_mode(self, mode):
        radio = self.radiobuttons[mode]
        radio.setChecked(True)

    def mode(self):
        for radio, mode in self.radiobuttons_to_mode.items():
            if radio.isChecked():
                return mode
        return REVISION_ID

    def search_callback(self, *args):
        engineclass = SEARCH_ENGINES[self.mode()]
        self.model.query = unicode(self.query.text())
        self.model.max_results = self.max_results.value()

        fmt = QtCore.Qt.ISODate
        self.model.start_date = str(self.start_date.date().toString(fmt))
        self.model.end_date = str(self.end_date.date().toString(fmt))

        self.results = engineclass(self.model).search()
        if self.results:
            self.display_results()
        else:
            self.commit_list.clear()
            self.commit_text.setText('')

    def browse_callback(self):
        paths = QtGui.QFileDialog.getOpenFileNames(self,
                                                   self.tr("Choose Path(s)"))
        if not paths:
            return
        filepaths = []
        lenprefix = len(os.getcwd()) + 1
        for path in map(lambda x: unicode(x), paths):
            if not path.startswith(os.getcwd()):
                continue
            filepaths.append(path[lenprefix:])
        query = subprocess.list2cmdline(filepaths)
        self.set_mode(PATH)
        self.query.setText(query)

    def display_results(self):
        commit_list = map(lambda x: x[1], self.results)
        self.set_commit_list(commit_list)

    def display(self, *args):
        widget = self.commit_list
        row, selected = qtutils.selected_row(widget)
        if not selected or len(self.results) < row:
            self.commit_text.setText('')
            return
        revision = self.results[row][0]
        qtutils.set_clipboard(revision)
        diff = gitcmds.commit_diff(revision)
        self.commit_text.setText(diff)

    def export_patch(self):
        widget = self.commit_list
        row, selected = qtutils.selected_row(widget)
        if not selected or len(self.results) < row:
            return
        revision = self.results[row][0]
        qtutils.log(*self.model.export_patchset(revision, revision))

    def cherry_pick(self):
        widget = self.commit_list
        row, selected = qtutils.selected_row(widget)
        if not selected or len(self.results) < row:
            return
        revision = self.results[row][0]
        qtutils.log(*git.cherry_pick(revision,
                                     with_stderr=True,
                                     with_status=True))

def search_commits(parent):
    opts = SearchOptions()
    widget = Search(opts, parent)
    widget.show()



if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    search = Search()
    search.show()
    sys.exit(app.exec_())
