"""Provides the SearchView class."""

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

from cola.prefs import diff_font
from cola.qt import DiffSyntaxHighlighter
from cola.views import standard
from cola.widgets import defs


class SearchView(standard.Dialog):
    def __init__(self, parent=None):
        standard.Dialog.__init__(self, parent=parent)

        self.setWindowTitle(self.tr('Search'))
        if self.parent():
            self.resize(600, self.parent().height())
        else:
            self.resize(600, 500)

        self._main_vbox_layt = QtGui.QVBoxLayout(self)
        self._top_grid_layt = QtGui.QGridLayout()
        # Exposed
        self.radio_range = QtGui.QRadioButton(self)
        self.radio_range.setText(self.tr('Revision Range Expression'))
        self._top_grid_layt.addWidget(self.radio_range, 0, 0, 1, 2)
        # Exposed
        self.radio_path = QtGui.QRadioButton(self)
        self.radio_path.setText(self.tr('Commits Touching Paths'))
        self._top_grid_layt.addWidget(self.radio_path, 0, 2, 1, 1)
        # Exposed
        self.radio_author = QtGui.QRadioButton(self)
        self.radio_author.setText(self.tr('Author'))
        self._top_grid_layt.addWidget(self.radio_author, 0, 3, 1, 1)
        # Exposed
        self.radio_committer = QtGui.QRadioButton(self)
        self.radio_committer.setText(self.tr('Committer'))
        self._top_grid_layt.addWidget(self.radio_committer, 0, 4, 1, 1)
        # Exposed
        self.radio_revision = QtGui.QRadioButton(self)
        self.radio_revision.setText(self.tr('Revision ID'))
        self._top_grid_layt.addWidget(self.radio_revision, 1, 0, 1, 2)
        # Exposed
        self.radio_message = QtGui.QRadioButton(self)
        self.radio_message.setText(self.tr('Commit Messages'))
        self._top_grid_layt.addWidget(self.radio_message, 1, 2, 1, 1)
        # Exposed
        self.radio_daterange = QtGui.QRadioButton(self)
        self.radio_daterange.setText(self.tr('Date Range (Start / End)'))
        self._top_grid_layt.addWidget(self.radio_daterange, 1, 3, 1, 2)
        # Exposed
        self.maxresults_label = QtGui.QLabel(self)
        self.maxresults_label.setText(self.tr('Max Results'))
        self._top_grid_layt.addWidget(self.maxresults_label, 2, 0, 1, 1)
        # Exposed
        self.max_results = QtGui.QSpinBox(self)
        self.max_results.setMinimum(5)
        self.max_results.setMaximum(9995)
        self.max_results.setSingleStep(5)
        self.max_results.setProperty("value", QtCore.QVariant(500))
        self._top_grid_layt.addWidget(self.max_results, 2, 1, 1, 1)
        # Exposed
        self.radio_diff = QtGui.QRadioButton(self)
        self.radio_diff.setText(self.tr('Diff Content'))
        self._top_grid_layt.addWidget(self.radio_diff, 2, 2, 1, 1)
        # Exposed
        self.start_date = QtGui.QDateEdit(self)
        self.start_date.setCurrentSection(QtGui.QDateTimeEdit.YearSection)
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat(self.tr('yyyy-MM-dd'))
        self._top_grid_layt.addWidget(self.start_date, 2, 3, 1, 1)
        # Exposed
        self.end_date = QtGui.QDateEdit(self)
        self.end_date.setCurrentSection(QtGui.QDateTimeEdit.YearSection)
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat(self.tr('yyyy-MM-dd'))
        self._top_grid_layt.addWidget(self.end_date, 2, 4, 1, 1)
        # Exposed
        self.button_search = QtGui.QPushButton(self)
        self.button_search.setText(self.tr('Search'))
        self.button_search.setShortcut(self.tr('Return'))
        self._top_grid_layt.addWidget(self.button_search, 3, 0, 1, 1)
        # Exposed
        self.query = QtGui.QLineEdit(self)
        self.query.setFocus()
        self._top_grid_layt.addWidget(self.query, 3, 1, 1, 3)
        # Exposed
        self.button_browse = QtGui.QPushButton(self)
        self.button_browse.setText(self.tr('Browse'))
        self._top_grid_layt.addWidget(self.button_browse, 3, 4, 1, 1)
        self._main_vbox_layt.addLayout(self._top_grid_layt)
        # Exposed
        self.splitter = QtGui.QSplitter(self)
        self.splitter.setHandleWidth(defs.handle_width)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        # Exposed
        self.commit_list = QtGui.QListWidget(self.splitter)
        self.commit_list.setMinimumSize(QtCore.QSize(1, 1))
        self.commit_list.setAlternatingRowColors(True)
        self.commit_list.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        # Exposed
        self.commit_text = QtGui.QTextEdit(self.splitter)
        self.commit_text.setMinimumSize(QtCore.QSize(1, 1))
        self.commit_text.setTabChangesFocus(True)
        self.commit_text.setReadOnly(True)
        self.commit_text.setAcceptRichText(False)
        self.commit_text.setFont(diff_font())
        self._syntax = DiffSyntaxHighlighter(self.commit_text.document(),
                                             whitespace=False)
        self._main_vbox_layt.addWidget(self.splitter)

        self._button_grid_layt = QtGui.QGridLayout()
        # Exposed
        self.button_export = QtGui.QPushButton(self)
        self.button_export.setText(self.tr('Export Patches'))
        self._button_grid_layt.addWidget(self.button_export, 0, 0, 1, 1)
        # Exposed
        self.button_cherrypick = QtGui.QPushButton(self)
        self.button_cherrypick.setText(self.tr('Cherry Pick'))
        self._button_grid_layt.addWidget(self.button_cherrypick, 0, 1, 1, 1)
        # Exposed
        self._button_spacer = QtGui.QSpacerItem(111, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self._button_grid_layt.addItem(self._button_spacer, 0, 2, 1, 1)
        # Exposed
        self.button_close = QtGui.QPushButton(self)
        self.button_close.setText(self.tr('Close'))
        self._button_grid_layt.addWidget(self.button_close, 0, 3, 1, 1)
        self._main_vbox_layt.addLayout(self._button_grid_layt)

        self.connect(self.button_close, SIGNAL('clicked()'), self.accept)


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    search = SearchView()
    search.show()
    sys.exit(app.exec_())
