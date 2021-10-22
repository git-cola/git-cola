"""A widget for searching git commits"""
from __future__ import absolute_import, division, print_function, unicode_literals
import time

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from ..i18n import N_
from ..interaction import Interaction
from ..git import STDOUT
from ..qtutils import connect_button
from ..qtutils import create_toolbutton
from ..qtutils import get
from .. import core
from .. import gitcmds
from .. import icons
from .. import utils
from .. import qtutils
from . import diff
from . import defs
from . import standard


def mkdate(timespec):
    return '%04d-%02d-%02d' % time.localtime(timespec)[:3]


class SearchOptions(object):
    def __init__(self):
        self.query = ''
        self.max_count = 500
        self.start_date = ''
        self.end_date = ''


class SearchWidget(standard.Dialog):
    def __init__(self, context, parent):
        standard.Dialog.__init__(self, parent)

        self.context = context
        self.setWindowTitle(N_('Search'))

        self.mode_combo = QtWidgets.QComboBox()
        self.browse_button = create_toolbutton(
            icon=icons.folder(), tooltip=N_('Browse...')
        )
        self.query = QtWidgets.QLineEdit()

        self.start_date = QtWidgets.QDateEdit()
        self.start_date.setCurrentSection(QtWidgets.QDateTimeEdit.YearSection)
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat(N_('yyyy-MM-dd'))

        self.end_date = QtWidgets.QDateEdit()
        self.end_date.setCurrentSection(QtWidgets.QDateTimeEdit.YearSection)
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat(N_('yyyy-MM-dd'))

        icon = icons.search()
        self.search_button = qtutils.create_button(
            text=N_('Search'), icon=icon, default=True
        )
        self.max_count = standard.SpinBox(value=500, mini=5, maxi=9995, step=5)

        self.commit_list = QtWidgets.QListWidget()
        self.commit_list.setMinimumSize(QtCore.QSize(10, 10))
        self.commit_list.setAlternatingRowColors(True)
        selection_mode = QtWidgets.QAbstractItemView.SingleSelection
        self.commit_list.setSelectionMode(selection_mode)

        self.commit_text = diff.DiffTextEdit(context, self, whitespace=False)

        self.button_export = qtutils.create_button(
            text=N_('Export Patches'), icon=icons.diff()
        )

        self.button_cherrypick = qtutils.create_button(
            text=N_('Cherry Pick'), icon=icons.cherry_pick()
        )
        self.button_close = qtutils.close_button()

        self.top_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.query,
            self.start_date,
            self.end_date,
            self.browse_button,
            self.search_button,
            qtutils.STRETCH,
            self.mode_combo,
            self.max_count,
        )

        self.splitter = qtutils.splitter(
            Qt.Vertical, self.commit_list, self.commit_text
        )

        self.bottom_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.button_close,
            qtutils.STRETCH,
            self.button_export,
            self.button_cherrypick,
        )

        self.main_layout = qtutils.vbox(
            defs.margin,
            defs.spacing,
            self.top_layout,
            self.splitter,
            self.bottom_layout,
        )
        self.setLayout(self.main_layout)

        self.init_size(parent=parent)


def search(context):
    """Return a callback to handle various search actions."""
    return search_commits(context, qtutils.active_window())


class SearchEngine(object):
    def __init__(self, context, model):
        self.context = context
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
        if self.validate():
            return self.results()
        return []

    def validate(self):
        return len(self.model.query) > 1

    def revisions(self, *args, **kwargs):
        git = self.context.git
        revlist = git.log(*args, **kwargs)[STDOUT]
        return gitcmds.parse_rev_list(revlist)

    def results(self):
        pass


class RevisionSearch(SearchEngine):
    def results(self):
        query, opts = self.common_args()
        args = utils.shell_split(query)
        return self.revisions(*args, **opts)


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
        git = self.context.git
        query, kwargs = self.common_args()
        return gitcmds.parse_rev_list(git.log('-S' + query, all=True, **kwargs)[STDOUT])


class DateRangeSearch(SearchEngine):
    def validate(self):
        return self.model.start_date < self.model.end_date

    def results(self):
        kwargs = self.rev_args()
        start_date = self.model.start_date
        end_date = self.model.end_date
        return self.revisions(
            date='iso', all=True, after=start_date, before=end_date, **kwargs
        )


class Search(SearchWidget):
    def __init__(self, context, model, parent):
        """
        Search diffs and commit logs

        :param model: SearchOptions instance

        """
        SearchWidget.__init__(self, context, parent)
        self.model = model

        self.EXPR = N_('Search by Expression')
        self.PATH = N_('Search by Path')
        self.MESSAGE = N_('Search Commit Messages')
        self.DIFF = N_('Search Diffs')
        self.AUTHOR = N_('Search Authors')
        self.COMMITTER = N_('Search Committers')
        self.DATE_RANGE = N_('Search Date Range')
        self.results = []

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

        self.modes = (
            self.EXPR,
            self.PATH,
            self.DATE_RANGE,
            self.DIFF,
            self.MESSAGE,
            self.AUTHOR,
            self.COMMITTER,
        )
        self.mode_combo.addItems(self.modes)

        connect_button(self.search_button, self.search_callback)
        connect_button(self.browse_button, self.browse_callback)
        connect_button(self.button_export, self.export_patch)
        connect_button(self.button_cherrypick, self.cherry_pick)
        connect_button(self.button_close, self.accept)

        # pylint: disable=no-member
        self.mode_combo.currentIndexChanged.connect(self.mode_changed)
        self.commit_list.itemSelectionChanged.connect(self.display)

        self.set_start_date(mkdate(time.time() - (87640 * 31)))
        self.set_end_date(mkdate(time.time() + 87640))
        self.set_mode(self.EXPR)

        self.query.setFocus()

    def mode_changed(self, _idx):
        mode = self.mode()
        self.update_shown_widgets(mode)
        if mode == self.PATH:
            self.browse_callback()

    def set_commits(self, commits):
        widget = self.commit_list
        widget.clear()
        widget.addItems(commits)

    def set_start_date(self, datestr):
        set_date(self.start_date, datestr)

    def set_end_date(self, datestr):
        set_date(self.end_date, datestr)

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
        return self.mode_combo.currentText()

    # pylint: disable=unused-argument
    def search_callback(self, *args):
        engineclass = self.engines[self.mode()]
        self.model.query = get(self.query)
        self.model.max_count = get(self.max_count)

        self.model.start_date = get(self.start_date)
        self.model.end_date = get(self.end_date)

        self.results = engineclass(self.context, self.model).search()
        if self.results:
            self.display_results()
        else:
            self.commit_list.clear()
            self.commit_text.setText('')

    def browse_callback(self):
        paths = qtutils.open_files(N_('Choose Paths'))
        if not paths:
            return
        filepaths = []
        curdir = core.getcwd()
        prefix_len = len(curdir) + 1
        for path in paths:
            if not path.startswith(curdir):
                continue
            relpath = path[prefix_len:]
            if relpath:
                filepaths.append(relpath)

        query = core.list2cmdline(filepaths)
        self.query.setText(query)
        if query:
            self.search_callback()

    def display_results(self):
        commits = [result[1] for result in self.results]
        self.set_commits(commits)

    def selected_revision(self):
        result = qtutils.selected_item(self.commit_list, self.results)
        return result[0] if result else None

    # pylint: disable=unused-argument
    def display(self, *args):
        context = self.context
        revision = self.selected_revision()
        if revision is None:
            self.commit_text.setText('')
        else:
            qtutils.set_clipboard(revision)
            diff_text = gitcmds.commit_diff(context, revision)
            self.commit_text.setText(diff_text)

    def export_patch(self):
        context = self.context
        revision = self.selected_revision()
        if revision is not None:
            Interaction.log_status(
                *gitcmds.export_patchset(context, revision, revision)
            )

    def cherry_pick(self):
        git = self.context.git
        revision = self.selected_revision()
        if revision is not None:
            Interaction.log_status(*git.cherry_pick(revision))


def set_date(widget, datestr):
    fmt = Qt.ISODate
    date = QtCore.QDate.fromString(datestr, fmt)
    if date:
        widget.setDate(date)


def search_commits(context, parent):
    opts = SearchOptions()
    widget = Search(context, opts, parent)
    widget.show()
    return widget
