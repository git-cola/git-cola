import fnmatch
import time

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import gitcmds
from cola import qtutils
from cola import utils
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import main
from cola.qtutils import connect_button
from cola.widgets import defs
from cola.widgets import standard

FETCH = 'Fetch'
PUSH = 'Push'
PULL = 'Pull'


def fetch():
    return run(Fetch)


def push():
    return run(Push)


def pull():
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
    view = RemoteDialog(model, parent)
    view.show()
    return view


def combine(result, existing):
    if existing is None:
        return result

    if type(existing) is tuple:
        if len(existing) == 3:
            return (max(existing[0], result[0]),
                    combine(existing[1], result[1]),
                    combine(existing[2], result[2]))
        else:
            raise AssertionError('combine() with length %d' % len(existing))
    else:
        if existing and result:
            return existing + '\n\n' + result
        elif existing:
            return existing
        else:
            return result


class ActionTask(QtCore.QRunnable):

    def __init__(self, sender, model_action, remote, kwargs):
        QtCore.QRunnable.__init__(self)
        self.sender = sender
        self.model_action = model_action
        self.remote = remote
        self.kwargs = kwargs

    def run(self):
        """Runs the model action and captures the result"""
        status, out, err = self.model_action(self.remote, **self.kwargs)
        self.sender.emit(SIGNAL('action_completed'), self, status, out, err)


class ProgressAnimationThread(QtCore.QThread):

    def __init__(self, txt, parent, timeout=0.25):
        QtCore.QThread.__init__(self, parent)
        self.running = False
        self.txt = txt
        self.timeout = timeout
        self.symbols = [
            '..   ',
            '...  ',
            '.... ',
            '.....',
            '.... ',
            '...  '
        ]
        self.idx = -1

    def next(self):
        self.idx = (self.idx + 1) % len(self.symbols)
        return self.txt + self.symbols[self.idx]

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            self.emit(SIGNAL('str'), self.next())
            time.sleep(self.timeout)


class RemoteActionDialog(standard.Dialog):

    def __init__(self, model, action, parent):
        """Customizes the dialog based on the remote action
        """
        standard.Dialog.__init__(self, parent=parent)
        self.model = model
        self.action = action
        self.tasks = []
        self.filtered_remote_branches = []
        self.selected_remotes = []

        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowModality(Qt.WindowModal)
        self.setWindowTitle(N_(action))

        self.progress = QtGui.QProgressDialog(self)
        self.progress.setFont(qtutils.diff_font())
        self.progress.setRange(0, 0)
        self.progress.setCancelButton(None)
        self.progress.setWindowTitle(action)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setLabelText(N_('Updating') + '..   ')
        self.progress_thread = ProgressAnimationThread(N_('Updating'), self)

        self.local_label = QtGui.QLabel()
        self.local_label.setText(N_('Local Branch'))

        self.local_branch = QtGui.QLineEdit()
        self.local_branches = QtGui.QListWidget()
        self.local_branches.addItems(self.model.local_branches)

        self.remote_label = QtGui.QLabel()
        self.remote_label.setText(N_('Remote'))

        self.remote_name = QtGui.QLineEdit()
        self.remotes = QtGui.QListWidget()
        if action == PUSH:
            self.remotes.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.remotes.addItems(self.model.remotes)

        self.remote_branch_label = QtGui.QLabel()
        self.remote_branch_label.setText(N_('Remote Branch'))

        self.remote_branch = QtGui.QLineEdit()
        self.remote_branches = QtGui.QListWidget()
        self.remote_branches.addItems(self.model.remote_branches)

        self.ffwd_only_checkbox = QtGui.QCheckBox()
        self.ffwd_only_checkbox.setText(N_('Fast Forward Only '))
        self.ffwd_only_checkbox.setChecked(True)

        self.tags_checkbox = QtGui.QCheckBox()
        self.tags_checkbox.setText(N_('Include tags '))

        self.rebase_checkbox = QtGui.QCheckBox()
        self.rebase_checkbox.setText(N_('Rebase '))

        self.action_button = QtGui.QPushButton()
        self.action_button.setText(N_(action))
        self.action_button.setIcon(qtutils.ok_icon())

        self.close_button = QtGui.QPushButton()
        self.close_button.setText(N_('Close'))
        self.close_button.setIcon(qtutils.close_icon())

        self.local_branch_layout = QtGui.QHBoxLayout()
        self.local_branch_layout.addWidget(self.local_label)
        self.local_branch_layout.addWidget(self.local_branch)

        self.remote_branch_layout = QtGui.QHBoxLayout()
        self.remote_branch_layout.addWidget(self.remote_label)
        self.remote_branch_layout.addWidget(self.remote_name)

        self.remote_branches_layout = QtGui.QHBoxLayout()
        self.remote_branches_layout.addWidget(self.remote_branch_label)
        self.remote_branches_layout.addWidget(self.remote_branch)

        self.options_layout = QtGui.QHBoxLayout()
        self.options_layout.setSpacing(defs.button_spacing)
        self.options_layout.addStretch()
        self.options_layout.addWidget(self.ffwd_only_checkbox)
        self.options_layout.addWidget(self.tags_checkbox)
        self.options_layout.addWidget(self.rebase_checkbox)
        self.options_layout.addWidget(self.action_button)
        self.options_layout.addWidget(self.close_button)

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.setMargin(defs.margin)
        self.main_layout.setSpacing(defs.spacing)
        self.main_layout.addLayout(self.remote_branch_layout)
        self.main_layout.addWidget(self.remotes)
        if action == PUSH:
            self.main_layout.addLayout(self.local_branch_layout)
            self.main_layout.addWidget(self.local_branches)
            self.main_layout.addLayout(self.remote_branches_layout)
            self.main_layout.addWidget(self.remote_branches)
        else: # fetch and pull
            self.main_layout.addLayout(self.remote_branches_layout)
            self.main_layout.addWidget(self.remote_branches)
            self.main_layout.addLayout(self.local_branch_layout)
            self.main_layout.addWidget(self.local_branches)
        self.main_layout.addLayout(self.options_layout)
        self.setLayout(self.main_layout)

        remotes = self.model.remotes
        if 'origin' in remotes:
            idx = remotes.index('origin')
            if self.select_remote(idx):
                self.remote_name.setText('origin')
        else:
            if self.select_first_remote():
                self.remote_name.setText(remotes[0])

        # Trim the remote list to just the default remote
        self.update_remotes()
        self.set_field_defaults()

        # Setup signals and slots
        self.connect(self.remotes, SIGNAL('itemSelectionChanged()'),
                     self.update_remotes)

        self.connect(self.local_branches, SIGNAL('itemSelectionChanged()'),
                     self.update_local_branches)

        self.connect(self.remote_branches, SIGNAL('itemSelectionChanged()'),
                     self.update_remote_branches)

        connect_button(self.action_button, self.action_callback)
        connect_button(self.close_button, self.close)

        qtutils.add_action(self, N_('Close'),
                      self.close, QtGui.QKeySequence.Close, 'Esc')

        self.connect(self, SIGNAL('action_completed'), self.action_completed)
        self.connect(self.progress_thread, SIGNAL('str'), self.update_progress)

        if action == PULL:
            self.tags_checkbox.hide()
            self.ffwd_only_checkbox.hide()
            self.local_label.hide()
            self.local_branch.hide()
            self.local_branches.hide()
            self.remote_branch.setFocus()
        else:
            self.rebase_checkbox.hide()

        if not qtutils.apply_state(self):
            self.resize(666, 420)

        self.remote_name.setFocus()

    def set_rebase(self, value):
        self.rebase_checkbox.setChecked(value)

    def set_field_defaults(self):
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
        self.remote_name.setText(remote_name)
        if remote_name:
            self.remote_name.selectAll()

    def set_local_branch(self, branch):
        self.local_branch.setText(branch)
        if branch:
            self.local_branch.selectAll()

    def set_remote_branch(self, branch):
        self.remote_branch.setText(branch)
        if branch:
            self.remote_branch.selectAll()

    def set_remote_branches(self, branches):
        self.remote_branches.clear()
        self.remote_branches.addItems(branches)
        self.filtered_remote_branches = branches

    def select_first_remote(self):
        """Selects the first remote in the list view"""
        return self.select_remote(0)

    def select_remote(self, idx):
        """Selects a remote by index"""
        item = self.remotes.item(idx)
        if item:
            self.remotes.setItemSelected(item, True)
            self.remotes.setCurrentItem(item)
            self.set_remote_name(unicode(item.text()))
            return True
        else:
            return False

    def select_local_branch(self, idx):
        """Selects a local branch by index in the list view"""
        item = self.local_branches.item(idx)
        if not item:
            return False
        self.local_branches.setItemSelected(item, True)
        self.local_branches.setCurrentItem(item)
        self.local_branch.setText(item.text())
        return True

    def display_remotes(self, widget):
        """Display the available remotes in a listwidget"""
        displayed = []
        for remote_name in self.model.remotes:
            url = self.model.remote_url(remote_name, self.action)
            display = ('%s\t(%s)'
                       % (remote_name, N_('URL: %s') % url))
            displayed.append(display)
        qtutils.set_items(widget,displayed)

    def update_remotes(self, *rest):
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

        all_branches = gitcmds.branch_list(remote=True)
        branches = []
        patterns = []
        for remote in self.selected_remotes:
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

    def update_local_branches(self,*rest):
        """Update the local/remote branch names when a branch is selected"""
        branches = self.model.local_branches
        widget = self.local_branches
        selection = qtutils.selected_item(widget, branches)
        if not selection:
            return
        self.set_local_branch(selection)
        self.set_remote_branch(selection)

    def update_remote_branches(self,*rest):
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
        """Returns git arguments common to fetch/push/pulll"""
        remote_name = unicode(self.remote_name.text())
        local_branch = unicode(self.local_branch.text())
        remote_branch = unicode(self.remote_branch.text())

        ffwd_only = self.ffwd_only_checkbox.isChecked()
        rebase = self.rebase_checkbox.isChecked()
        tags = self.tags_checkbox.isChecked()

        return (remote_name,
                {
                    'local_branch': local_branch,
                    'remote_branch': remote_branch,
                    'ffwd': ffwd_only,
                    'rebase': rebase,
                    'tags': tags,
                })

    # Actions

    def action_callback(self):
        action = self.action
        if action == FETCH:
            model_action = self.model.fetch
        elif action == PUSH:
            model_action = self.push_to_all
        else: # if action == PULL:
            model_action = self.model.pull

        remote_name = unicode(self.remote_name.text())
        if not remote_name:
            errmsg = N_('No repository selected.')
            Interaction.log(errmsg)
            return
        remote, kwargs = self.common_args()
        self.selected_remotes = qtutils.selected_items(self.remotes,
                                                       self.model.remotes)

        # Check if we're about to create a new branch and warn.
        remote_branch = unicode(self.remote_branch.text())
        local_branch = unicode(self.local_branch.text())

        if action == PUSH and not remote_branch:
            branch = local_branch
            candidate = '%s/%s' % (remote, branch)
            if candidate not in self.model.remote_branches:
                title = N_('Push')
                args = dict(branch=branch, remote=remote)
                msg = N_('Branch "%(branch)s" does not exist in "%(remote)s".\n'
                         'A new remote branch will be published.') % args
                info_txt= N_('Create a new remote branch?')
                ok_text = N_('Create Remote Branch')
                if not qtutils.confirm(title, msg, info_txt, ok_text,
                                       default=False,
                                       icon=qtutils.git_icon()):
                    return

        if not self.ffwd_only_checkbox.isChecked():
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
            else: # pull: shouldn't happen since the controls are hidden
                msg = "You probably don't want to do this.\n\tContinue?"
                return

            if not qtutils.confirm(title, msg, info_txt, ok_text,
                                   default=False,
                                   icon=qtutils.discard_icon()):
                return

        # Disable the GUI by default
        self.action_button.setEnabled(False)
        self.close_button.setEnabled(False)
        QtGui.QApplication.setOverrideCursor(Qt.WaitCursor)

        # Show a nice progress bar
        self.progress.show()
        self.progress_thread.start()

        # Use a thread to update in the background
        task = ActionTask(self, model_action, remote, kwargs)
        self.tasks.append(task)
        QtCore.QThreadPool.globalInstance().start(task)

    def update_progress(self, txt):
        self.progress.setLabelText(txt)

    def push_to_all(self, dummy_remote, *args, **kwargs):
        selected_remotes = self.selected_remotes
        all_results = None
        for remote in selected_remotes:
            result = self.model.push(remote, *args, **kwargs)
            all_results = combine(result, all_results)
        return all_results

    def action_completed(self, task, status, out, err):
        # Grab the results of the action and finish up
        self.action_button.setEnabled(True)
        self.close_button.setEnabled(True)
        QtGui.QApplication.restoreOverrideCursor()

        self.progress_thread.stop()
        self.progress_thread.wait()
        self.progress.close()
        if task in self.tasks:
            self.tasks.remove(task)

        already_up_to_date = N_('Already up-to-date.')

        if not out: # git fetch --tags --verbose doesn't print anything...
            out = already_up_to_date

        command = 'git %s' % self.action.lower()
        message = (N_('"%(command)s" returned exit status %(status)d') %
                   dict(command=command, status=status))
        if out:
            message += '\n\n' + out
        if err:
            message += '\n\n' + err

        Interaction.log(message)

        if status == 0:
            self.accept()
            return

        if self.action == PUSH:
            message += '\n\n'
            message += N_('Have you rebased/pulled lately?')

        Interaction.critical(self.windowTitle(),
                             message=message, details=output)


# Use distinct classes so that each saves its own set of preferences
class Fetch(RemoteActionDialog):
    def __init__(self, model, parent):
        RemoteActionDialog.__init__(self, model, FETCH, parent)


class Push(RemoteActionDialog):
    def __init__(self, model, parent):
        RemoteActionDialog.__init__(self, model, PUSH, parent)


class Pull(RemoteActionDialog):
    def __init__(self, model, parent):
        RemoteActionDialog.__init__(self, model, PULL, parent)

    def apply_state(self, state):
        RemoteActionDialog.apply_state(self, state)
        try:
            rebase = state['rebase']
        except KeyError:
            pass
        else:
            self.rebase_checkbox.setChecked(rebase)

    def export_state(self):
        state = RemoteActionDialog.export_state(self)
        state['rebase'] = self.rebase_checkbox.isChecked()
        return state

    def done(self, exit_code):
        qtutils.save_state(self)
        return RemoteActionDialog.done(self, exit_code)
