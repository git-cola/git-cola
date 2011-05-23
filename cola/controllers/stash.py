"""This controller handles the stash dialog."""


import os

from PyQt4 import QtGui

import cola
from cola import utils
from cola import qtutils
from cola import signals
from cola.qobserver import QObserver
from cola.views import stash as stashmod

def stash():
    """Launches a stash dialog using the provided model + view
    """
    model = cola.model()
    model.keep_index = True
    model.stash_list = []
    model.stash_revids = []
    parent = QtGui.QApplication.instance().activeWindow()
    view = stashmod.StashView(parent)
    ctl = StashController(model, view)
    view.show()


class StashController(QObserver):
    """The StashController is the brains behind the 'Stash' dialog
    """
    def __init__(self, model, view):
        QObserver.__init__(self, model, view)
        self.add_observables('stash_list', 'keep_index')
        self.add_callbacks(button_stash_show  = self.stash_show,
                           button_stash_apply = self.stash_apply,
                           button_stash_drop  = self.stash_drop,
                           button_stash_clear = self.stash_clear,
                           button_stash_save  = self.stash_save)
        self.update_model()

    def update_model(self):
        """Initiates git queries on the model and updates the view
        """
        self.model.set_stash_list(self.model.parse_stash_list())
        self.model.set_stash_revids(self.model.parse_stash_list(revids=True))
        self.refresh_view()

    def selected_stash(self):
        """Returns the stash name of the currently selected stash
        """
        list_widget = self.view.stash_list
        stash_list = self.model.stash_revids
        return qtutils.selected_item(list_widget, stash_list)

    def stash_save(self):
        """Saves the worktree in a stash

        This prompts the user for a stash name and creates
        a git stash named accordingly.
        """
        if not qtutils.question(self.view,
                                'Stash Changes?',
                                'This will stash your current '
                                'changes away for later use.\n'
                                'Continue?'):
            return

        stash_name, ok = qtutils.prompt('Enter a name for this stash')
        if not ok:
            return
        while stash_name in self.model.stash_list:
            qtutils.information('Oops!',
                                'That name already exists.  '
                                'Please enter another name.')
            stash_name, ok = qtutils.prompt('Enter a name for this stash')
            if not ok:
                return

        if not stash_name:
            return

        # Sanitize the stash name
        stash_name = utils.sanitize(stash_name)
        args = []
        if self.model.keep_index:
            args.append('--keep-index')
        args.append(stash_name)

        qtutils.log(*self.model.git.stash('save',
                                          with_stderr=True,
                                          with_status=True,
                                          *args))
        self.view.accept()
        cola.notifier().broadcast(signals.rescan)

    def stash_show(self):
        """Shows the current stash in the main view."""
        selection = self.selected_stash()
        if not selection:
            return
        diffstat = self.model.git.stash('show', selection)
        diff = self.model.git.stash('show', '-p', selection)
        cola.notifier().broadcast(signals.diff_text, '%s\n\n%s' % (diffstat, diff))

    def stash_apply(self):
        """Applies the currently selected stash
        """
        selection = self.selected_stash()
        if not selection:
            return
        qtutils.log(*self.model.git.stash('apply', '--index', selection,
                                          with_stderr=True,
                                          with_status=True))
        self.view.accept()
        cola.notifier().broadcast(signals.rescan)

    def stash_drop(self):
        """Drops the currently selected stash
        """
        selection = self.selected_stash()
        if not selection:
            return
        if not qtutils.question(self.view,
                                'Drop Stash?',
                                'This will permanently remove the '
                                'selected stash.\n'
                                'Recovering these changes may not '
                                'be possible.\n\n'
                                'Continue?'):
            return
        qtutils.log(*self.model.git.stash('drop', selection,
                                          with_stderr=True,
                                          with_status=True))
        self.update_model()

    def stash_clear(self):
        """Clears all stashes
        """
        if not qtutils.question(self.view,
                                'Drop All Stashes?',
                                'This will permanently remove '
                                'ALL stashed changes.\n'
                                'Recovering these changes may not '
                                'be possible.\n\n'
                                'Continue?'):
            return
        self.model.git.stash('clear'),
        self.update_model()
