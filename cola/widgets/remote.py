"""Widgets for Fetch, Push, and Pull"""
from __future__ import division, absolute_import, unicode_literals
import fnmatch

from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from ..i18n import N_
from ..interaction import Interaction
from ..models import main
from ..qtutils import connect_button
from .. import gitcmds
from .. import icons
from .. import qtutils
from .. import utils
from .standard import ProgressDialog
from . import defs
from . import standard


FETCH = 'FETCH'
PUSH = 'PUSH'
PULL = 'PULL'


def fetch():
    """Fetch from remote repositories"""
    return run(Fetch)


def push():
    """Push to remote repositories"""
    return run(Push)


def pull():
    """Pull from remote repositories"""
    return run(Pull)


def run(RemoteDialog):
    """Launches fetch/push/pull dialogs."""
    # Copy global stuff over to speedup startup
    model = main.MainModel()
    global_model = main.model()
    model.currentbranch = global_model.currentbranch
    model.local_branches = global_model.local_branches
    model.remote_branches = global_model.remote_branches
    model.tags = global_model.tags
    model.remotes = global_model.remotes
    parent = qtutils.active_window()
    view = RemoteDialog(model, parent=parent)
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
        combined = (max(prev[0], result[0]),
                    combine(prev[1], result[1]),
                    combine(prev[2], result[2]))
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

    e.g. "origin/master" becomes "master".

    """
    branches = [utils.strip_one(branch) for branch in remote_branches]
    return [branch for branch in branches if branch != 'HEAD']


class ActionTask(qtutils.Task):
    """Run actions asynchronously"""

    def __init__(self, parent, model_action, remote, kwargs):
        qtutils.Task.__init__(self, parent)
        self.model_action = model_action
        self.remote = remote
        self.kwargs = kwargs

    def task(self):
        """Runs the model action and captures the result"""
        return self.model_action(self.remote, **self.kwargs)


class RemoteActionDialog(standard.Dialog):
    """Interface for performing remote operations"""

    def __init__(self, model, action, title, parent=None, icon=None):
        """Customize the dialog based on the remote action"""

        standard.Dialog.__init__(self, parent=parent)
        self.model = model
        self.action = action
        self.filtered_remote_branches = []
        self.selected_remotes = []

        self.setWindowTitle(title)
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.runtask = qtutils.RunTask(parent=self)
        self.progress = ProgressDialog(title, N_('Updating'), self)

        self.local_label = QtWidgets.QLabel()
        self.local_label.setText(N_('Local Branch'))

        self.local_branch = QtWidgets.QLineEdit()
        qtutils.add_completer(self.local_branch, self.model.local_branches)

        self.local_branches = QtWidgets.QListWidget()
        self.local_branches.addItems(self.model.local_branches)

        self.remote_label = QtWidgets.QLabel()
        self.remote_label.setText(N_('Remote'))

        self.remote_name = QtWidgets.QLineEdit()
        qtutils.add_completer(self.remote_name, self.model.remotes)
        self.remote_name.editingFinished.connect(self.remote_name_edited)
        self.remote_name.textEdited.connect(lambda x: self.remote_name_edited())

        self.remotes = QtWidgets.QListWidget()
        if action == PUSH:
            mode = QtWidgets.QAbstractItemView.ExtendedSelection
            self.remotes.setSelectionMode(mode)
        self.remotes.addItems(self.model.remotes)

        self.remote_branch_label = QtWidgets.QLabel()
        self.remote_branch_label.setText(N_('Remote Branch'))

        self.remote_branch = QtWidgets.QLineEdit()
        remote_branches = strip_remotes(self.model.remote_branches)
        qtutils.add_completer(self.remote_branch, remote_branches)

        self.remote_branches = QtWidgets.QListWidget()
        self.remote_branches.addItems(self.model.remote_branches)

        text = N_('Prompt on creation')
        tooltip = N_('Prompt when pushing creates new remote branches')
        self.prompt_checkbox = qtutils.checkbox(checked=True, text=text,
                                                tooltip=tooltip)

        text = N_('Fast-forward only')
        tooltip = N_('Refuse to merge unless the current HEAD is already up-'
                     'to-date or the merge can be resolved as a fast-forward')
        self.ff_only_checkbox = qtutils.checkbox(checked=True,
                                                 text=text, tooltip=tooltip)

        text = N_('No fast-forward')
        tooltip = N_('Create a merge commit even when the merge resolves as a '
                     'fast-forward')
        self.no_ff_checkbox = qtutils.checkbox(checked=False,
                                               text=text, tooltip=tooltip)
        text = N_('Force')
        tooltip = N_('Allow non-fast-forward updates.  Using "force" can '
                     'cause the remote repository to lose commits; '
                     'use it with care')
        self.force_checkbox = qtutils.checkbox(checked=False, text=text,
                                               tooltip=tooltip)

        self.tags_checkbox = qtutils.checkbox(text=N_('Include tags '))

        tooltip = N_('Rebase the current branch instead of merging')
        self.rebase_checkbox = qtutils.checkbox(text=N_('Rebase'),
                                                tooltip=tooltip)

        text = N_('Set upstream')
        tooltip = N_('Configure the remote branch as the the new upstream')
        self.upstream_checkbox = qtutils.checkbox(text=text, tooltip=tooltip)

        self.action_button = qtutils.ok_button(title, icon=icon)
        self.close_button = qtutils.close_button()

        self.buttons = utils.Group(self.action_button, self.close_button)

        self.local_branch_layout = qtutils.hbox(
            defs.small_margin,
            defs.spacing,
            self.local_label,
            self.local_branch)

        self.remote_layout = qtutils.hbox(
            defs.small_margin,
            defs.spacing,
            self.remote_label,
            self.remote_name)

        self.remote_branch_layout = qtutils.hbox(
            defs.small_margin,
            defs.spacing,
            self.remote_branch_label,
            self.remote_branch)

        self.options_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.ff_only_checkbox,
            self.no_ff_checkbox,
            self.tags_checkbox,
            self.rebase_checkbox,
            self.upstream_checkbox,
            self.prompt_checkbox,
            self.force_checkbox,
            qtutils.STRETCH,
            self.close_button,
            self.action_button)

        self.remote_input_layout = qtutils.vbox(
            defs.no_margin, defs.spacing,
            self.remote_layout, self.remotes)

        self.local_branch_input_layout = qtutils.vbox(
            defs.no_margin, defs.spacing,
            self.local_branch_layout, self.local_branches)

        self.remote_branch_input_layout = qtutils.vbox(
            defs.no_margin, defs.spacing,
            self.remote_branch_layout, self.remote_branches)

        if action == PUSH:
            widgets = (
                self.remote_input_layout,
                self.local_branch_input_layout,
                self.remote_branch_input_layout)
        else:  # fetch and pull
            widgets = (
                self.remote_input_layout,
                self.remote_branch_input_layout,
                self.local_branch_input_layout)
        self.top_layout = qtutils.hbox(defs.no_margin, defs.spacing, *widgets)

        self.main_layout = qtutils.vbox(
            defs.no_margin, defs.spacing,
            self.top_layout, self.options_layout)
        self.setLayout(self.main_layout)

        default_remote = gitcmds.default_remote() or 'origin'

        remotes = self.model.remotes
        if default_remote in remotes:
            idx = remotes.index(default_remote)
            if self.select_remote(idx):
                self.set_remote_name(default_remote)
        else:
            if self.select_first_remote():
                self.set_remote_name(remotes[0])

        # Trim the remote list to just the default remote
        self.update_remotes()
        self.set_field_defaults()

        # Setup signals and slots
        self.remotes.itemSelectionChanged.connect(self.update_remotes)

        local = self.local_branches
        local.itemSelectionChanged.connect(self.update_local_branches)

        remote = self.remote_branches
        remote.itemSelectionChanged.connect(self.update_remote_branches)

        self.no_ff_checkbox.toggled.connect(
            lambda x: uncheck(x, self.ff_only_checkbox, self.rebase_checkbox))

        self.ff_only_checkbox.toggled.connect(
            lambda x: uncheck(x, self.no_ff_checkbox, self.rebase_checkbox))

        self.rebase_checkbox.toggled.connect(
            lambda x: uncheck(x, self.no_ff_checkbox, self.ff_only_checkbox))

        connect_button(self.action_button, self.action_callback)
        connect_button(self.close_button, self.close)

        qtutils.add_action(self, N_('Close'), self.close,
                           QtGui.QKeySequence.Close, 'Esc')

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

        desktop = qtutils.desktop()
        width = desktop.width()//2
        height = desktop.height() - desktop.height()//4
        self.init_state(None, self.resize, width, height)

    def set_rebase(self, value):
        """Check the rebase checkbox"""
        self.rebase_checkbox.setChecked(value)

    def set_field_defaults(self):
        """Set sensible initial defaults"""
        # Default to "git fetch origin master"
        action = self.action
        if action == FETCH or action == PULL:
            self.local_branch.setText('')
            self.remote_branch.setText('')
            return

        # Select the current branch by default for push
        if action == PUSH:
            branch = self.model.currentbranch
            try:
                idx = self.model.local_branches.index(branch)
            except ValueError:
                return
            if self.select_local_branch(idx):
                self.set_local_branch(branch)
            self.set_remote_branch('')

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

    def select_remote(self, idx):
        """Select a remote by index"""
        item = self.remotes.item(idx)
        if item:
            item.setSelected(True)
            self.remotes.setCurrentItem(item)
            self.set_remote_name(item.text())
            result = True
        else:
            result = False
        return result

    def select_local_branch(self, idx):
        """Selects a local branch by index in the list view"""
        item = self.local_branches.item(idx)
        if item:
            item.setSelected(True)
            self.local_branches.setCurrentItem(item)
            self.local_branch.setText(item.text())
            result = True
        else:
            result = False
        return result

    def display_remotes(self, widget):
        """Display the available remotes in a listwidget"""
        displayed = []
        for remote_name in self.model.remotes:
            url = self.model.remote_url(remote_name, self.action)
            display = ('%s\t(%s)'
                       % (remote_name, N_('URL: %s') % url))
            displayed.append(display)
        qtutils.set_items(widget, displayed)

    def update_remotes(self):
        """Update the remote name when a remote from the list is selected"""
        widget = self.remotes
        remotes = self.model.remotes
        selection = qtutils.selected_item(widget, remotes)
        if not selection:
            self.selected_remotes = []
            return
        self.set_remote_name(selection)
        self.selected_remotes = qtutils.selected_items(self.remotes,
                                                       self.model.remotes)
        self.set_remote_to(selection, self.selected_remotes)

    def set_remote_to(self, remote, selected_remotes):
        all_branches = gitcmds.branch_list(remote=True)
        branches = []
        patterns = []
        for remote in selected_remotes:
            pat = remote + '/*'
            patterns.append(pat)

        for branch in all_branches:
            for pat in patterns:
                if fnmatch.fnmatch(branch, pat):
                    branches.append(branch)
                    break
        if branches:
            self.set_remote_branches(branches)
        else:
            self.set_remote_branches(all_branches)
        self.set_remote_branch('')

    def remote_name_edited(self):
        """Update the current remote when the remote name is typed manually"""
        remote = self.remote_name.text()
        self.set_remote_to(remote, [remote])

    def update_local_branches(self):
        """Update the local/remote branch names when a branch is selected"""
        branches = self.model.local_branches
        widget = self.local_branches
        selection = qtutils.selected_item(widget, branches)
        if not selection:
            return
        self.set_local_branch(selection)
        self.set_remote_branch(selection)

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

    def common_args(self):
        """Returns git arguments common to fetch/push/pull"""
        remote_name = self.remote_name.text()
        local_branch = self.local_branch.text()
        remote_branch = self.remote_branch.text()

        ff_only = self.ff_only_checkbox.isChecked()
        force = self.force_checkbox.isChecked()
        no_ff = self.no_ff_checkbox.isChecked()
        rebase = self.rebase_checkbox.isChecked()
        set_upstream = self.upstream_checkbox.isChecked()
        tags = self.tags_checkbox.isChecked()

        return (remote_name,
                {
                    'ff_only': ff_only,
                    'force': force,
                    'local_branch': local_branch,
                    'no_ff': no_ff,
                    'rebase': rebase,
                    'remote_branch': remote_branch,
                    'set_upstream': set_upstream,
                    'tags': tags,
                })

    # Actions

    def push_to_all(self, dummy_remote, *args, **kwargs):
        """Push to all selected remotes"""
        selected_remotes = self.selected_remotes
        all_results = None
        for remote in selected_remotes:
            result = self.model.push(remote, *args, **kwargs)
            all_results = combine(result, all_results)
        return all_results

    def action_callback(self):
        """Perform the actual fetch/push/pull operation"""
        action = self.action
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
        self.selected_remotes = qtutils.selected_items(self.remotes,
                                                       self.model.remotes)

        # Check if we're about to create a new branch and warn.
        remote_branch = self.remote_branch.text()
        local_branch = self.local_branch.text()

        if action == PUSH and not remote_branch:
            branch = local_branch
            candidate = '%s/%s' % (remote, branch)
            prompt = self.prompt_checkbox.isChecked()

            if prompt and candidate not in self.model.remote_branches:
                title = N_('Push')
                args = dict(branch=branch, remote=remote)
                msg = N_('Branch "%(branch)s" does not exist in "%(remote)s".\n'
                         'A new remote branch will be published.') % args
                info_txt = N_('Create a new remote branch?')
                ok_text = N_('Create Remote Branch')
                if not qtutils.confirm(title, msg, info_txt, ok_text,
                                       icon=icons.cola()):
                    return

        if self.force_checkbox.isChecked():
            if action == FETCH:
                title = N_('Force Fetch?')
                msg = N_('Non-fast-forward fetch overwrites local history!')
                info_txt = N_('Force fetching from %s?') % remote
                ok_text = N_('Force Fetch')
            elif action == PUSH:
                title = N_('Force Push?')
                msg = N_('Non-fast-forward push overwrites published '
                         'history!\n(Did you pull first?)')
                info_txt = N_('Force push to %s?') % remote
                ok_text = N_('Force Push')
            else:  # pull: shouldn't happen since the controls are hidden
                return
            if not qtutils.confirm(title, msg, info_txt, ok_text,
                                   default=False, icon=icons.discard()):
                return

        # Disable the GUI by default
        self.buttons.setEnabled(False)

        # Use a thread to update in the background
        task = ActionTask(self, model_action, remote, kwargs)
        self.runtask.start(task,
                           progress=self.progress,
                           finish=self.action_completed)

    def action_completed(self, task):
        """Grab the results of the action and finish up"""
        status, out, err = task.result
        self.buttons.setEnabled(True)

        command = 'git %s' % self.action.lower()
        message = (N_('"%(command)s" returned exit status %(status)d') %
                   dict(command=command, status=status))
        details = ''
        if out:
            details = out
        if err:
            details += '\n\n' + err

        log_message = message
        if details:
            log_message += '\n\n' + details
        Interaction.log(log_message)

        if status == 0:
            self.accept()
            return

        if self.action == PUSH:
            message += '\n\n'
            message += N_('Have you rebased/pulled lately?')

        Interaction.critical(self.windowTitle(),
                             message=message, details=details)


# Use distinct classes so that each saves its own set of preferences
class Fetch(RemoteActionDialog):
    """Fetch from remote repositories"""

    def __init__(self, model, parent=None):
        RemoteActionDialog.__init__(self, model, FETCH, N_('Fetch'),
                                    parent=parent, icon=icons.repo())

    def export_state(self):
        """Export persistent settings"""
        state = RemoteActionDialog.export_state(self)
        state['tags'] = self.tags_checkbox.isChecked()
        return state

    def apply_state(self, state):
        """Apply persistent settings"""
        result = RemoteActionDialog.apply_state(self, state)
        tags = bool(state.get('tags', False))
        self.tags_checkbox.setChecked(tags)
        return result


class Push(RemoteActionDialog):
    """Push to remote repositories"""

    def __init__(self, model, parent=None):
        RemoteActionDialog.__init__(self, model, PUSH, N_('Push'),
                                    parent=parent, icon=icons.push())

    def export_state(self):
        """Export persistent settings"""
        state = RemoteActionDialog.export_state(self)
        state['tags'] = self.tags_checkbox.isChecked()
        state['prompt'] = self.prompt_checkbox.isChecked()
        return state

    def apply_state(self, state):
        """Apply persistent settings"""
        result = RemoteActionDialog.apply_state(self, state)

        tags = bool(state.get('tags', False))
        self.tags_checkbox.setChecked(tags)

        prompt = bool(state.get('prompt', True))
        self.prompt_checkbox.setChecked(prompt)
        return result


class Pull(RemoteActionDialog):
    """Pull from remote repositories"""

    def __init__(self, model, parent=None):
        RemoteActionDialog.__init__(self, model, PULL, N_('Pull'),
                                    parent=parent, icon=icons.pull())

    def apply_state(self, state):
        """Apply persistent settings"""
        result = RemoteActionDialog.apply_state(self, state)
        # Rebase has the highest priority
        rebase = bool(state.get('rebase', False))
        ff_only = not rebase and bool(state.get('ff_only', False))
        no_ff = not rebase and not ff_only and bool(state.get('no_ff', False))

        self.rebase_checkbox.setChecked(rebase)
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

        state['ff_only'] = self.ff_only_checkbox.isChecked()
        state['no_ff'] = self.no_ff_checkbox.isChecked()
        state['rebase'] = self.rebase_checkbox.isChecked()

        return state
