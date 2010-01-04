"""This controller handles the merge dialog."""


from PyQt4 import QtGui
from PyQt4.Qt import Qt

import cola
from cola import gitcmds
from cola import utils
from cola import qtutils
from cola import serializer
from cola.qobserver import QObserver
from cola.views.merge import MergeView

def abort_merge():
    """Prompts before aborting a merge in progress
    """
    txt = ('Abort merge?\n'
           'Aborting the current merge will cause '
           '*ALL* uncommitted changes to be lost.\n\n'
           'Continue with aborting the current merge?')
    parent = QtGui.QApplication.instance().activeWindow()
    answer = qtutils.question(parent, 'Abort Merge?', txt, default=False)
    if answer:
        gitcmds.abort_merge()

def local_merge():
    """Provides a dialog for merging branches"""
    model = serializer.clone(cola.model())
    parent = QtGui.QApplication.instance().activeWindow()
    view = MergeView(parent)
    ctl = MergeController(model, view)
    view.show()

class MergeController(QObserver):
    """Provide control to the merge dialog"""
    def __init__(self, model, view):
        QObserver.__init__(self, model, view)
        # Set the current branch label
        self.view.set_branch(self.model.currentbranch)
        self.add_observables('revision', 'revisions')
        self.add_callbacks(radio_local = self.radio_callback,
                           radio_remote = self.radio_callback,
                           radio_tag = self.radio_callback,
                           revisions = self.revision_selected,
                           button_viz = self.viz_revision,
                           button_merge = self.merge_revision)
        self.model.set_revisions(self.model.local_branches)

    def revisions(self):
        """Retrieve candidate items to merge"""
        if self.view.radio_local.isChecked():
            return self.model.local_branches
        elif self.view.radio_remote.isChecked():
            return self.model.remote_branches
        elif self.view.radio_tag.isChecked():
            return self.model.tags
        return []

    def revision_selected(self, *args):
        """Update the revision field when a list item is selected"""
        revlist = self.revisions()
        widget = self.view.revisions
        row, selected = qtutils.selected_row(widget)
        if selected and row < len(revlist):
            revision = revlist[row]
            self.model.set_revision(revision)

    def radio_callback(self):
        """Update the revision list whenever a radio button is clicked"""
        self.model.set_revisions(self.revisions())

    def merge_revision(self):
        """Merge the selected revision/branch"""
        revision = self.model.revision
        if not revision:
            qtutils.information('No Revision Specified',
                                'You must specify a revision to merge')
            return

        no_commit = not(self.view.checkbox_commit.isChecked())
        squash = self.view.checkbox_squash.isChecked()
        msg = gitcmds.merge_message()
        qtutils.log(*self.model.git.merge('-m'+msg,
                                         revision,
                                         strategy='recursive',
                                         no_commit=no_commit,
                                         squash=squash,
                                         with_stderr=True,
                                         with_status=True))
        self.view.accept()

    def viz_revision(self):
        """Launch a gitk-like viewer on the selection revision"""
        revision = self.model.revision
        browser = self.model.history_browser()
        utils.fork([browser, revision])
