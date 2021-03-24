"""A GUI for selecting commits"""
from __future__ import division, absolute_import, unicode_literals

from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import gitcmds
from .. import qtutils
from ..i18n import N_
from ..icons import folder
from ..interaction import Interaction
from . import completion
from . import defs
from .diff import DiffTextEdit
from .standard import Dialog


def select_commits(context, title, revs, summaries, multiselect=True):
    """Use the SelectCommits to select commits from a list."""
    model = Model(revs, summaries)
    parent = qtutils.active_window()
    dialog = SelectCommits(context, model, parent, title, multiselect=multiselect)
    return dialog.select_commits()


def select_commits_and_output(context, title, revs, summaries, multiselect=True):
    """Select commits from a list and output path"""
    model = Model(revs, summaries)
    parent = qtutils.active_window()
    dialog = SelectCommitsAndOutput(
        context, model, parent, title, multiselect=multiselect
    )
    return dialog.select_commits_and_output()


class Model(object):
    def __init__(self, revs, summaries):
        self.revisions = revs
        self.summaries = summaries


class SelectCommits(Dialog):
    def __init__(self, context, model, parent=None, title=None, multiselect=True):
        Dialog.__init__(self, parent)
        self.context = context
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

        self.commit_text = DiffTextEdit(context, self, whitespace=False)

        self.revision_label = QtWidgets.QLabel()
        self.revision_label.setText(N_('Revision Expression:'))
        self.revision = completion.GitRefLineEdit(context)
        self.revision.setReadOnly(True)

        self.search_label = QtWidgets.QLabel()
        self.search_label.setText(N_('Search:'))
        self.search = QtWidgets.QLineEdit()
        self.search.setReadOnly(False)

        # pylint: disable=no-member
        self.search.textChanged.connect(self.search_list)

        self.select_button = qtutils.ok_button(N_('Select'), enabled=False)

        # Make the list widget slightly larger
        self.splitter = qtutils.splitter(Qt.Vertical, self.commits, self.commit_text)
        self.splitter.setSizes([100, 150])

        self.input_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.search_label,
            self.search,
            qtutils.STRETCH,
            self.revision_label,
            self.revision,
            self.select_button,
        )

        self.main_layout = qtutils.vbox(
            defs.margin, defs.margin, self.input_layout, self.splitter
        )
        self.setLayout(self.main_layout)

        # pylint: disable=no-member
        commits.itemSelectionChanged.connect(self.commit_oid_selected)
        commits.itemDoubleClicked.connect(self.commit_oid_double_clicked)

        qtutils.connect_button(self.select_button, self.accept)

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
        context = self.context
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
        commit_diff = gitcmds.commit_diff(context, oid)
        self.commit_text.setText(commit_diff)

    def commit_oid_double_clicked(self, _item):
        oid = self.selected_commit()
        if oid:
            self.accept()

    def search_list(self, text):
        if text:
            for i in range(self.commits.count()):
                self.commits.item(i).setHidden(True)
        search_items = self.commits.findItems(text, Qt.MatchContains)
        for items in search_items:
            items.setHidden(False)


class SelectCommitsAndOutput(SelectCommits):
    def __init__(self, context, model, parent=None, title=None, multiselect=True):
        SelectCommits.__init__(self, context, model, parent, title, multiselect)

        self.output_dir = 'output'
        self.select_output = qtutils.create_button(
            tooltip=N_('Select output dir'), icon=folder()
        )
        self.output_text = QtWidgets.QLineEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setText(self.output_dir)

        output_layout = qtutils.hbox(
            defs.no_margin, defs.no_spacing, self.select_output, self.output_text
        )

        self.input_layout.insertLayout(1, output_layout)
        qtutils.connect_button(self.select_output, self.show_output_dialog)

    def select_commits_and_output(self):
        to_export = SelectCommits.select_commits(self)
        output = self.output_dir

        return {'to_export': to_export, 'output': output}

    def show_output_dialog(self):
        self.output_dir = qtutils.opendir_dialog(
            N_('Select output directory'), self.output_dir
        )
        if not self.output_dir:
            return

        self.output_text.setText(self.output_dir)
