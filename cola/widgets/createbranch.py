from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtWidgets
from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..i18n import N_
from ..interaction import Interaction
from ..qtutils import get
from .. import gitcmds
from .. import icons
from .. import qtutils
from . import defs
from . import completion
from . import standard


def create_new_branch(context, revision=''):
    """Launches a dialog for creating a new branch"""
    view = CreateBranchDialog(context, parent=qtutils.active_window())
    if revision:
        view.set_revision(revision)
    view.show()
    return view


class CreateOpts(object):
    def __init__(self, context):
        self.context = context
        self.reset = False
        self.track = False
        self.fetch = True
        self.checkout = True
        self.revision = 'HEAD'
        self.branch = ''


class CreateThread(QtCore.QThread):
    command = Signal(object, object, object)
    result = Signal(object)

    def __init__(self, opts, parent):
        QtCore.QThread.__init__(self, parent)
        self.opts = opts

    def run(self):
        branch = self.opts.branch
        revision = self.opts.revision
        reset = self.opts.reset
        checkout = self.opts.checkout
        track = self.opts.track
        context = self.opts.context
        git = context.git
        model = context.model
        results = []
        status = 0

        if track and '/' in revision:
            remote = revision.split('/', 1)[0]
            status, out, err = git.fetch(remote)
            self.command.emit(status, out, err)
            results.append(('fetch', status, out, err))

        if status == 0:
            status, out, err = model.create_branch(
                branch, revision, force=reset, track=track
            )
            self.command.emit(status, out, err)

        results.append(('branch', status, out, err))
        if status == 0 and checkout:
            status, out, err = git.checkout(branch)
            self.command.emit(status, out, err)
            results.append(('checkout', status, out, err))

        model.update_status()
        self.result.emit(results)


class CreateBranchDialog(standard.Dialog):
    """A dialog for creating branches."""

    def __init__(self, context, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.setWindowTitle(N_('Create Branch'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.context = context
        self.model = context.model
        self.opts = CreateOpts(context)
        self.thread = CreateThread(self.opts, self)

        self.progress = None

        self.branch_name_label = QtWidgets.QLabel()
        self.branch_name_label.setText(N_('Branch Name'))

        self.branch_name = completion.GitCreateBranchLineEdit(context)
        self.branch_validator = completion.BranchValidator(
            context.git, parent=self.branch_name
        )
        self.branch_name.setValidator(self.branch_validator)

        self.rev_label = QtWidgets.QLabel()
        self.rev_label.setText(N_('Starting Revision'))

        self.revision = completion.GitRefLineEdit(context)
        current = gitcmds.current_branch(context)
        if current:
            self.revision.setText(current)

        self.local_radio = qtutils.radio(text=N_('Local branch'), checked=True)
        self.remote_radio = qtutils.radio(text=N_('Tracking branch'))
        self.tag_radio = qtutils.radio(text=N_('Tag'))

        self.branch_list = QtWidgets.QListWidget()

        self.update_existing_label = QtWidgets.QLabel()
        self.update_existing_label.setText(N_('Update Existing Branch:'))

        self.no_update_radio = qtutils.radio(text=N_('No'))
        self.ffwd_only_radio = qtutils.radio(text=N_('Fast Forward Only'), checked=True)
        self.reset_radio = qtutils.radio(text=N_('Reset'))

        text = N_('Fetch Tracking Branch')
        self.fetch_checkbox = qtutils.checkbox(text=text, checked=True)

        text = N_('Checkout After Creation')
        self.checkout_checkbox = qtutils.checkbox(text=text, checked=True)

        icon = icons.branch()
        self.create_button = qtutils.create_button(
            text=N_('Create Branch'), icon=icon, default=True
        )
        self.close_button = qtutils.close_button()

        self.options_checkbox_layout = qtutils.hbox(
            defs.margin,
            defs.spacing,
            self.fetch_checkbox,
            self.checkout_checkbox,
            qtutils.STRETCH,
        )

        self.branch_name_layout = qtutils.hbox(
            defs.margin, defs.spacing, self.branch_name_label, self.branch_name
        )

        self.rev_radio_group = qtutils.buttongroup(
            self.local_radio, self.remote_radio, self.tag_radio
        )

        self.rev_radio_layout = qtutils.hbox(
            defs.margin,
            defs.spacing,
            self.local_radio,
            self.remote_radio,
            self.tag_radio,
            qtutils.STRETCH,
        )

        self.rev_start_textinput_layout = qtutils.hbox(
            defs.no_margin, defs.spacing, self.rev_label, defs.spacing, self.revision
        )

        self.rev_start_layout = qtutils.vbox(
            defs.no_margin,
            defs.spacing,
            self.rev_radio_layout,
            self.branch_list,
            self.rev_start_textinput_layout,
        )

        self.options_radio_group = qtutils.buttongroup(
            self.no_update_radio, self.ffwd_only_radio, self.reset_radio
        )

        self.options_radio_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.update_existing_label,
            self.no_update_radio,
            self.ffwd_only_radio,
            self.reset_radio,
            qtutils.STRETCH,
        )

        self.buttons_layout = qtutils.hbox(
            defs.margin,
            defs.spacing,
            self.close_button,
            qtutils.STRETCH,
            self.create_button,
        )

        self.main_layout = qtutils.vbox(
            defs.margin,
            defs.spacing,
            self.branch_name_layout,
            self.rev_start_layout,
            defs.button_spacing,
            self.options_radio_layout,
            self.options_checkbox_layout,
            self.buttons_layout,
        )
        self.setLayout(self.main_layout)

        qtutils.add_close_action(self)
        qtutils.connect_button(self.close_button, self.close)
        qtutils.connect_button(self.create_button, self.create_branch)
        qtutils.connect_toggle(self.local_radio, self.display_model)
        qtutils.connect_toggle(self.remote_radio, self.display_model)
        qtutils.connect_toggle(self.tag_radio, self.display_model)

        branches = self.branch_list
        # pylint: disable=no-member
        branches.itemSelectionChanged.connect(self.branch_item_changed)

        thread = self.thread
        thread.command.connect(Interaction.log_status, type=Qt.QueuedConnection)
        thread.result.connect(self.thread_result, type=Qt.QueuedConnection)

        self.init_size(settings=context.settings, parent=parent)
        self.display_model()

    def set_revision(self, revision):
        self.revision.setText(revision)

    def getopts(self):
        self.opts.revision = get(self.revision)
        self.opts.branch = get(self.branch_name)
        self.opts.checkout = get(self.checkout_checkbox)
        self.opts.reset = get(self.reset_radio)
        self.opts.fetch = get(self.fetch_checkbox)
        self.opts.track = get(self.remote_radio)

    def create_branch(self):
        """Creates a branch; called by the "Create Branch" button"""
        context = self.context
        self.getopts()
        revision = self.opts.revision
        branch = self.opts.branch
        no_update = get(self.no_update_radio)
        ffwd_only = get(self.ffwd_only_radio)
        existing_branches = gitcmds.branch_list(context)
        check_branch = False

        if not branch or not revision:
            Interaction.critical(
                N_('Missing Data'),
                N_('Please provide both a branch ' 'name and revision expression.'),
            )
            return
        if branch in existing_branches:
            if no_update:
                msg = N_('Branch "%s" already exists.') % branch
                Interaction.critical(N_('Branch Exists'), msg)
                return
            # Whether we should prompt the user for lost commits
            commits = gitcmds.rev_list_range(context, revision, branch)
            check_branch = bool(commits)

        if check_branch:
            msg = N_(
                'Resetting "%(branch)s" to "%(revision)s" ' 'will lose commits.'
            ) % dict(branch=branch, revision=revision)
            if ffwd_only:
                Interaction.critical(N_('Branch Exists'), msg)
                return
            lines = [msg]
            for idx, commit in enumerate(commits):
                subject = commit[1][0 : min(len(commit[1]), 16)]
                if len(subject) < len(commit[1]):
                    subject += '...'
                lines.append('\t' + commit[0][:8] + '\t' + subject)
                if idx >= 5:
                    skip = len(commits) - 5
                    lines.append('\t(%s)' % (N_('%d skipped') % skip))
                    break
            line = N_('Recovering lost commits may not be easy.')
            lines.append(line)

            info_text = N_('Reset "%(branch)s" to "%(revision)s"?') % dict(
                branch=branch, revision=revision
            )

            if not Interaction.confirm(
                N_('Reset Branch?'),
                '\n'.join(lines),
                info_text,
                N_('Reset Branch'),
                default=False,
                icon=icons.undo(),
            ):
                return

        title = N_('Create Branch')
        label = N_('Updating')
        self.progress = standard.progress(title, label, self)
        self.progress.show()
        self.thread.start()

    def thread_result(self, results):
        self.progress.hide()
        del self.progress

        for (cmd, status, _, _) in results:
            if status != 0:
                Interaction.critical(
                    N_('Error Creating Branch'),
                    (
                        N_('"%(command)s" returned exit status "%(status)d"')
                        % dict(command='git ' + cmd, status=status)
                    ),
                )
                return

        self.accept()

    # pylint: disable=unused-argument
    def branch_item_changed(self, *rest):
        """This callback is called when the branch selection changes"""
        # When the branch selection changes then we should update
        # the "Revision Expression" accordingly.
        qlist = self.branch_list
        remote_branch = qtutils.selected_item(qlist, self.branch_sources())
        if not remote_branch:
            return
        # Update the model with the selection
        self.revision.setText(remote_branch)

        # Set the branch field if we're branching from a remote branch.
        if not get(self.remote_radio):
            return
        branch = gitcmds.strip_remote(self.model.remotes, remote_branch)
        if branch == 'HEAD':
            return
        # Signal that we've clicked on a remote branch
        self.branch_name.set_value(branch)

    def display_model(self):
        """Sets the branch list to the available branches"""
        branches = self.branch_sources()
        qtutils.set_items(self.branch_list, branches)

    def branch_sources(self):
        """Get the list of items for populating the branch root list."""
        if get(self.local_radio):
            value = self.model.local_branches
        elif get(self.remote_radio):
            value = self.model.remote_branches
        elif get(self.tag_radio):
            value = self.model.tags
        else:
            value = []
        return value

    def dispose(self):
        self.branch_name.dispose()
        self.revision.dispose()
