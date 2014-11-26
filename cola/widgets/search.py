"""A widget for searching git commits"""
from __future__ import division, absolute_import, unicode_literals

import time
import subprocess

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import gitcmds
from cola import utils
from cola import qtutils
from cola.i18n import N_
from cola.interaction import Interaction
from cola.git import git
from cola.git import STDOUT
from cola.qtutils import connect_button
from cola.qtutils import create_toolbutton
from cola.qtutils import dir_icon
from cola.widgets import defs
from cola.widgets import standard
from cola.widgets.diff import DiffTextEdit
from cola.compat import ustr


def mkdate(timespec):
    return '%04d-%02d-%02d' % time.localtime(timespec)[:3]


class SearchOptions(object):
    def __init__(self):
        self.query = ''
        self.max_count = 500
        self.start_date = ''
        self.end_date = ''


class SearchWidget(standard.Dialog):
    def __init__(self, parent):
        standard.Dialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowTitle(N_('Search'))

        self.mode_combo = QtGui.QComboBox()
        self.browse_button = create_toolbutton(icon=dir_icon(),
                                               tooltip=N_('Browse...'))
        self.query = QtGui.QLineEdit()

        self.start_date = QtGui.QDateEdit()
        self.start_date.setCurrentSection(QtGui.QDateTimeEdit.YearSection)
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat(N_('yyyy-MM-dd'))

        self.end_date = QtGui.QDateEdit()
        self.end_date.setCurrentSection(QtGui.QDateTimeEdit.YearSection)
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat(N_('yyyy-MM-dd'))

        self.search_button = QtGui.QPushButton()
        self.search_button.setText(N_('Search'))
        self.search_button.setDefault(True)

        self.max_count = QtGui.QSpinBox()
        self.max_count.setMinimum(5)
        self.max_count.setMaximum(9995)
        self.max_count.setSingleStep(5)
        self.max_count.setValue(500)

        self.commit_list = QtGui.QListWidget()
        self.commit_list.setMinimumSize(QtCore.QSize(1, 1))
        self.commit_list.setAlternatingRowColors(True)
        self.commit_list.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)

        self.commit_text = DiffTextEdit(self, whitespace=False)

        self.button_export = QtGui.QPushButton()
        self.button_export.setText(N_('Export Patches'))

        self.button_cherrypick = QtGui.QPushButton()
        self.button_cherrypick.setText(N_('Cherry Pick'))

        self.button_close = QtGui.QPushButton()
        self.button_close.setText(N_('Close'))

        self.top_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                       self.query, self.start_date,
                                       self.end_date, self.browse_button,
                                       self.search_button, qtutils.STRETCH,
                                       self.mode_combo, self.max_count)

        self.splitter = qtutils.splitter(Qt.Vertical,
                                         self.commit_list, self.commit_text)

        self.bottom_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                          self.button_export,
                                          self.button_cherrypick,
                                          qtutils.STRETCH, self.button_close)

        self.main_layout = qtutils.vbox(defs.margin, defs.spacing,
                                        self.top_layout, self.splitter,
                                        self.bottom_layout)
        self.setLayout(self.main_layout)

        if self.parent():
            self.resize(self.parent().width(), self.parent().height())
        else:
            self.resize(720, 500)


def search():
    """Return a callback to handle various search actions."""
    return search_commits(qtutils.active_window())


class SearchEngine(object):
    def __init__(self, model):
        self.model = model

    def rev_args(self):
        max_count = self.model.max_count
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
        revlist = git.log(*args, **kwargs)[STDOUT]
        return gitcmds.parse_rev_list(revlist)

    def results(self):
        pass

class RevisionSearch(SearchEngine):
    def results(self):
        query, opts = self.common_args()
        args = utils.shell_split(query)
        return self.revisions(all=True, *args, **opts)


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
            git.log('-S'+query, all=True, **kwargs)[STDOUT])


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


class Search(SearchWidget):

    def __init__(self, model, parent):
        SearchWidget.__init__(self, parent)
        self.model = model

        self.EXPR = N_('Search by Expression')
        self.PATH = N_('Search by Path')
        self.MESSAGE = N_('Search Commit Messages')
        self.DIFF = N_('Search Diffs')
        self.AUTHOR = N_('Search Authors')
        self.COMMITTER = N_('Search Committers')
        self.DATE_RANGE = N_('Search Date Range')

        # Each search type is handled by a distinct SearchEngine subclass
        self.engines = {
            self.EXPR: RevisionSearch,
            self.PATH: PathSearch,
            self.MESSAGE: MessageSearch,
            self.DIFF: DiffSearch,
            self.AUTHOR: AuthorSearch,
            self.COMMITTER: CommitterSearch,
            self.DATE_RANGE: DateRangeSearch,
        }

        self.modes = (self.EXPR, self.PATH, self.DATE_RANGE,
                      self.DIFF, self.MESSAGE, self.AUTHOR, self.COMMITTER)
        self.mode_combo.addItems(self.modes)

        connect_button(self.search_button, self.search_callback)
        connect_button(self.browse_button, self.browse_callback)
        connect_button(self.button_export, self.export_patch)
        connect_button(self.button_cherrypick, self.cherry_pick)
        connect_button(self.button_close, self.accept)

        self.connect(self.mode_combo, SIGNAL('currentIndexChanged(int)'),
                     self.mode_index_changed)

        self.connect(self.commit_list,
                     SIGNAL('itemSelectionChanged()'),
                     self.display)

        self.set_start_date(mkdate(time.time()-(87640*31)))
        self.set_end_date(mkdate(time.time()+87640))
        self.set_mode(self.EXPR)

        self.query.setFocus()

    def mode_index_changed(self, idx):
        mode = self.mode()
        self.update_shown_widgets(mode)
        if mode == self.PATH:
            self.browse_callback()

    def set_commit_list(self, commits):
        widget = self.commit_list
        widget.clear()
        widget.addItems(commits)

    def set_start_date(self, datestr):
        self.set_date(self.start_date, datestr)

    def set_end_date(self, datestr):
        self.set_date(self.end_date, datestr)

    def set_date(self, widget, datestr):
        fmt = Qt.ISODate
        date = QtCore.QDate.fromString(datestr, fmt)
        if date:
            widget.setDate(date)

    def set_mode(self, mode):
        idx = self.modes.index(mode)
        self.mode_combo.setCurrentIndex(idx)
        self.update_shown_widgets(mode)

    def update_shown_widgets(self, mode):
        date_shown = mode == self.DATE_RANGE
        browse_shown = mode == self.PATH
        self.query.setVisible(not date_shown)
        self.browse_button.setVisible(browse_shown)
        self.start_date.setVisible(date_shown)
        self.end_date.setVisible(date_shown)

    def mode(self):
        return ustr(self.mode_combo.currentText())

    def search_callback(self, *args):
        engineclass = self.engines[self.mode()]
        self.model.query = ustr(self.query.text())
        self.model.max_count = self.max_count.value()

        fmt = Qt.ISODate
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
                                                   N_('Choose Path(s)'))
        if not paths:
            return
        filepaths = []
        lenprefix = len(core.getcwd()) + 1
        for path in map(lambda x: ustr(x), paths):
            if not path.startswith(core.getcwd()):
                continue
            filepaths.append(path[lenprefix:])
        query = subprocess.list2cmdline(filepaths)
        self.query.setText(query)
        if query:
            self.search_callback()

    def display_results(self):
        commit_list = [result[1] for result in self.results]
        self.set_commit_list(commit_list)

    def selected_revision(self):
        result = qtutils.selected_item(self.commit_list, self.results)
        if result is None:
            return None
        else:
            return result[0]

    def display(self, *args):
        revision = self.selected_revision()
        if revision is None:
            self.commit_text.setText('')
        else:
            qtutils.set_clipboard(revision)
            diff = gitcmds.commit_diff(revision)
            self.commit_text.setText(diff)

    def export_patch(self):
        revision = self.selected_revision()
        if revision is not None:
            Interaction.log_status(*gitcmds.export_patchset(revision,
                                                            revision))

    def cherry_pick(self):
        revision = self.selected_revision()
        if revision is not None:
            Interaction.log_status(*git.cherry_pick(revision))


def search_commits(parent):
    opts = SearchOptions()
    widget = Search(opts, parent)
    widget.show()
    return widget



if __name__ == '__main__':
    import sys
    app = QtGui.QApplication(sys.argv)
    search = Search()
    search.show()
    sys.exit(app.exec_())
