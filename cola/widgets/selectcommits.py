"""A GUI for selecting commits"""
from __future__ import division, absolute_import, unicode_literals

from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import gitcmds
from .. import qtutils
from ..i18n import N_
from ..interaction import Interaction
from . import defs
from .diff import DiffTextEdit


def select_commits(title, revs, summaries, multiselect=True):
    """Use the SelectCommitsDialog to select commits from a list."""
    model = Model(revs, summaries)
    parent = qtutils.active_window()
    dialog = SelectCommitsDialog(model, parent, title, multiselect=multiselect)
    return dialog.select_commits()


class Model(object):
    def __init__(self, revs, summaries):
        self.revisions = revs
        self.summaries = summaries


class SelectCommitsDialog(QtWidgets.QDialog):

    def __init__(self, model,
                 parent=None, title=None, multiselect=True, syntax=True):
        QtWidgets.QDialog.__init__(self, parent)
        self.model = model
        if title:
            self.setWindowTitle(title)

        if multiselect:
            mode = QtWidgets.QAbstractItemView.ExtendedSelection
        else:
            mode = QtWidgets.QAbstractItemView.SingleSelection
        commits = self.commits = QtWidgets.QListWidget()
        commits.setSelectionMode(mode)
        commits.setAlternatingRowColors(True)

        self.commit_text = DiffTextEdit(self, whitespace=False)

        self.label = QtWidgets.QLabel()
        self.label.setText(N_('Revision Expression:'))
        self.revision = QtWidgets.QLineEdit()
        self.revision.setReadOnly(True)

        self.select_button = qtutils.ok_button(N_('Select'),
                                               enabled=False, default=True)
        self.close_button = qtutils.close_button()

        # Make the list widget slightly larger
        self.splitter = qtutils.splitter(Qt.Vertical,
                                         self.commits, self.commit_text)
        self.splitter.setSizes([100, 150])

        self.input_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                         self.label, self.revision,
                                         self.select_button, self.close_button)

        self.main_layout = qtutils.vbox(defs.margin, defs.margin,
                                        self.splitter, self.input_layout)
        self.setLayout(self.main_layout)

        commits.itemSelectionChanged.connect(self.commit_sha1_selected)
        commits.itemDoubleClicked.connect(self.commit_sha1_double_clicked)

        qtutils.connect_button(self.select_button, self.accept)
        qtutils.connect_button(self.close_button, self.reject)

        self.resize(700, 420)

    def selected_commit(self):
        return qtutils.selected_item(self.commits, self.model.revisions)

    def selected_commits(self):
        return qtutils.selected_items(self.commits, self.model.revisions)

    def select_commits(self):
        summaries = self.model.summaries
        if not summaries:
            msg = N_('No commits exist in this branch.')
            Interaction.log(msg)
            return []
        qtutils.set_items(self.commits, summaries)
        self.show()
        if self.exec_() != QtWidgets.QDialog.Accepted:
            return []
        return self.selected_commits()

    def commit_sha1_selected(self):
        sha1 = self.selected_commit()
        selected = sha1 is not None
        self.select_button.setEnabled(selected)
        if not selected:
            self.commit_text.setText('')
            self.revision.setText('')
            return
        self.revision.setText(sha1)
        self.revision.selectAll()
        # Display the sha1's commit
        commit_diff = gitcmds.commit_diff(sha1)
        self.commit_text.setText(commit_diff)

    def commit_sha1_double_clicked(self, item):
        sha1 = self.selected_commit()
        if sha1:
            self.accept()
