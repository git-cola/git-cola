"""This controller handles the remote dialog."""


import os
import fnmatch
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QDialog

import cola
from cola import serializer
from cola import gitcmds
from cola import utils
from cola import qtutils
from cola.views import remote
from cola.qobserver import QObserver

def remote_action(parent, action):
    """Launches fetch/push/pull dialogs."""
    # TODO: subclass model
    model = serializer.clone(cola.model())
    model.remotename = ''
    model.tags_checkbox = False
    model.rebase_checkbox = False
    model.ffwd_only_checkbox = True

    view = remote.RemoteView(parent, action)
    controller = RemoteController(model, view, action)
    view.show()
    return view.exec_()


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
        self.action_result = None
        """Callbacks corresponding to the 3 (fetch/push/pull) modes"""

        self.add_actions(remotes = self.display_remotes)
        self.add_callbacks(action_button = self.action_method,
                           remotes = self.update_remotes,
                           local_branches = self.update_local_branches,
                           remote_branches = self.update_remote_branches)
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
        if action == 'fetch':
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

        if action == 'pull':
            branch = self.model.currentbranch
            remotebranch = gitcmds.tracked_branch(branch)
            if remotebranch is None:
                return
            try:
                idx = self.model.remote_branches.index(remotebranch)
            except ValueError:
                return
            self.model.set_remote_branch(branch)

    def display_remotes(self, widget):
        """Display the available remotes in a listwidget"""
        displayed = []
        for remotename in self.model.remotes:
            url = self.model.remote_url(remotename)
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
                    msg = ('Branch "' + branch + '" does not exist in ' +
                           remote + '.\n\nCreate a new branch?')
                    if not qtutils.question(self.view, 'Create New Branch?',
                                            msg, default=False):
                        return

            if not self.model.ffwd_only_checkbox:
                if action == 'fetch':
                    msg = ('Non-fast-forward fetch overwrites local '
                           'history!\n\tContinue?')
                elif action == 'push':
                    msg = ('Non-fast-forward push overwrites published '
                           'history!\nAre you sure you want to do this?  '
                           '(Did you pull first?)\n\tContinue?')
                else: # pull: shouldn't happen since the controls are hidden
                    msg = "You probably don't want to do this.\n\tContinue?"
                if not qtutils.question(self.view,
                        'Force %s?' % action.title(), msg, default=False):
                    return

            # Disable the GUI by default
            self.view.setEnabled(False)
            QtGui.QApplication.setOverrideCursor(Qt.WaitCursor)

            # Show a nice progress bar
            progress = QtGui.QProgressDialog(self.view)
            progress.setRange(0, 0)
            progress.setCancelButton(None)
            progress.setLabelText('Connecting to %s...' % remote)
            progress.setWindowModality(Qt.WindowModal)
            progress.setAutoClose(True)
            progress.setAutoReset(True)

            # Use a timer to run the action
            timer = QtCore.QTimer(self.view)
            timer.setSingleShot(True)

            def runaction():
                """Runs the model action and captures the result"""
                self.action_result = modelaction(remote, **kwargs)
                progress.close()

            # Connect the timer to runaction()
            self.view.connect(timer, SIGNAL('timeout()'), runaction)

            # Show the progress bar, start the timer, and block
            # waiting for runaction() to close the progress bar
            progress.show()
            timer.start(0)
            progress.exec_()

            # Grab the results of the action and finish up
            status, output = self.action_result

            if not output: # git fetch --tags --verbose doesn't print anything...
                output = self.tr('Already up-to-date.')
            # Force the status to 1 so that we always display the log
            qtutils.log(1, output)

            progress.close()
            QtGui.QApplication.restoreOverrideCursor()

            if status != 0 and action == 'push':
                message = 'Error pushing to "%s".\n\nPull first?' % remote
                qtutils.critical('Push Error',
                                 message=message, details=output)
            self.view.accept()

        return remote_callback
