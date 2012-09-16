"""A GUI for selecting commits"""
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

from cola import gitcmds
from cola import qtutils
from cola.interaction import Interaction
from cola.widgets import defs
from cola.widgets.text import DiffTextEdit


def select_commits(title, revs, summaries, multiselect=True):
    """Use the SelectCommitsDialog to select commits from a list."""
    model = Model(revs, summaries)
    parent = qtutils.active_window()
    dialog = SelectCommitsDialog(model, parent, qtutils.tr(title),
                                 multiselect=multiselect)
    return dialog.select_commits()


class Model(object):
    def __init__(self, revs, summaries):
        self.revisions = revs
        self.summaries = summaries

    def revision_sha1(self, idx):
        return self.revisions[idx]


class SelectCommitsDialog(QtGui.QDialog):
    def __init__(self, model,
                 parent=None, title=None, multiselect=True, syntax=True):
        QtGui.QDialog.__init__(self, parent)
        self.model = model
        if title:
            self.setWindowTitle(title)

        self.commit_list = QtGui.QListWidget()
        if multiselect:
            mode = QtGui.QAbstractItemView.ExtendedSelection
        else:
            mode = QtGui.QAbstractItemView.SingleSelection
        self.commit_list.setSelectionMode(mode)
        self.commit_list.setAlternatingRowColors(True)

        self.commit_text = DiffTextEdit(self, whitespace=False)

        self.label = QtGui.QLabel()
        self.label.setText(self.tr('Revision Expression:'))
        self.revision = QtGui.QLineEdit()
        self.revision.setReadOnly(True)

        self.select_button = QtGui.QPushButton(self.tr('Select'))
        self.select_button.setIcon(qtutils.apply_icon())
        self.select_button.setEnabled(False)
        self.select_button.setDefault(True)

        self.close_button = QtGui.QPushButton(self.tr('Close'))

        # Make the list widget slighty larger
        self.splitter = QtGui.QSplitter()
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.splitter.setHandleWidth(defs.handle_width)
        self.splitter.setSizes([100, 150])
        self.splitter.addWidget(self.commit_list)
        self.splitter.addWidget(self.commit_text)

        self.input_layout = QtGui.QHBoxLayout()
        self.input_layout.setMargin(0)
        self.input_layout.setSpacing(defs.spacing)
        self.input_layout.addWidget(self.label)
        self.input_layout.addWidget(self.revision)
        self.input_layout.addWidget(self.select_button)
        self.input_layout.addWidget(self.close_button)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(defs.margin)
        self.main_layout.setSpacing(defs.margin)
        self.main_layout.addWidget(self.splitter)
        self.main_layout.addLayout(self.input_layout)
        self.setLayout(self.main_layout)

        self.connect(self.commit_list,
                     SIGNAL('itemSelectionChanged()'), self.commit_sha1_selected)

        qtutils.connect_button(self.select_button, self.accept)
        qtutils.connect_button(self.close_button, self.reject)

        #self.setTabOrder(self.commit_list, self.commit_text)
        #self.setTabOrder(self.commit_text, self.revision)
        #self.setTabOrder(self.revision, self.select_button)
        #self.setTabOrder(self.select_button, self.close_button)
        #self.setTabOrder(self.close_button, self.commit_list)

        self.resize(700, 420)

    def select_commits(self):
        summaries = self.model.summaries
        if not summaries:
            msg = self.tr('No commits exist in this branch.')
            Interaction.log(msg)
            return []
        qtutils.set_items(self.commit_list, summaries)
        self.show()
        if self.exec_() != QtGui.QDialog.Accepted:
            return []
        revs = self.model.revisions
        return qtutils.selection_list(self.commit_list, revs)

    def commit_sha1_selected(self):
        row, selected = qtutils.selected_row(self.commit_list)
        self.select_button.setEnabled(selected)
        if not selected:
            self.commit_text.setText('')
            self.revision.setText('')
            return
        # Get the sha1 and put it in the revision line
        sha1 = self.model.revision_sha1(row)
        self.revision.setText(sha1)
        self.revision.selectAll()

        # Display the sha1's commit
        commit_diff = gitcmds.commit_diff(sha1)
        self.commit_text.setText(commit_diff)
