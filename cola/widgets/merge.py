from __future__ import division, absolute_import, unicode_literals

from qtpy import QtWidgets
from qtpy.QtCore import Qt

from cola import cmds
from cola import gitcfg
from cola import gitcmds
from cola import icons
from cola import qtutils
from cola.i18n import N_
from cola.models import main
from cola.widgets import completion
from cola.widgets import defs


def local_merge():
    """Provides a dialog for merging branches"""
    model = main.model()
    cfg = gitcfg.current()
    view = MergeView(cfg, model, qtutils.active_window())
    view.show()
    view.raise_()
    return view


def abort_merge():
    """Prompts before aborting a merge in progress
    """
    title = N_('Abort Merge...')
    txt = N_('Aborting the current merge will cause '
             '*ALL* uncommitted changes to be lost.\n'
             'Recovering uncommitted changes is not possible.')
    info_txt = N_('Aborting the current merge?')
    ok_txt = N_('Abort Merge')
    if qtutils.confirm(title, txt, info_txt, ok_txt,
                       default=False, icon=icons.undo()):
        gitcmds.abort_merge()


class MergeView(QtWidgets.QDialog):
    """Provides a dialog for merging branches."""

    def __init__(self, cfg, model, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        self.cfg = cfg
        self.model = model
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)
        self.setAttribute(Qt.WA_MacMetalStyle)

        # Widgets
        self.title_label = QtWidgets.QLabel()
        self.revision_label = QtWidgets.QLabel()
        self.revision_label.setText(N_('Revision to Merge'))

        self.revision = completion.GitRefLineEdit()
        self.revision.setFocus()
        self.revision.setToolTip(N_('Revision to Merge'))

        self.radio_local = qtutils.radio(text=N_('Local Branch'), checked=True)
        self.radio_remote = qtutils.radio(text=N_('Tracking Branch'))

        self.radio_tag = qtutils.radio(text=N_('Tag'))

        self.revisions = QtWidgets.QListWidget()
        self.revisions.setAlternatingRowColors(True)

        self.button_viz = qtutils.create_button(text=N_('Visualize'),
                                                icon=icons.visualize())

        tooltip = N_('Squash the merged commit(s) into a single commit')
        self.checkbox_squash = qtutils.checkbox(text=N_('Squash'),
                                                tooltip=tooltip)

        tooltip = N_('Always create a merge commit when enabled, '
                     'even when the merge is a fast-forward update')
        self.checkbox_noff = qtutils.checkbox(text=N_('No fast forward'),
                                              tooltip=tooltip, checked=False)
        self.checkbox_noff_state = False

        tooltip = N_('Commit the merge if there are no conflicts.  '
                     'Uncheck to leave the merge uncommitted')
        self.checkbox_commit = qtutils.checkbox(text=N_('Commit'),
                                                tooltip=tooltip, checked=True)
        self.checkbox_commit_state = True

        text = N_('Create Signed Commit')
        checked = cfg.get('cola.signcommits', False)
        tooltip = N_('GPG-sign the merge commit')
        self.checkbox_sign = qtutils.checkbox(text=text, checked=checked,
                                              tooltip=tooltip)
        self.button_close = qtutils.close_button()

        icon = icons.merge()
        self.button_merge = qtutils.create_button(text=N_('Merge'), icon=icon)

        # Layouts
        self.revlayt = qtutils.hbox(defs.no_margin, defs.spacing,
                                    self.revision_label, self.revision,
                                    qtutils.STRETCH, self.title_label)

        self.radiolayt = qtutils.hbox(defs.no_margin, defs.spacing,
                                      self.radio_local, self.radio_remote,
                                      self.radio_tag)

        self.buttonlayt = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                       self.button_viz, qtutils.STRETCH,
                                       self.checkbox_squash, self.checkbox_noff,
                                       self.checkbox_commit, self.checkbox_sign,
                                       self.button_close, self.button_merge)

        self.mainlayt = qtutils.vbox(defs.margin, defs.spacing,
                                     self.radiolayt, self.revisions,
                                     self.revlayt, self.buttonlayt)
        self.setLayout(self.mainlayt)

        # Signal/slot connections
        self.revision.textChanged.connect(self.update_title)
        self.revisions.itemSelectionChanged.connect(self.revision_selected)

        qtutils.connect_button(self.button_close, self.reject)
        qtutils.connect_button(self.checkbox_squash, self.toggle_squash)
        qtutils.connect_button(self.radio_local, self.update_revisions)
        qtutils.connect_button(self.radio_remote, self.update_revisions)
        qtutils.connect_button(self.radio_tag, self.update_revisions)
        qtutils.connect_button(self.button_merge, self.merge_revision)
        qtutils.connect_button(self.button_viz, self.viz_revision)

        # Observer messages
        model.add_observer(model.message_updated, self.update_all)
        self.update_all()
        self.resize(700, 400)

    def update_all(self):
        """Set the branch name for the window title and label."""
        self.update_title()
        self.update_revisions()

    def update_title(self, dummy_txt=None):
        branch = self.model.currentbranch
        revision = self.revision.text()
        if revision:
            txt = (N_('Merge "%(revision)s" into "%(branch)s"') %
                   dict(revision=revision, branch=branch))
        else:
            txt = N_('Merge into "%s"') % branch
        self.title_label.setText(txt)
        self.setWindowTitle(txt)

    def toggle_squash(self):
        """Toggles the commit checkbox based on the squash checkbox."""
        if self.checkbox_squash.isChecked():
            self.checkbox_commit_state = self.checkbox_commit.checkState()
            self.checkbox_commit.setCheckState(Qt.Unchecked)
            self.checkbox_commit.setDisabled(True)
            self.checkbox_noff_state = self.checkbox_noff.checkState()
            self.checkbox_noff.setCheckState(Qt.Unchecked)
            self.checkbox_noff.setDisabled(True)
        else:
            self.checkbox_noff.setDisabled(False)
            oldstateff = self.checkbox_noff_state
            self.checkbox_noff.setCheckState(oldstateff)
            self.checkbox_commit.setDisabled(False)
            oldstate = self.checkbox_commit_state
            self.checkbox_commit.setCheckState(oldstate)

    def update_revisions(self):
        """Update the revision list whenever a radio button is clicked"""
        self.revisions.clear()
        self.revisions.addItems(self.current_revisions())

    def revision_selected(self):
        """Update the revision field when a list item is selected"""
        revlist = self.current_revisions()
        widget = self.revisions
        revision = qtutils.selected_item(widget, revlist)
        if revision is not None:
            self.revision.setText(revision)

    def current_revisions(self):
        """Retrieve candidate items to merge"""
        if self.radio_local.isChecked():
            return self.model.local_branches
        elif self.radio_remote.isChecked():
            return self.model.remote_branches
        elif self.radio_tag.isChecked():
            return self.model.tags
        return []

    def viz_revision(self):
        """Launch a gitk-like viewer on the selection revision"""
        revision = self.revision.text()
        if not revision:
            qtutils.information(N_('No Revision Specified'),
                                N_('You must specify a revision to view.'))
            return
        cmds.do(cmds.VisualizeRevision, revision)

    def merge_revision(self):
        """Merge the selected revision/branch"""
        revision = self.revision.text()
        if not revision:
            qtutils.information(N_('No Revision Specified'),
                                N_('You must specify a revision to merge.'))
            return

        noff = self.checkbox_noff.isChecked()
        no_commit = not self.checkbox_commit.isChecked()
        squash = self.checkbox_squash.isChecked()
        sign = self.checkbox_sign.isChecked()
        cmds.do(cmds.Merge, revision, no_commit, squash, noff, sign)
        self.accept()
