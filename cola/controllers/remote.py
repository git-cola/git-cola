"""This controller handles the remote dialog."""


import os
from PyQt4.QtGui import QDialog

import cola
from cola import utils
from cola import qtutils
from cola.views import RemoteView
from cola.qobserver import QObserver

def remote_action(parent, action):
    """Launches fetch/push/pull dialogs."""
    # TODO: subclass model
    model = cola.model()
    model.remotename = ''
    model.tags_checkbox = False
    model.rebase_checkbox = False
    model.ffwd_only_checkbox = True

    view = RemoteView(parent, action)
    controller = RemoteController(model, view, action)
    view.show()

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

        # Select the current branch by default for push
        if action != 'push':
            return
        branches = self.model.local_branches
        branch = self.model.currentbranch
        if branch not in branches:
            return
        idx = branches.index(branch)
        if self.view.select_local_branch(idx):
            self.model.set_local_branch(branch)

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
            action = self.action
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
            remote, kwargs = self.common_args()
            status, output = modelaction(remote, **kwargs)
            if not output: # git fetch --tags --verbose doesn't print anything...
                output = self.tr('Already up-to-date.')
            # Force the status to 1 so that we always display the log
            qtutils.log(1, output)
            self.view.accept()
        return remote_callback
