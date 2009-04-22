"""This controller handles the remote dialog."""


import os
from PyQt4.QtGui import QDialog

from cola import utils
from cola import qtutils
from cola.views import RemoteView
from cola.views.drawer import Drawer
from cola.qobserver import QObserver

def remote_action(model, parent, action):
    # TODO: subclass model
    model = model.clone()
    model.generate_remote_helpers()
    model.remotename = ''
    model.tags_checkbox = False
    model.rebase_checkbox = False
    model.ffwd_only_checkbox = True

    view = RemoteView(parent, action)
    controller = RemoteController(model, view, action)
    view.show()

class RemoteController(QObserver):
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
        self.action_method = {
            'fetch': self.gen_remote_callback(self.model.fetch_helper),
            'push': self.gen_remote_callback(self.model.push_helper),
            'pull': self.gen_remote_callback(self.model.pull_helper),
        }   [action]

        self.add_actions(remotes = self.display_remotes)
        self.add_callbacks(action_button = self.action_method,
                           remotes = self.update_remotes,
                           local_branches = self.update_local_branches,
                           remote_branches = self.update_remote_branches)
        self.refresh_view()
        remotes = self.model.get_remotes()
        if 'origin' in remotes:
            idx = remotes.index('origin')
            if self.view.select_remote(idx):
                self.model.set_remotename('origin')
        else:
            if self.view.select_first_remote():
                self.model.set_remotename(remotes[0])


    def display_remotes(self, widget):
        displayed = []
        for remotename in self.model.get_remotes():
            url = self.model.remote_url(remotename)
            display = ('%s\t(%s %s)'
                       % (remotename, unicode(self.tr('URL:')), url))
            displayed.append(display)
        qtutils.set_items(widget,displayed)

    def update_remotes(self,*rest):
        widget = self.view.remotes
        remotes = self.model.get_remotes()
        selection = qtutils.get_selected_item(widget, remotes)
        if not selection:
            return
        self.model.set_remotename(selection)
        self.view.remotename.selectAll()

    def update_local_branches(self,*rest):
        branches = self.model.get_local_branches()
        widget = self.view.local_branches
        selection = qtutils.get_selected_item(widget, branches)
        if not selection:
            return

        self.model.set_local_branch(selection)
        self.model.set_remote_branch(selection)

        self.view.local_branch.selectAll()
        self.view.remote_branch.selectAll()

    def update_remote_branches(self,*rest):
        widget = self.view.remote_branches
        branches = self.model.get_remote_branches()
        selection = qtutils.get_selected_item(widget,branches)
        if not selection:
            return
        branch = utils.basename(selection)
        if branch == 'HEAD':
            return
        self.model.set_remote_branch(branch)
        self.view.remote_branch.selectAll()

    def get_common_args(self):
        return (self.model.get_remotename(),
                {
                    'local_branch': self.model.get_local_branch(),
                    'remote_branch': self.model.get_remote_branch(),
                    'ffwd': self.model.get_ffwd_only_checkbox(),
                    'tags': self.model.get_tags_checkbox(),
                    'rebase': self.model.get_rebase_checkbox(),
                })

    #+-------------------------------------------------------------
    #+ Actions
    def gen_remote_callback(self, modelaction):
        """Generates a Qt callback for fetch/push/pull.
        """
        def remote_callback():
            if not self.model.get_remotename():
                errmsg = self.tr('No repository selected.')
                qtutils.log(1, errmsg)
                return
            action = self.action
            if not self.model.get_ffwd_only_checkbox():
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
            remote, kwargs = self.get_common_args()
            status, output = modelaction(remote, **kwargs)
            if not output: # git fetch --tags --verbose doesn't print anything...
                output = self.tr('Already up-to-date.')
            # Force the status to 1 so that we always display the log
            qtutils.log(1, output)
            self.view.accept()
        return remote_callback
