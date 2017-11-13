"""A GUI for selecting commits"""
from __future__ import division, absolute_import, unicode_literals

from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import gitcmds
from .. import qtutils
from ..i18n import N_
from ..icons import folder
from ..interaction import Interaction
from . import defs
from .diff import DiffTextEdit
from .standard import Dialog


def select_commits(title, revs, summaries, multiselect=True):
    """Use the SelectCommits to select commits from a list."""
    model = Model(revs, summaries)
    parent = qtutils.active_window()
    dialog = SelectCommits(model, parent, title, multiselect=multiselect)

    return dialog.select_commits()


def select_commits_and_output(title, revs, summaries, multiselect=True):
    """Use the SelectCommitsAndOutput to select commits from a list and output path."""
    model = Model(revs, summaries)
    parent = qtutils.active_window()
    dialog = SelectCommitsAndOutput(model, parent, title,
                                    multiselect=multiselect)
    return dialog.select_commits_and_output()


class Model(object):
    def __init__(self, revs, summaries):
        self.revisions = revs
        self.summaries = summaries


class SelectCommits(Dialog):

    def __init__(self, model,
                 parent=None, title=None, multiselect=True, syntax=True):
        Dialog.__init__(self, parent)
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

        self.select_button = qtutils.ok_button(N_('Select'), enabled=False)
        self.close_button = qtutils.close_button()

        # Make the list widget slightly larger
        self.splitter = qtutils.splitter(Qt.Vertical,
                                         self.commits, self.commit_text)
        self.splitter.setSizes([100, 150])

        self.input_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                         self.close_button,
                                         qtutils.STRETCH,
                                         self.label, self.revision,
                                         self.select_button)

        self.main_layout = qtutils.vbox(defs.margin, defs.margin,
                                        self.splitter, self.input_layout)
        self.setLayout(self.main_layout)

        commits.itemSelectionChanged.connect(self.commit_oid_selected)
        commits.itemDoubleClicked.connect(self.commit_oid_double_clicked)

        qtutils.connect_button(self.select_button, self.accept)
        qtutils.connect_button(self.close_button, self.reject)

        self.init_state(None, self.resize_widget, parent)

    def resize_widget(self, parent):
        """Set the initial size of the widget"""
        width, height = qtutils.default_size(parent, 720, 480)
        self.resize(width, height)

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

    def commit_oid_selected(self):
        oid = self.selected_commit()
        selected = oid is not None
        self.select_button.setEnabled(selected)
        if not selected:
            self.commit_text.set_value('')
            self.revision.setText('')
            return
        self.revision.setText(oid)
        self.revision.selectAll()
        # Display the oid's commit
        commit_diff = gitcmds.commit_diff(oid)
        self.commit_text.setText(commit_diff)

    def commit_oid_double_clicked(self, item):
        oid = self.selected_commit()
        if oid:
            self.accept()


class SelectCommitsAndOutput(SelectCommits):

    def __init__(self, model, parent=None, title=None, multiselect=True,
                 syntax=True):
        SelectCommits.__init__(self, model, parent, title, multiselect, syntax)

        self.output_dir = 'output'
        self.select_output = qtutils.create_button(tooltip=N_('Select output dir'),
                                                   icon=folder())
        self.output_text = QtWidgets.QLineEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setText(self.output_dir)

        output_layout = qtutils.hbox(defs.no_margin, defs.no_spacing,
                                     self.select_output,
                                     self.output_text)

        self.input_layout.insertLayout(1, output_layout)
        qtutils.connect_button(self.select_output, self.show_output_dialog)

    def select_commits_and_output(self):
        to_export = SelectCommits.select_commits(self)
        output = self.output_dir

        return {'to_export': to_export, 'output': output}

    def show_output_dialog(self):
        self.output_dir = qtutils.opendir_dialog(N_('Select output directory'),
                                                 self.output_dir)
        if not self.output_dir:
            return

        self.output_text.setText(self.output_dir)
