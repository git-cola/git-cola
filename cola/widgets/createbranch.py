from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import gitcmds
from cola import qt
from cola import qtutils
from cola import utils
from cola.widgets import defs
from cola.widgets import standard
from cola.main.model import MainModel


def create_new_branch(revision=''):
    """Launches a dialog for creating a new branch"""
    model = MainModel()
    model.update_status()
    view = CreateBranchDialog(model, qtutils.active_window())
    if revision:
        view.set_revision(revision)
    view.show()
    return view


class CreateBranchDialog(standard.Dialog):
    """A dialog for creating branches."""

    def __init__(self, model, parent=None):
        super(CreateBranchDialog, self).__init__(parent=parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.model = model

        self.setWindowTitle(self.tr('Create Branch'))

        self.branch_name_label = QtGui.QLabel()
        self.branch_name_label.setText(self.tr('Branch Name'))

        self.local_branch = QtGui.QLineEdit()

        self.rev_label = QtGui.QLabel()
        self.rev_label.setText(self.tr('Revision Expression:'))

        self.revision = QtGui.QLineEdit()

        self.local_radio = QtGui.QRadioButton()
        self.local_radio.setText(self.tr('Local Branch'))
        self.local_radio.setChecked(True)

        self.remote_radio = QtGui.QRadioButton()
        self.remote_radio.setText(self.tr('Tracking Branch'))

        self.tag_radio = QtGui.QRadioButton()
        self.tag_radio.setText(self.tr('Tag'))

        self.branch_list = QtGui.QListWidget()

        self.update_existing_label = QtGui.QLabel()
        self.update_existing_label.setText(self.tr('Update Existing Branch:'))

        self.no_update_radio = QtGui.QRadioButton()
        self.no_update_radio.setText(self.tr('No'))

        self.ffwd_only_radio = QtGui.QRadioButton()
        self.ffwd_only_radio.setText(self.tr('Fast Forward Only'))
        self.ffwd_only_radio.setChecked(True)

        self.reset_radio = QtGui.QRadioButton()
        self.reset_radio.setText(self.tr('Reset'))

        self.options_bottom_layout = QtGui.QHBoxLayout()
        self.options_checkbox_layout = QtGui.QVBoxLayout()

        self.fetch_checkbox = QtGui.QCheckBox()
        self.fetch_checkbox.setText(self.tr('Fetch Tracking Branch'))
        self.fetch_checkbox.setChecked(True)
        self.options_checkbox_layout.addWidget(self.fetch_checkbox)

        self.checkout_checkbox = QtGui.QCheckBox()
        self.checkout_checkbox.setText(self.tr('Checkout After Creation'))
        self.checkout_checkbox.setChecked(True)
        self.options_checkbox_layout.addWidget(self.checkout_checkbox)

        self.options_bottom_layout.addLayout(self.options_checkbox_layout)
        self.options_bottom_layout.addStretch()

        self.create_button = qt.create_button(text='Create Branch',
                                              icon=qtutils.git_icon())
        self.create_button.setDefault(True)

        self.cancel_button = qt.create_button(text='Cancel')

        self.branch_name_layout = QtGui.QHBoxLayout()
        self.branch_name_layout.addWidget(self.branch_name_label)
        self.branch_name_layout.addWidget(self.local_branch)

        self.rev_start_radiobtn_layout = QtGui.QHBoxLayout()
        self.rev_start_radiobtn_layout.addWidget(self.local_radio)
        self.rev_start_radiobtn_layout.addWidget(self.remote_radio)
        self.rev_start_radiobtn_layout.addWidget(self.tag_radio)
        self.rev_start_radiobtn_layout.addStretch()

        self.rev_start_textinput_layout = QtGui.QHBoxLayout()
        self.rev_start_textinput_layout.setMargin(0)
        self.rev_start_textinput_layout.setSpacing(defs.spacing)
        self.rev_start_textinput_layout.addWidget(self.rev_label)
        self.rev_start_textinput_layout.addWidget(self.revision)

        self.rev_start_group = QtGui.QGroupBox()
        self.rev_start_group.setTitle(self.tr('Starting Revision'))

        self.rev_start_layout = QtGui.QVBoxLayout(self.rev_start_group)
        self.rev_start_layout.setMargin(defs.margin)
        self.rev_start_layout.setSpacing(defs.spacing)
        self.rev_start_layout.addLayout(self.rev_start_radiobtn_layout)
        self.rev_start_layout.addWidget(self.branch_list)
        self.rev_start_layout.addLayout(self.rev_start_textinput_layout)

        self.options_radio_layout = QtGui.QHBoxLayout()
        self.options_radio_layout.addWidget(self.update_existing_label)
        self.options_radio_layout.addWidget(self.no_update_radio)
        self.options_radio_layout.addWidget(self.ffwd_only_radio)
        self.options_radio_layout.addWidget(self.reset_radio)

        self.option_group = QtGui.QGroupBox()
        self.option_group.setTitle(self.tr('Options'))

        self.options_grp_layout = QtGui.QVBoxLayout(self.option_group)
        self.options_grp_layout.setMargin(defs.margin)
        self.options_grp_layout.setSpacing(defs.spacing)
        self.options_grp_layout.addLayout(self.options_radio_layout)
        self.options_grp_layout.addLayout(self.options_bottom_layout)

        self.buttons_layout = QtGui.QHBoxLayout()
        self.buttons_layout.setMargin(defs.margin)
        self.buttons_layout.setSpacing(defs.spacing)
        self.buttons_layout.addWidget(self.create_button)
        self.buttons_layout.addWidget(self.cancel_button)

        self.options_section_layout = QtGui.QHBoxLayout()
        self.options_section_layout.setMargin(defs.margin)
        self.options_section_layout.setSpacing(defs.spacing)
        self.options_section_layout.addWidget(self.option_group)
        self.options_section_layout.addLayout(self.buttons_layout)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(defs.margin)
        self.main_layout.setSpacing(defs.spacing)
        self.main_layout.addLayout(self.branch_name_layout)
        self.main_layout.addWidget(self.rev_start_group)
        self.main_layout.addLayout(self.options_section_layout)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.cancel_button, self.reject)
        qtutils.connect_button(self.create_button, self.create_branch)
        qtutils.connect_button(self.local_radio, self.display_model)
        qtutils.connect_button(self.remote_radio, self.display_model)
        qtutils.connect_button(self.tag_radio, self.display_model)

        self.connect(self.branch_list, SIGNAL('itemSelectionChanged()'),
                     self.branch_item_changed)

        if self.parent():
            self.resize(self.parent().width(), self.parent().height())
        else:
            self.resize(555, 333)

        self.display_model()

    def set_revision(self, revision):
        self.revision.setText(revision)

    def create_branch(self):
        """Creates a branch; called by the "Create Branch" button"""

        revision = unicode(self.revision.text())
        branch = unicode(self.local_branch.text())
        existing_branches = self.model.local_branches

        if not branch or not revision:
            qtutils.critical('Missing Data',
                             'Please provide both a branch '
                             'name and revision expression.')
            return

        check_branch = False
        if branch in existing_branches:
            if self.no_update_radio.isChecked():
                msg = self.tr("Branch '%s' already exists.")
                msg = unicode(msg) % branch
                qtutils.critical('Branch Exists', msg)
                return
            # Whether we should prompt the user for lost commits
            commits = gitcmds.rev_list_range(revision, branch)
            check_branch = bool(commits)

        if check_branch:
            msg = self.tr("Resetting '%s' to '%s' will "
                          "lose the following commits:")
            lines = [ unicode(msg) % (branch, revision) ]

            for idx, commit in enumerate(commits):
                subject = commit[1][0:min(len(commit[1]),16)]
                if len(subject) < len(commit[1]):
                    subject += '...'
                lines.append('\t' + commit[0][:8]
                        +'\t' + subject)
                if idx >= 5:
                    skip = len(commits) - 5
                    lines.append('\t(%d skipped)' % skip)
                    break

            lines.extend([
                unicode(self.tr('Recovering lost commits may not be easy.')),
                ])

            if not qtutils.confirm('Reset Branch?',
                                   '\n'.join(lines),
                                   'Reset "%s" to "%s"?' % (branch, revision),
                                   'Reset Branch',
                                   default=False,
                                   icon=qtutils.icon('undo.svg')):
                return

        # TODO handle fetch
        track = self.remote_radio.isChecked()
        fetch = self.fetch_checkbox.isChecked()
        ffwd = self.ffwd_only_radio.isChecked()
        reset = self.reset_radio.isChecked()
        chkout = self.checkout_checkbox.isChecked()

        status, output = self.model.create_branch(branch, revision, track=track)
        qtutils.log(status, output)
        if status == 0 and chkout:
            status, output = self.model.git.checkout(branch,
                                                     with_status=True,
                                                     with_stderr=True)
            qtutils.log(status, output)
        self.accept()

    def branch_item_changed(self, *rest):
        """This callback is called when the branch selection changes"""

        # When the branch selection changes then we should update
        # the "Revision Expression" accordingly.
        qlist = self.branch_list
        (row, selected) = qtutils.selected_row(qlist)
        if not selected:
            return

        sources = self.branch_sources()
        rev = sources[row]

        # Update the model with the selection
        self.revision.setText(rev)

        # Only set the branch name field if we're
        # branching from a remote branch.
        if not self.remote_radio.isChecked():
            return
        branch = utils.basename(rev)
        if branch == 'HEAD':
            return

        # Signal that we've clicked on a remote branch
        self.local_branch.setText(branch)

    def display_model(self):
        """Sets the branch list to the available branches
        """
        branches = self.branch_sources()
        qtutils.set_items(self.branch_list, branches)

    def branch_sources(self):
        """Get the list of items for populating the branch root list.
        """
        if self.local_radio.isChecked():
            return self.model.local_branches
        elif self.remote_radio.isChecked():
            return self.model.remote_branches
        elif self.tag_radio.isChecked():
            return self.model.tags
