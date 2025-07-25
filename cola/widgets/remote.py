"""Widgets for Fetch, Push, and Pull"""
import fnmatch
import time
import os

try:
    import notifypy
except (ImportError, ModuleNotFoundError):
    notifypy = None

from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from ..i18n import N_
from ..interaction import Interaction
from ..models import main
from ..models import prefs
from ..models.main import FETCH, FETCH_HEAD, PULL, PUSH
from ..qtutils import connect_button
from ..qtutils import get
from .. import core
from .. import display
from .. import git
from .. import gitcmds
from .. import icons
from .. import resources
from .. import qtutils
from .. import utils
from . import defs
from . import log
from . import standard


def fetch(context):
    """Fetch from remote repositories"""
    return run(context, Fetch)


def push(context):
    """Push to remote repositories"""
    return run(context, Push)


def pull(context):
    """Pull from remote repositories"""
    return run(context, Pull)


def run(context, RemoteDialog):
    """Launches fetch/push/pull dialogs."""
    # Copy global stuff over to speedup startup
    parent = qtutils.active_window()
    view = RemoteDialog(context, parent=parent)
    view.show()
    return view


def combine(result, prev):
    """Combine multiple (status, out, err) tuples into a combined tuple

    The current state is passed in via `prev`.
    The status code is a max() over all the subprocess status codes.
    Individual (out, err) strings are sequentially concatenated together.

    """
    if isinstance(prev, (tuple, list)):
        if len(prev) != 3:
            raise AssertionError('combine() with length %d' % len(prev))
        combined = (
            max(prev[0], result[0]),
            combine(prev[1], result[1]),
            combine(prev[2], result[2]),
        )
    elif prev and result:
        combined = prev + '\n\n' + result
    elif prev:
        combined = prev
    else:
        combined = result

    return combined


def uncheck(value, *checkboxes):
    """Uncheck the specified checkboxes if value is True"""
    if value:
        for checkbox in checkboxes:
            checkbox.setChecked(False)


def strip_remotes(remote_branches):
    """Strip the <remote>/ prefixes from branches

    e.g. "origin/main" becomes "main".

    """
    branches = [utils.strip_one(branch) for branch in remote_branches]
    return [branch for branch in branches if branch != 'HEAD']


class ActionTask(qtutils.Task):
    """Run actions asynchronously"""

    def __init__(self, model_action, remote, kwargs):
        qtutils.Task.__init__(self)
        self.model_action = model_action
        self.remote = remote
        self.kwargs = kwargs

    def task(self):
        """Runs the model action and captures the result"""
        return self.model_action(self.remote, **self.kwargs)


def _emit_push_notification(
    context, selected_remotes, pushed_remotes, unpushed_remotes
):
    """Emit desktop notification when pushing remotes"""
    total = len(selected_remotes)
    count = len(pushed_remotes)
    scope = {
        'total': total,
        'count': count,
    }
    title = N_('Pushed %(count)s / %(total)s remotes') % scope

    pushed_message = N_('Pushed: %s') % ', '.join(pushed_remotes)
    unpushed_message = N_('Not pushed: %s') % ', '.join(unpushed_remotes)
    success_icon = resources.icon_path('git-cola-ok.svg')
    error_icon = resources.icon_path('git-cola-error.svg')

    if unpushed_remotes:
        icon = error_icon
    else:
        icon = success_icon

    if pushed_remotes and unpushed_remotes:
        message = unpushed_message + '\t\t' + pushed_message
    elif pushed_remotes:
        message = pushed_message
    else:
        message = unpushed_message

    display.notify(context.app_name, title, message, icon)


class RemoteActionDialog(standard.Dialog):
    """Interface for performing remote operations"""

    def __init__(self, context, action, title, parent=None, icon=None):
        """Customize the dialog based on the remote action"""
        standard.Dialog.__init__(self, parent=parent)
        self.setWindowTitle(title)
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.context = context
        self.model = model = context.model
        self.action = action
        self.filtered_remote_branches = []
        self.selected_remotes = []
        self.selected_remotes_by_worktree = {}
        self.last_updated = 0.0

        self.runtask = qtutils.RunTask(parent=self)
        self.local_label = QtWidgets.QLabel()
        self.local_label.setText(N_('Local Branch'))

        self.local_branch = QtWidgets.QLineEdit()
        self.local_branch.textChanged.connect(self.local_branch_text_changed)
        local_branches = self.get_local_branches()
        qtutils.add_completer(self.local_branch, local_branches)

        self.local_branches = QtWidgets.QListWidget()
        self.local_branches.addItems(local_branches)

        self.remote_label = QtWidgets.QLabel()
        self.remote_label.setText(N_('Remote'))

        self.remote_name = QtWidgets.QLineEdit()
        qtutils.add_completer(self.remote_name, model.remotes)

        self.remote_name.editingFinished.connect(self.remote_name_edited)
        self.remote_name.textEdited.connect(lambda _: self.remote_name_edited())

        self.remotes = QtWidgets.QListWidget()
        if action == PUSH:
            mode = QtWidgets.QAbstractItemView.ExtendedSelection
            self.remotes.setSelectionMode(mode)
        self.remotes.addItems(model.remotes)

        self.remote_branch_label = QtWidgets.QLabel()
        self.remote_branch_label.setText(N_('Remote Branch'))

        self.remote_branch = QtWidgets.QLineEdit()
        self.remote_branch.textChanged.connect(lambda _: self.update_command_display())
        remote_branches = strip_remotes(model.remote_branches)
        qtutils.add_completer(self.remote_branch, remote_branches)

        self.remote_branches = QtWidgets.QListWidget()
        self.remote_branches.addItems(model.remote_branches)

        text = N_('Prompt on creation')
        tooltip = N_('Prompt when pushing creates new remote branches')
        self.prompt_checkbox = qtutils.checkbox(
            checked=True, text=text, tooltip=tooltip
        )

        text = N_('Show remote messages')
        tooltip = N_('Display remote messages in a separate dialog')
        self.remote_messages_checkbox = qtutils.checkbox(
            checked=False, text=text, tooltip=tooltip
        )

        text = N_('Fast-forward only')
        tooltip = N_(
            'Refuse to merge unless the current HEAD is already up-'
            'to-date or the merge can be resolved as a fast-forward'
        )
        self.ff_only_checkbox = qtutils.checkbox(
            checked=True, text=text, tooltip=tooltip
        )
        self.ff_only_checkbox.toggled.connect(self.update_command_display)

        text = N_('No fast-forward')
        tooltip = N_(
            'Create a merge commit even when the merge resolves as a fast-forward'
        )
        self.no_ff_checkbox = qtutils.checkbox(
            checked=False, text=text, tooltip=tooltip
        )
        self.no_ff_checkbox.toggled.connect(self.update_command_display)
        text = N_('Force')
        tooltip = N_(
            'Allow non-fast-forward updates.  Using "force" can '
            'cause the remote repository to lose commits; '
            'use it with care'
        )
        self.force_checkbox = qtutils.checkbox(
            checked=False, text=text, tooltip=tooltip
        )
        self.force_checkbox.toggled.connect(self.update_command_display)

        self.tags_checkbox = qtutils.checkbox(text=N_('Include tags '))
        self.tags_checkbox.toggled.connect(self.update_command_display)

        tooltip = N_(
            'Remove remote-tracking branches that no longer exist on the remote'
        )
        self.prune_checkbox = qtutils.checkbox(text=N_('Prune '), tooltip=tooltip)
        self.prune_checkbox.toggled.connect(self.update_command_display)

        tooltip = N_('Rebase the current branch instead of merging')
        self.rebase_checkbox = qtutils.checkbox(text=N_('Rebase'), tooltip=tooltip)
        self.rebase_checkbox.toggled.connect(self.update_command_display)

        text = N_('Set upstream')
        tooltip = N_('Configure the remote branch as the the new upstream')
        self.upstream_checkbox = qtutils.checkbox(text=text, tooltip=tooltip)
        self.upstream_checkbox.toggled.connect(self.update_command_display)

        text = N_('Close on completion')
        tooltip = N_('Close dialog when completed')
        self.close_on_completion_checkbox = qtutils.checkbox(
            checked=True, text=text, tooltip=tooltip
        )

        self.action_button = qtutils.ok_button(title, icon=icon)
        self.close_button = qtutils.close_button()
        self.buttons_group = utils.Group(self.close_button, self.action_button)
        self.inputs_group = utils.Group(
            self.close_on_completion_checkbox,
            self.force_checkbox,
            self.ff_only_checkbox,
            self.local_branch,
            self.local_branches,
            self.tags_checkbox,
            self.prune_checkbox,
            self.rebase_checkbox,
            self.remote_name,
            self.remotes,
            self.remote_branch,
            self.remote_branches,
            self.upstream_checkbox,
            self.prompt_checkbox,
            self.remote_messages_checkbox,
        )
        self.progress = standard.progress_bar(
            self,
            disable=(self.buttons_group, self.inputs_group),
        )

        self.command_display = log.LogWidget(self.context, display_usage=False)

        self.local_branch_layout = qtutils.hbox(
            defs.small_margin, defs.spacing, self.local_label, self.local_branch
        )

        self.remote_layout = qtutils.hbox(
            defs.small_margin, defs.spacing, self.remote_label, self.remote_name
        )

        self.remote_branch_layout = qtutils.hbox(
            defs.small_margin,
            defs.spacing,
            self.remote_branch_label,
            self.remote_branch,
        )

        self.options_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.force_checkbox,
            self.ff_only_checkbox,
            self.no_ff_checkbox,
            self.tags_checkbox,
            self.prune_checkbox,
            self.rebase_checkbox,
            self.upstream_checkbox,
            self.prompt_checkbox,
            self.close_on_completion_checkbox,
            self.remote_messages_checkbox,
            qtutils.STRETCH,
            self.progress,
            self.close_button,
            self.action_button,
        )

        self.remote_input_layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.remote_layout, self.remotes
        )

        self.local_branch_input_layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.local_branch_layout, self.local_branches
        )

        self.remote_branch_input_layout = qtutils.vbox(
            defs.no_margin,
            defs.spacing,
            self.remote_branch_layout,
            self.remote_branches,
        )

        if action == PUSH:
            widgets = (
                self.remote_input_layout,
                self.local_branch_input_layout,
                self.remote_branch_input_layout,
            )
        else:  # fetch and pull
            widgets = (
                self.remote_input_layout,
                self.remote_branch_input_layout,
                self.local_branch_input_layout,
            )
        self.top_layout = qtutils.hbox(defs.no_margin, defs.spacing, *widgets)

        self.main_layout = qtutils.vbox(
            defs.margin,
            defs.spacing,
            self.top_layout,
            self.command_display,
            self.options_layout,
        )
        self.main_layout.setStretchFactor(self.top_layout, 2)
        self.setLayout(self.main_layout)

        remotes = model.remotes
        default_remote = gitcmds.get_default_remote(context)
        if default_remote in remotes:
            idx = remotes.index(default_remote)
            if self.select_remote(idx):
                self.set_remote_name(default_remote)
        else:
            if self.select_first_remote():
                self.set_remote_name(remotes[0])

        # Trim the remote list to just the default remote
        self.update_remotes(update_command_display=False)

        # Setup signals and slots
        self.remotes.itemSelectionChanged.connect(self.update_remotes)

        local = self.local_branches
        local.itemSelectionChanged.connect(self.update_local_branches)

        remote = self.remote_branches
        remote.itemSelectionChanged.connect(self.update_remote_branches)

        self.no_ff_checkbox.toggled.connect(
            lambda x: uncheck(x, self.ff_only_checkbox, self.rebase_checkbox)
        )

        self.ff_only_checkbox.toggled.connect(
            lambda x: uncheck(x, self.no_ff_checkbox, self.rebase_checkbox)
        )

        self.rebase_checkbox.toggled.connect(
            lambda x: uncheck(x, self.no_ff_checkbox, self.ff_only_checkbox)
        )

        connect_button(self.action_button, self.action_callback)
        connect_button(self.close_button, self.close)

        qtutils.add_action(
            self, N_('Close'), self.close, QtGui.QKeySequence.Close, 'Esc'
        )
        if action != FETCH:
            self.prune_checkbox.hide()

        if action != PUSH:
            # Push-only options
            self.upstream_checkbox.hide()
            self.prompt_checkbox.hide()

        if action == PULL:
            # Fetch and Push-only options
            self.force_checkbox.hide()
            self.tags_checkbox.hide()
            self.local_label.hide()
            self.local_branch.hide()
            self.local_branches.hide()
        else:
            # Pull-only options
            self.rebase_checkbox.hide()
            self.no_ff_checkbox.hide()
            self.ff_only_checkbox.hide()

        self.init_size(parent=parent)
        self.set_field_defaults()

    def set_rebase(self, value):
        """Check the rebase checkbox"""
        self.rebase_checkbox.setChecked(value)

    def set_field_defaults(self):
        """Set sensible initial defaults"""
        # Default to "git fetch origin main"
        action = self.action
        if action == FETCH:
            self.set_local_branch('')
            self.set_remote_branch('')
        if action == PULL:  # Nothing to do when fetching.
            pass
        # Select the current branch by default for push
        if action == PUSH:
            branch = self.model.currentbranch
            try:
                idx = self.model.local_branches.index(branch)
            except ValueError:
                return
            self.select_local_branch(idx)
            self.set_remote_branch(branch)

        self.update_command_display()

    def update_command_display(self):
        """Display the git commands that will be run"""
        commands = ['']
        for remote in self.selected_remotes:
            cmd = ['git', self.action]
            _, kwargs = self.common_args()
            args, kwargs = main.remote_args(self.context, remote, self.action, **kwargs)
            cmd.extend(git.transform_kwargs(**kwargs))
            cmd.extend(args)
            commands.append(core.list2cmdline(cmd))
        self.command_display.set_output('\n'.join(commands))

    def local_branch_text_changed(self, value):
        """Update the remote branch field in response to local branch text edits"""
        if self.action == PUSH:
            self.remote_branches.clearSelection()
            self.set_remote_branch(value)
        self.update_command_display()

    def set_remote_name(self, remote_name):
        """Set the remote name"""
        self.remote_name.setText(remote_name)

    def set_local_branch(self, branch):
        """Set the local branch name"""
        self.local_branch.setText(branch)
        if branch:
            self.local_branch.selectAll()

    def set_remote_branch(self, branch):
        """Set the remote branch name"""
        self.remote_branch.setText(branch)
        if branch:
            self.remote_branch.selectAll()

    def set_remote_branches(self, branches):
        """Set the list of remote branches"""
        self.remote_branches.clear()
        self.remote_branches.addItems(branches)
        self.filtered_remote_branches = branches
        qtutils.add_completer(self.remote_branch, strip_remotes(branches))

    def select_first_remote(self):
        """Select the first remote in the list view"""
        return self.select_remote(0)

    def select_remote(self, idx, make_current=True):
        """Select a remote by index"""
        item = self.remotes.item(idx)
        if item:
            item.setSelected(True)
            if make_current:
                self.remotes.setCurrentItem(item)
                self.set_remote_name(item.text())
            result = True
        else:
            result = False
        return result

    def select_remote_by_name(self, remote, make_current=True):
        """Select a remote by name"""
        remotes = self.model.remotes
        if remote in remotes:
            idx = remotes.index(remote)
            result = self.select_remote(idx, make_current=make_current)
        else:
            result = False
        return result

    def set_selected_remotes(self, remotes):
        """Set the list of selected remotes

        Return True if all remotes were found and selected.

        """
        # Invalid remote names are ignored.
        # This handles a remote going away between sessions.
        # The selection is unchanged when none of the specified remotes exist.
        found = False
        for remote in remotes:
            if remote in self.model.remotes:
                found = True
                break
        if found:
            # Only clear the selection if the specified remotes exist
            self.remotes.clearSelection()
            found = all(self.select_remote_by_name(x) for x in remotes)
        return found

    def select_local_branch(self, idx):
        """Selects a local branch by index in the list view"""
        item = self.local_branches.item(idx)
        if item:
            item.setSelected(True)
            self.local_branches.setCurrentItem(item)
            self.set_local_branch(item.text())
            result = True
        else:
            result = False
        return result

    def select_remote_branch(self, idx):
        """Selects a remote branch by index in the list view"""
        item = self.remote_branches.item(idx)
        if item:
            item.setSelected(True)
            self.remote_branches.setCurrentItem(item)
            remote_branch = item.text()
            branch = remote_branch.split('/', 1)[-1]
            self.set_remote_branch(branch)
            result = True
        else:
            result = False
        return result

    def display_remotes(self, widget):
        """Display the available remotes in a listwidget"""
        displayed = []
        for remote_name in self.model.remotes:
            url = self.model.remote_url(remote_name, self.action)
            display_text = '{}\t({})'.format(remote_name, N_('URL: %s') % url)
            displayed.append(display_text)
        qtutils.set_items(widget, displayed)

    def update_remotes(self, update_command_display=True):
        """Update the remote name when a remote from the list is selected"""
        widget = self.remotes
        remotes = self.model.remotes
        selection = qtutils.selected_item(widget, remotes)
        if not selection:
            self.selected_remotes = []
            return
        self.set_remote_name(selection)
        self.selected_remotes = qtutils.selected_items(self.remotes, self.model.remotes)
        self.set_remote_to(selection, self.selected_remotes)
        worktree = self.context.git.worktree()
        self.selected_remotes_by_worktree[worktree] = self.selected_remotes
        if update_command_display:
            self.update_command_display()

    def set_remote_to(self, _remote, selected_remotes):
        context = self.context
        all_branches = gitcmds.branch_list(context, remote=True)
        branches = []
        patterns = []
        remote = ''
        for remote_name in selected_remotes:
            remote = remote or remote_name  # Use the first remote when prepopulating.
            patterns.append(remote_name + '/*')

        for branch in all_branches:
            for pat in patterns:
                if fnmatch.fnmatch(branch, pat):
                    branches.append(branch)
                    break
        if branches:
            self.set_remote_branches(branches)
        else:
            self.set_remote_branches(all_branches)

        if self.action == FETCH:
            self.set_remote_branch('')
        elif self.action in (PUSH, PULL):
            branch = ''
            current_branch = (
                self.local_branch.text() or self.context.model.currentbranch
            )
            remote_branch = f'{remote}/{current_branch}'
            if branches and remote_branch in branches:
                branch = current_branch
                try:
                    idx = self.filtered_remote_branches.index(remote_branch)
                except ValueError:
                    pass
                self.select_remote_branch(idx)
                return
            self.set_remote_branch(branch)

    def remote_name_edited(self):
        """Update the current remote when the remote name is typed manually"""
        remote = self.remote_name.text()
        self.update_selected_remotes(remote)
        self.set_remote_to(remote, self.selected_remotes)
        self.update_command_display()

    def get_local_branches(self):
        """Calculate the list of local branches"""
        if self.action == FETCH:
            branches = self.model.local_branches + [FETCH_HEAD]
        else:
            branches = self.model.local_branches
        return branches

    def update_local_branches(self):
        """Update the local/remote branch names when a branch is selected"""
        branches = self.get_local_branches()
        widget = self.local_branches
        selection = qtutils.selected_item(widget, branches)
        if not selection:
            return
        self.set_local_branch(selection)
        if self.action == FETCH and selection != FETCH_HEAD:
            self.set_remote_branch(selection)
        self.update_command_display()

    def update_remote_branches(self):
        """Update the remote branch name when a branch is selected"""
        widget = self.remote_branches
        branches = self.filtered_remote_branches
        selection = qtutils.selected_item(widget, branches)
        if not selection:
            return
        branch = utils.strip_one(selection)
        if branch == 'HEAD':
            return
        self.set_remote_branch(branch)
        self.update_command_display()

    def common_args(self):
        """Returns git arguments common to fetch/push/pull"""
        remote_name = self.remote_name.text()
        local_branch = self.local_branch.text()
        remote_branch = self.remote_branch.text()

        ff_only = get(self.ff_only_checkbox)
        force = get(self.force_checkbox)
        no_ff = get(self.no_ff_checkbox)
        rebase = get(self.rebase_checkbox)
        set_upstream = get(self.upstream_checkbox)
        tags = get(self.tags_checkbox)
        prune = get(self.prune_checkbox)

        return (
            remote_name,
            {
                'ff_only': ff_only,
                'force': force,
                'local_branch': local_branch,
                'no_ff': no_ff,
                'rebase': rebase,
                'remote_branch': remote_branch,
                'set_upstream': set_upstream,
                'tags': tags,
                'prune': prune,
            },
        )

    # Actions

    def push_to_all(self, _remote, *args, **kwargs):
        """Push to all selected remotes"""
        selected_remotes = self.selected_remotes
        all_results = None

        pushed_remotes = []
        unpushed_remotes = []

        for remote in selected_remotes:
            result = self.model.push(remote, *args, **kwargs)

            if result[0] == 0:
                pushed_remotes.append(remote)
            else:
                unpushed_remotes.append(remote)

            all_results = combine(result, all_results)

        if prefs.notify_on_push(self.context):
            _emit_push_notification(
                self.context, selected_remotes, pushed_remotes, unpushed_remotes
            )

        return all_results

    def action_callback(self):
        """Perform the actual fetch/push/pull operation"""
        action = self.action
        remote_messages = get(self.remote_messages_checkbox)
        if action == FETCH:
            model_action = self.model.fetch
        elif action == PUSH:
            model_action = self.push_to_all
        else:  # if action == PULL:
            model_action = self.model.pull

        remote_name = self.remote_name.text()
        if not remote_name:
            errmsg = N_('No repository selected.')
            Interaction.log(errmsg)
            return
        remote, kwargs = self.common_args()
        self.update_selected_remotes(remote)

        # Check if we're about to create a new branch and warn.
        remote_branch = self.remote_branch.text()
        local_branch = self.local_branch.text()

        if action == PUSH:
            if remote_branch:
                branch = remote_branch
            else:
                branch = local_branch
            candidate = f'{remote}/{branch}'
            prompt = get(self.prompt_checkbox)

            if prompt and candidate not in self.model.remote_branches:
                title = N_('Push')
                args = {
                    'branch': branch,
                    'remote': remote,
                }
                msg = (
                    N_(
                        'Branch "%(branch)s" does not exist in "%(remote)s".\n'
                        'A new remote branch will be published.'
                    )
                    % args
                )
                info_txt = N_('Create a new remote branch?')
                ok_text = N_('Create Remote Branch')
                if not Interaction.confirm(
                    title, msg, info_txt, ok_text, icon=icons.cola()
                ):
                    return

        if get(self.force_checkbox):
            if action == FETCH:
                title = N_('Force Fetch?')
                msg = N_('Non-fast-forward fetch overwrites local history!')
                info_txt = N_('Force fetching from %s?') % remote
                ok_text = N_('Force Fetch')
            elif action == PUSH:
                title = N_('Force Push?')
                msg = N_(
                    'Non-fast-forward push overwrites published '
                    'history!\n(Did you pull first?)'
                )
                info_txt = N_('Force push to %s?') % remote
                ok_text = N_('Force Push')
            else:  # pull: shouldn't happen since the controls are hidden
                return
            if not Interaction.confirm(
                title, msg, info_txt, ok_text, default=False, icon=icons.discard()
            ):
                return

        self.progress.setMaximumHeight(
            self.action_button.height() - defs.small_margin * 2
        )

        # Use a thread to update in the background
        task = ActionTask(model_action, remote, kwargs)
        if remote_messages:
            result = log.show_remote_messages(self, self.context)
        else:
            result = None
        self.runtask.start(
            task,
            progress=self.progress,
            finish=self.action_completed,
            result=result,
        )

    def update_selected_remotes(self, remote):
        """Update the selected remotes when an ad-hoc remote is typed in"""
        self.selected_remotes = qtutils.selected_items(self.remotes, self.model.remotes)
        if remote not in self.selected_remotes:
            self.selected_remotes = [remote]
        worktree = self.context.git.worktree()
        self.selected_remotes_by_worktree[worktree] = self.selected_remotes

    def action_completed(self, task):
        """Grab the results of the action and finish up"""
        if not task.result or not isinstance(task.result, (list, tuple)):
            return

        status, out, err = task.result
        command = 'git %s' % self.action
        message = Interaction.format_command_status(command, status)
        details = Interaction.format_out_err(out, err)

        log_message = message
        if details:
            log_message += '\n\n' + details
        Interaction.log(log_message)

        if status == 0:
            close_on_completion = get(self.close_on_completion_checkbox)
            if close_on_completion:
                self.accept()
            return

        if self.action == PUSH:
            message += '\n\n'
            message += N_('Have you rebased/pulled lately?')

        Interaction.critical(self.windowTitle(), message=message, details=details)

    def export_state(self):
        """Export persistent settings"""
        state = standard.Dialog.export_state(self)
        state['close_on_completion'] = get(self.close_on_completion_checkbox)
        state['remote_messages'] = get(self.remote_messages_checkbox)
        state['selected_remotes'] = self.selected_remotes_by_worktree
        state['last_updated'] = self.last_updated
        return state

    def apply_state(self, state):
        """Apply persistent settings"""
        result = standard.Dialog.apply_state(self, state)
        # Restore the "close on completion" checkbox
        close_on_completion = bool(state.get('close_on_completion', True))
        self.close_on_completion_checkbox.setChecked(close_on_completion)
        # Restore the "show remote messages" checkbox
        remote_messages = bool(state.get('remote_messages', False))
        self.remote_messages_checkbox.setChecked(remote_messages)
        # Restore the selected remotes.
        self.selected_remotes_by_worktree = state.get('selected_remotes', {})
        self.last_updated = state.get('last_updated', 0.0)
        current_time = time.time()
        one_month = 60.0 * 60.0 * 24.0 * 31.0  # one month is ~31 days.
        if (current_time - self.last_updated) > one_month:
            self._prune_selected_remotes()
            self.last_updated = current_time
        # Selected remotes are stored per-worktree.
        worktree = self.context.git.worktree()
        selected_remotes = self.selected_remotes_by_worktree.get(worktree, [])
        if selected_remotes:
            # Restore the stored selection. We stash away the current selection so that
            # we can restore it in case we are unable to apply the stored selection.
            current_selection = self.remotes.selectedItems()
            self.remotes.clearSelection()
            selected = False
            for idx, remote in enumerate(selected_remotes):
                make_current = idx == 0 or not selected
                if self.select_remote_by_name(remote, make_current=make_current):
                    selected = True
            # Restore the original selection if nothing was selected.
            if not selected:
                for item in current_selection:
                    item.setSelected(True)
        return result

    def _prune_selected_remotes(self):
        """Prune stale worktrees from the persistent selected_remotes_by_worktree"""
        worktrees = list(self.selected_remotes_by_worktree.keys())
        for worktree in worktrees:
            if not os.path.exists(worktree):
                self.selected_remotes_by_worktree.pop(worktree, None)


# Use distinct classes so that each saves its own set of preferences
class Fetch(RemoteActionDialog):
    """Fetch from remote repositories"""

    def __init__(self, context, parent=None):
        super().__init__(context, FETCH, N_('Fetch'), parent=parent, icon=icons.repo())

    def export_state(self):
        """Export persistent settings"""
        state = RemoteActionDialog.export_state(self)
        state['tags'] = get(self.tags_checkbox)
        state['prune'] = get(self.prune_checkbox)
        return state

    def apply_state(self, state):
        """Apply persistent settings"""
        result = RemoteActionDialog.apply_state(self, state)
        tags = bool(state.get('tags', False))
        self.tags_checkbox.setChecked(tags)
        prune = bool(state.get('prune', False))
        self.prune_checkbox.setChecked(prune)
        return result


class Push(RemoteActionDialog):
    """Push to remote repositories"""

    def __init__(self, context, parent=None):
        super().__init__(context, PUSH, N_('Push'), parent=parent, icon=icons.push())

    def export_state(self):
        """Export persistent settings"""
        state = RemoteActionDialog.export_state(self)
        state['force'] = get(self.force_checkbox)
        state['prompt'] = get(self.prompt_checkbox)
        state['tags'] = get(self.tags_checkbox)
        return state

    def apply_state(self, state):
        """Apply persistent settings"""
        result = RemoteActionDialog.apply_state(self, state)
        # Restore the "force" checkbox
        force = bool(state.get('force', False))
        self.force_checkbox.setChecked(force)
        # Restore the "prompt on creation" checkbox
        prompt = bool(state.get('prompt', True))
        self.prompt_checkbox.setChecked(prompt)
        # Restore the "tags" checkbox
        tags = bool(state.get('tags', False))
        self.tags_checkbox.setChecked(tags)
        return result


class Pull(RemoteActionDialog):
    """Pull from remote repositories"""

    def __init__(self, context, parent=None):
        super().__init__(context, PULL, N_('Pull'), parent=parent, icon=icons.pull())

    def apply_state(self, state):
        """Apply persistent settings"""
        result = RemoteActionDialog.apply_state(self, state)
        # Rebase has the highest priority
        rebase = bool(state.get('rebase', False))
        self.rebase_checkbox.setChecked(rebase)

        ff_only = not rebase and bool(state.get('ff_only', False))
        no_ff = not rebase and not ff_only and bool(state.get('no_ff', False))
        self.no_ff_checkbox.setChecked(no_ff)
        # Allow users coming from older versions that have rebase=False to
        # pickup the new ff_only=True default by only setting ff_only False
        # when it either exists in the config or when rebase=True.
        if 'ff_only' in state or rebase:
            self.ff_only_checkbox.setChecked(ff_only)
        return result

    def export_state(self):
        """Export persistent settings"""
        state = RemoteActionDialog.export_state(self)
        state['ff_only'] = get(self.ff_only_checkbox)
        state['no_ff'] = get(self.no_ff_checkbox)
        state['rebase'] = get(self.rebase_checkbox)
        return state
