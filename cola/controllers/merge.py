"""This controller handles the merge dialog."""


from PyQt4.Qt import Qt

from cola import utils
from cola import qtutils
from cola.qobserver import QObserver
from cola.views import MergeView

def abort_merge(model, parent):
    """Prompts before aborting a merge in progress
    """
    txt = parent.tr('Abort merge?\n'
                    'Aborting the current merge will cause '
                    '*ALL* uncommitted changes to be lost.\n\n'
                    'Continue with aborting the current merge?')
    answer = qtutils.question(parent, parent.tr('Abort Merge?'), txt)
    if answer:
        model.abort_merge()

def local_merge(model, parent):
    """Provides a dialog for merging branches"""
    model = model.clone()
    view = MergeView(parent)
    ctl = MergeController(model, view)
    view.show()

class MergeController(QObserver):
    """Provide control to the merge dialog"""
    def __init__(self, model, view):
        QObserver.__init__(self, model, view)
        # Set the current branch label
        branch = self.model.currentbranch
        title = unicode(self.tr('Merge Into %s')) %  branch
        self.view.label.setText(title)
        self.add_observables('revision', 'revisions')
        self.add_callbacks(radio_local = self.radio_callback,
                           radio_remote = self.radio_callback,
                           radio_tag = self.radio_callback,
                           revisions = self.revision_selected,
                           button_viz = self.viz_revision,
                           button_merge = self.merge_revision,
                           checkbox_squash = self.squash_update)
        self.model.set_revisions(self.model.local_branches)
        self.view.radio_local.setChecked(True)

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
        msg = self.model.merge_message()
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

    def squash_update(self):
        """Enables/disables widgets when the 'squash' radio is clicked"""
        # TODO move this code into the view
        if self.view.checkbox_squash.isChecked():
            self.old_commit_checkbox_state =\
                self.view.checkbox_commit.checkState()
            self.view.checkbox_commit.setCheckState(Qt.Unchecked)
            self.view.checkbox_commit.setDisabled(True)
        else:
            self.view.checkbox_commit.setDisabled(False)
            try:
                oldstate = self.old_commit_checkbox_state
                self.view.checkbox_commit.setCheckState(oldstate)
            except AttributeError:
                # no problem
                pass
