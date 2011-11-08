"""This controller handles the remote dialog."""

import fnmatch
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import gitcmds
from cola import utils
from cola import qtutils
from cola.views import remote
from cola.qobserver import QObserver
from cola.main.model import MainModel

def remote_action(action):
    """Launches fetch/push/pull dialogs."""
    # TODO: subclass model
    model = MainModel()

    global_model = cola.model()
    model.currentbranch = global_model.currentbranch
    model.local_branches = global_model.local_branches
    model.remote_branches = global_model.remote_branches
    model.tags = global_model.tags
    model.remotes = global_model.remotes

    model.local_branch = ''
    model.remote_branch = ''
    model.remotename = ''
    model.tags_checkbox = False
    model.rebase_checkbox = False
    model.ffwd_only_checkbox = True

    view = remote.RemoteView(qtutils.active_window(), action)
    ctl = RemoteController(model, view, action)
    view.show()
    return ctl


class RemoteController(QObserver):
    """Provides control for the remote-action dialog."""
    def __init__(self, model, view, action):
        QObserver.__init__(self, model, view)
        self.add_observables('remotename',
                             'remotes',
                             'local_branch',
                             'local_branches',
                             'remote_branch',
                             'remote_branches',
                             'tags_checkbox',
                             'rebase_checkbox',
                             'ffwd_only_checkbox')
        self.action = action
        """The current mode; one of fetch/push/pull"""

        self.action_method = {
            'fetch': self.gen_remote_callback(self.model.fetch_helper),
            'push': self.gen_remote_callback(self.model.push_helper),
            'pull': self.gen_remote_callback(self.model.pull_helper),
        }   [action]
        self._tasks = []
        self.progress = QtGui.QProgressDialog(self.view)
        self.progress.setRange(0, 0)
        self.progress.setCancelButton(None)
        self.progress.setWindowTitle('git ' + action)
        self.progress.setWindowModality(Qt.WindowModal)
        """Callbacks corresponding to the 3 (fetch/push/pull) modes"""

        self.add_actions(remotes = self.display_remotes)
        self.add_callbacks(action_button = self.action_method,
                           remotes = self.update_remotes,
                           local_branches = self.update_local_branches,
                           remote_branches = self.update_remote_branches)
        self.view.connect(self.view, SIGNAL('action_completed'),
                          self._action_completed)
        self.refresh_view()
        remotes = self.model.remotes
        if 'origin' in remotes:
            idx = remotes.index('origin')
            if self.view.select_remote(idx):
                self.model.set_remotename('origin')
        else:
            if self.view.select_first_remote():
                self.model.set_remotename(remotes[0])

        # Trim the remote list to just the default remote
        self.update_remotes()

        # Default to "git fetch origin master"
        if action == 'fetch' or action == 'pull':
            self.model.set_local_branch('')
            self.model.set_remote_branch('')
            return

        # Select the current branch by default for push
        if action == 'push':
            branch = self.model.currentbranch
            try:
                idx = self.model.local_branches.index(branch)
            except ValueError:
                return
            if self.view.select_local_branch(idx):
                self.model.set_local_branch(branch)
            self.model.set_remote_branch('')

    def display_remotes(self, widget):
        """Display the available remotes in a listwidget"""
        displayed = []
        for remotename in self.model.remotes:
            url = self.model.remote_url(remotename, self.action)
            display = ('%s\t(%s %s)'
                       % (remotename, unicode(self.tr('URL:')), url))
            displayed.append(display)
        qtutils.set_items(widget,displayed)

    def update_remotes(self,*rest):
        """Update the remote name when a remote from the list is selected"""
        widget = self.view.remotes
        remotes = self.model.remotes
        selection = qtutils.selected_item(widget, remotes)
        if not selection:
            return
        self.model.set_remotename(selection)
        self.view.remotename.selectAll()

        if self.action != 'pull':
            pass
        all_branches = gitcmds.branch_list(remote=True)
        branches = []
        pat = selection + '/*'
        for branch in all_branches:
            if fnmatch.fnmatch(branch, pat):
                branches.append(branch)
        if branches:
            self.model.set_remote_branches(branches)
        else:
            self.model.set_remote_branches(all_branches)
        self.model.set_remote_branch('')

    def update_local_branches(self,*rest):
        """Update the local/remote branch names when a branch is selected"""
        branches = self.model.local_branches
        widget = self.view.local_branches
        selection = qtutils.selected_item(widget, branches)
        if not selection:
            return

        self.model.set_local_branch(selection)
        self.model.set_remote_branch(selection)

        self.view.local_branch.selectAll()
        self.view.remote_branch.selectAll()

    def update_remote_branches(self,*rest):
        """Update the remote branch name when a branch is selected"""
        widget = self.view.remote_branches
        branches = self.model.remote_branches
        selection = qtutils.selected_item(widget,branches)
        if not selection:
            return
        branch = utils.basename(selection)
        if branch == 'HEAD':
            return
        self.model.set_remote_branch(branch)
        self.view.remote_branch.selectAll()

    def common_args(self):
        """Returns git arguments common to fetch/push/pulll"""
        # TODO move to model
        return (self.model.remotename,
                {
                    'local_branch': self.model.local_branch,
                    'remote_branch': self.model.remote_branch,
                    'ffwd': self.model.ffwd_only_checkbox,
                    'tags': self.model.tags_checkbox,
                    'rebase': self.model.rebase_checkbox,
                })

    #+-------------------------------------------------------------
    #+ Actions
    def gen_remote_callback(self, modelaction):
        """Generates a Qt callback for fetch/push/pull.
        """
        def remote_callback():
            if not self.model.remotename:
                errmsg = self.tr('No repository selected.')
                qtutils.log(1, errmsg)
                return
            remote, kwargs = self.common_args()
            action = self.action

            # Check if we're about to create a new branch and warn.
            if action == 'push' and not self.model.remote_branch:
                branch = self.model.local_branch
                candidate = '%s/%s' % (remote, branch)
                if candidate not in self.model.remote_branches:
                    title = 'Push'
                    msg = 'Branch "%s" does not exist in %s.' % (branch, remote)
                    msg += '\nA new remote branch will be published.'
                    info_txt= 'Create a new remote branch?'
                    ok_text = 'Create Remote Branch'
                    if not qtutils.confirm(title, msg, info_txt, ok_text,
                                           default=False,
                                           icon=qtutils.git_icon()):
                        return

            if not self.model.ffwd_only_checkbox:
                title = 'Force %s?' % action.title()
                ok_text = 'Force %s' % action.title()

                if action == 'fetch':
                    msg = 'Non-fast-forward fetch overwrites local history!'
                    info_txt = 'Force fetching from %s?' % remote
                elif action == 'push':
                    msg = ('Non-fast-forward push overwrites published '
                           'history!\n(Did you pull first?)')
                    info_txt = 'Force push to %s?' % remote
                else: # pull: shouldn't happen since the controls are hidden
                    msg = "You probably don't want to do this.\n\tContinue?"
                    return

                if not qtutils.confirm(title, msg, info_txt, ok_text,
                                       default=False,
                                       icon=qtutils.discard_icon()):
                    return

            # Disable the GUI by default
            self.view.setEnabled(False)
            self.progress.setEnabled(True)
            QtGui.QApplication.setOverrideCursor(Qt.WaitCursor)

            # Show a nice progress bar
            self.progress.setLabelText('Updating...')
            self.progress.show()

            # Use a thread to update in the background
            task = ActionTask(self.view, modelaction, remote, kwargs)
            self._tasks.append(task)
            QtCore.QThreadPool.globalInstance().start(task)

        return remote_callback


    def _action_completed(self, task, status, output):
        # Grab the results of the action and finish up
        if task in self._tasks:
            self._tasks.remove(task)

        if not output: # git fetch --tags --verbose doesn't print anything...
            output = self.tr('Already up-to-date.')
        # Force the status to 1 so that we always display the log
        qtutils.log(1, output)

        self.progress.close()
        QtGui.QApplication.restoreOverrideCursor()

        if status != 0 and self.action == 'push':
            message = 'Error pushing to "%s".\n\nPull first?' % self.model.remotename
            qtutils.critical('Push Error',
                             message=message, details=output)
        else:
            title = self.view.windowTitle()
            if status == 0:
                result = 'succeeded'
            else:
                result = 'returned exit status %d' % status

            message = '"git %s" %s' % (self.action, result)
            qtutils.information(title,
                                message=message, details=output)
        self.view.accept()


class ActionTask(QtCore.QRunnable):
    def __init__(self, sender, modelaction, remote, kwargs):
        QtCore.QRunnable.__init__(self)
        self._sender = sender
        self._modelaction = modelaction
        self._remote = remote
        self._kwargs = kwargs

    def run(self):
        """Runs the model action and captures the result"""
        status, output = self._modelaction(self._remote, **self._kwargs)
        self._sender.emit(SIGNAL('action_completed'), self, status, output)
