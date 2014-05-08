from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import gitcmds
from cola import qtutils
from cola import utils
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import main
from cola.widgets import defs
from cola.widgets import completion
from cola.widgets.standard import Dialog
from cola.compat import ustr


def create_new_branch(revision=''):
    """Launches a dialog for creating a new branch"""
    model = main.MainModel()
    model.update_status()
    view = CreateBranchDialog(model, qtutils.active_window())
    if revision:
        view.set_revision(revision)
    view.show()
    return view


class CreateOpts(object):
    def __init__(self, model):
        self.model = model
        self.reset = False
        self.track = False
        self.fetch = True
        self.checkout = True
        self.revision = 'HEAD'
        self.branch = ''


class CreateThread(QtCore.QThread):
    def __init__(self, opts, parent):
        QtCore.QThread.__init__(self, parent)
        self.opts = opts

    def run(self):
        branch = self.opts.branch
        revision = self.opts.revision
        reset = self.opts.reset
        checkout = self.opts.checkout
        track = self.opts.track
        model = self.opts.model
        results = []
        status = 0

        if track and '/' in revision:
            remote = revision.split('/', 1)[0]
            status, out, err = model.git.fetch(remote)
            self.emit(SIGNAL('command'), status, out, err)
            results.append(('fetch', status, out, err))

        if status == 0:
            status, out, err = model.create_branch(branch, revision,
                                                   force=reset,
                                                   track=track)
            self.emit(SIGNAL('command'), status, out, err)

        results.append(('branch', status, out, err))
        if status == 0 and checkout:
            status, out, err = model.git.checkout(branch)
            self.emit(SIGNAL('command'), status, out, err)
            results.append(('checkout', status, out, err))

        main.model().update_status()
        self.emit(SIGNAL('done'), results)


class CreateBranchDialog(Dialog):
    """A dialog for creating branches."""

    def __init__(self, model, parent=None):
        Dialog.__init__(self, parent=parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowTitle(N_('Create Branch'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.model = model
        self.opts = CreateOpts(model)
        self.thread = CreateThread(self.opts, self)

        self.progress = QtGui.QProgressDialog(self)
        self.progress.setRange(0, 0)
        self.progress.setCancelButton(None)
        self.progress.setWindowTitle(N_('Create Branch'))
        self.progress.setWindowModality(Qt.WindowModal)

        self.branch_name_label = QtGui.QLabel()
        self.branch_name_label.setText(N_('Branch Name'))

        self.branch_name = QtGui.QLineEdit()

        self.rev_label = QtGui.QLabel()
        self.rev_label.setText(N_('Starting Revision'))

        self.revision = completion.GitRefLineEdit()
        current = gitcmds.current_branch()
        if current:
            self.revision.setText(current)

        self.local_radio = QtGui.QRadioButton()
        self.local_radio.setText(N_('Local branch'))
        self.local_radio.setChecked(True)

        self.remote_radio = QtGui.QRadioButton()
        self.remote_radio.setText(N_('Tracking branch'))

        self.tag_radio = QtGui.QRadioButton()
        self.tag_radio.setText(N_('Tag'))

        self.branch_list = QtGui.QListWidget()

        self.update_existing_label = QtGui.QLabel()
        self.update_existing_label.setText(N_('Update Existing Branch:'))

        self.no_update_radio = QtGui.QRadioButton()
        self.no_update_radio.setText(N_('No'))

        self.ffwd_only_radio = QtGui.QRadioButton()
        self.ffwd_only_radio.setText(N_('Fast Forward Only'))
        self.ffwd_only_radio.setChecked(True)

        self.reset_radio = QtGui.QRadioButton()
        self.reset_radio.setText(N_('Reset'))

        self.options_bottom_layout = QtGui.QHBoxLayout()
        self.options_checkbox_layout = QtGui.QVBoxLayout()

        self.fetch_checkbox = QtGui.QCheckBox()
        self.fetch_checkbox.setText(N_('Fetch Tracking Branch'))
        self.fetch_checkbox.setChecked(True)
        self.options_checkbox_layout.addWidget(self.fetch_checkbox)

        self.checkout_checkbox = QtGui.QCheckBox()
        self.checkout_checkbox.setText(N_('Checkout After Creation'))
        self.checkout_checkbox.setChecked(True)
        self.options_checkbox_layout.addWidget(self.checkout_checkbox)

        self.options_bottom_layout.addLayout(self.options_checkbox_layout)
        self.options_bottom_layout.addStretch()

        self.create_button = qtutils.create_button(text=N_('Create Branch'),
                                                   icon=qtutils.git_icon())
        self.create_button.setDefault(True)

        self.close_button = qtutils.create_button(text=N_('Close'))

        self.branch_name_layout = QtGui.QHBoxLayout()
        self.branch_name_layout.addWidget(self.branch_name_label)
        self.branch_name_layout.addWidget(self.branch_name)

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
        self.rev_start_group.setTitle(N_('Starting Revision'))

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
        self.option_group.setTitle(N_('Options'))

        self.options_grp_layout = QtGui.QVBoxLayout(self.option_group)
        self.options_grp_layout.setMargin(defs.margin)
        self.options_grp_layout.setSpacing(defs.spacing)
        self.options_grp_layout.addLayout(self.options_radio_layout)
        self.options_grp_layout.addLayout(self.options_bottom_layout)

        self.buttons_layout = QtGui.QHBoxLayout()
        self.buttons_layout.setMargin(defs.margin)
        self.buttons_layout.setSpacing(defs.spacing)
        self.buttons_layout.addWidget(self.create_button)
        self.buttons_layout.addWidget(self.close_button)

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

        qtutils.connect_button(self.close_button, self.reject)
        qtutils.connect_button(self.create_button, self.create_branch)
        qtutils.connect_button(self.local_radio, self.display_model)
        qtutils.connect_button(self.remote_radio, self.display_model)
        qtutils.connect_button(self.tag_radio, self.display_model)

        self.connect(self.branch_list, SIGNAL('itemSelectionChanged()'),
                     self.branch_item_changed)

        self.connect(self.thread, SIGNAL('command'), self.thread_command)
        self.connect(self.thread, SIGNAL('done'), self.thread_done)

        self.resize(555, 333)
        self.display_model()

    def set_revision(self, revision):
        self.revision.setText(revision)

    def getopts(self):
        self.opts.revision = self.revision.value()
        self.opts.branch = ustr(self.branch_name.text())
        self.opts.checkout = self.checkout_checkbox.isChecked()
        self.opts.reset = self.reset_radio.isChecked()
        self.opts.fetch = self.fetch_checkbox.isChecked()
        self.opts.track = self.remote_radio.isChecked()

    def create_branch(self):
        """Creates a branch; called by the "Create Branch" button"""
        self.getopts()
        revision = self.opts.revision
        branch = self.opts.branch
        no_update = self.no_update_radio.isChecked()
        ffwd_only = self.ffwd_only_radio.isChecked()
        existing_branches = gitcmds.branch_list()
        check_branch = False

        if not branch or not revision:
            qtutils.critical(N_('Missing Data'),
                             N_('Please provide both a branch '
                                'name and revision expression.'))
            return
        if branch in existing_branches:
            if no_update:
                msg = N_('Branch "%s" already exists.') % branch
                qtutils.critical(N_('Branch Exists'), msg)
                return
            # Whether we should prompt the user for lost commits
            commits = gitcmds.rev_list_range(revision, branch)
            check_branch = bool(commits)

        if check_branch:
            msg = (N_('Resetting "%(branch)s" to "%(revision)s" '
                      'will lose commits.') %
                   dict(branch=branch, revision=revision))
            if ffwd_only:
                qtutils.critical(N_('Branch Exists'), msg)
                return
            lines = [msg]
            for idx, commit in enumerate(commits):
                subject = commit[1][0:min(len(commit[1]),16)]
                if len(subject) < len(commit[1]):
                    subject += '...'
                lines.append('\t' + commit[0][:8]
                        +'\t' + subject)
                if idx >= 5:
                    skip = len(commits) - 5
                    lines.append('\t(%s)' % (N_('%d skipped') % skip))
                    break
            line = N_('Recovering lost commits may not be easy.')
            lines.append(line)
            if not qtutils.confirm(N_('Reset Branch?'),
                                   '\n'.join(lines),
                                   (N_('Reset "%(branch)s" to "%(revision)s"?') %
                                    dict(branch=branch, revision=revision)),
                                   N_('Reset Branch'),
                                   default=False,
                                   icon=qtutils.icon('undo.svg')):
                return
        self.setEnabled(False)
        self.progress.setEnabled(True)
        QtGui.QApplication.setOverrideCursor(Qt.WaitCursor)

        # Show a nice progress bar
        self.progress.setLabelText(N_('Updating...'))
        self.progress.show()
        self.thread.start()

    def thread_command(self, status, out, err):
        Interaction.log_status(status, out, err)

    def thread_done(self, results):
        self.setEnabled(True)
        self.progress.close()
        QtGui.QApplication.restoreOverrideCursor()

        for (cmd, status, out, err) in results:
            if status != 0:
                Interaction.critical(
                        N_('Error Creating Branch'),
                        (N_('"%(command)s" returned exit status "%(status)d"') %
                         dict(command='git '+cmd, status=status)))
                return

        self.accept()

    def branch_item_changed(self, *rest):
        """This callback is called when the branch selection changes"""
        # When the branch selection changes then we should update
        # the "Revision Expression" accordingly.
        qlist = self.branch_list
        (row, selected) = qtutils.selected_row(qlist)
        if not selected:
            return
        # Update the model with the selection
        sources = self.branch_sources()
        rev = sources[row]
        self.revision.setText(rev)

        # Set the branch field if we're branching from a remote branch.
        if not self.remote_radio.isChecked():
            return
        branch = utils.basename(rev)
        if branch == 'HEAD':
            return
        # Signal that we've clicked on a remote branch
        self.branch_name.setText(branch)

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
