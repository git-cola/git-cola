#!/usr/bin/env python
from cola import utils
from cola import qtutils
from cola.qobserver import QObserver
from cola.views import MergeView
from PyQt4.Qt import *

def abort_merge(model, parent):
    txt = parent.tr('Abort merge?\n'
                    'Aborting the current merge will cause '
                    '*ALL* uncommitted changes to be lost.\n\n'
                    'Continue with aborting the current merge?')
    answer = qtutils.question(parent, parent.tr('Abort Merge?'), txt)
    if answer:
        model.abort_merge()

def local_merge(model, parent):
    model = model.clone()
    model.create(revision='', revision_list=[])
    view = MergeView(parent)
    ctl = MergeController(model, view)
    view.show()

class MergeController(QObserver):
    def init(self, model, view):
        # Set the current branch label
        branch = self.model.get_currentbranch()
        title = unicode(self.tr('Merge Into %s')) %  branch
        self.view.label.setText(title)
        self.add_observables('revision', 'revision_list')
        self.add_callbacks(radio_local = self.radio_callback,
                           radio_remote = self.radio_callback,
                           radio_tag = self.radio_callback,
                           revision_list = self.revision_selected,
                           button_viz = self.viz_revision,
                           button_merge = self.merge_revision,
                           checkbox_squash = self.squash_update)
        self.model.set_revision_list(self.model.get_local_branches())
        self.view.radio_local.setChecked(True)
    
    def get_revision_list(self):
        if self.view.radio_local.isChecked():
            return self.model.get_local_branches()
        elif self.view.radio_remote.isChecked():
            return self.model.get_remote_branches()
        elif self.view.radio_tag.isChecked():
            return self.model.get_tags()
        return []

    def revision_selected(self, *args):
        revlist = self.get_revision_list()
        widget = self.view.revision_list
        row, selected = qtutils.get_selected_row(widget)
        if selected and row < len(revlist):
            revision = revlist[row]
            self.model.set_revision(revision)

    def radio_callback(self):
        revlist = self.get_revision_list()
        self.model.set_revision_list(revlist)

    def merge_revision(self):
        revision = self.model.get_revision()
        if not revision:
            qtutils.information('No Revision Specified',
                                'You must specify a revision to merge')
            return

        no_commit = not(self.view.checkbox_commit.isChecked())
        squash = self.view.checkbox_squash.isChecked()
        msg = self.model.get_merge_message()
        qtutils.log(self.model.git.merge('-m'+msg,
                                         revision,
                                         strategy='recursive',
                                         no_commit=no_commit,
                                         squash=squash),
                    quiet=False,
                    doraise=True)
        self.view.accept()

    def viz_revision(self):
        revision = self.model.get_revision()
        browser = self.model.get_history_browser()
        utils.fork(browser, revision)

    def squash_update(self):
        if self.view.checkbox_squash.isChecked():
            self.old_commit_checkbox_state = self.view.checkbox_commit.checkState()
            self.view.checkbox_commit.setCheckState(Qt.Unchecked)
            self.view.checkbox_commit.setDisabled(True)
        else:
            self.view.checkbox_commit.setDisabled(False)
            try:
                self.view.checkbox_commit.setCheckState(self.old_commit_checkbox_state)
            except AttributeError:
                # no problem
                NOP

