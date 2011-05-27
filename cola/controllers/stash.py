"""This controller handles the stash dialog."""


import os

from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

import cola
from cola import utils
from cola import qtutils
from cola import signals
from cola.qobserver import QObserver
from cola.views import stash as stashmod

def stash(parent=None):
    """Launches a stash dialog using the provided model + view
    """
    model = cola.model()
    model.stash_list = []
    model.stash_revids = []
    model.stash_names = []
    if parent is None:
        parent = QtGui.QApplication.instance().activeWindow()
    view = stashmod.StashView(parent)
    ctl = StashController(model, view)
    view.show()


class StashController(QObserver):
    """The StashController is the brains behind the 'Stash' dialog
    """
    def __init__(self, model, view):
        QObserver.__init__(self, model, view)
        self.add_callbacks(button_apply = self.stash_apply,
                           button_remove = self.stash_remove,
                           button_save  = self.stash_save,
                           button_close = self.close)
        self.connect(self.view.stash_list, SIGNAL('itemSelectionChanged()'),
                     self.item_selected)
        self.update_model()
        self.update_actions()

    def update_model(self):
        """Initiates git queries on the model and updates the view
        """
        self.model.set_stash_list(self.model.parse_stash_list())
        self.model.set_stash_revids(self.model.parse_stash_list(revids=True))
        self.model.set_stash_names(self.model.parse_stash_list(names=True))
        self.refresh_view()

    def refresh_view(self):
        self.view.stash_list.clear()
        for item in self.model.stash_list:
            self.view.stash_list.addItem(item)

    def selected_stash(self):
        """Returns the stash name of the currently selected stash
        """
        list_widget = self.view.stash_list
        stash_list = self.model.stash_revids
        return qtutils.selected_item(list_widget, stash_list)

    def selected_name(self):
        list_widget = self.view.stash_list
        stash_list = self.model.stash_names
        return qtutils.selected_item(list_widget, stash_list)

    def stash_save(self):
        """Saves the worktree in a stash

        This prompts the user for a stash name and creates
        a git stash named accordingly.
        """
        stash_name, ok = qtutils.prompt('Save Stash',
                                        'Enter a name for the stash')
        if not ok or not stash_name:
            return

        # Sanitize the stash name
        stash_name = utils.sanitize(stash_name)

        if stash_name in self.model.stash_names:
            qtutils.critical('Oops!',
                             'A stash named "%s" already exists' % stash_name)
            return

        args = []
        if self.view.keep_index.isChecked():
            args.append('--keep-index')
        args.append(stash_name)

        qtutils.log(*self.model.git.stash('save',
                                          with_stderr=True,
                                          with_status=True,
                                          *args))
        self.view.accept()
        cola.notifier().broadcast(signals.rescan)

    def update_actions(self):
        has_changes = bool(self.model.modified + self.model.staged)
        has_stash = self.selected_stash() is not None
        self.view.button_save.setEnabled(has_changes)
        self.view.button_apply.setEnabled(has_stash)
        self.view.button_remove.setEnabled(has_stash)

    def item_selected(self):
        """Shows the current stash in the main view."""
        self.update_actions()
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

    def stash_remove(self):
        """Drops the currently selected stash
        """
        selection = self.selected_stash()
        name = self.selected_name()
        if not selection:
            return
        if not qtutils.confirm(self.view,
                               'Remove Stash?',
                               'Remove "%s"?' % name,
                               'Recovering these changes may not be possible.',
                               'Remove',
                               icon=qtutils.discard_icon()):
            return
        qtutils.log(*self.model.git.stash('drop', selection,
                                          with_stderr=True,
                                          with_status=True))
        self.update_model()

    def close(self):
        self.view.accept()
        cola.notifier().broadcast(signals.rescan)
