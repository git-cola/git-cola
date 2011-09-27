from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import qtutils
from cola import signals
from cola.qt import GitRefLineEdit
from cola.qtutils import tr

class MergeView(QtGui.QDialog):
    """Provides a dialog for merging branches."""
    def __init__(self, model, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.model = model

        self.setWindowModality(Qt.WindowModal)
        self.resize(700, 400)

        # Widgets
        self.title_label = QtGui.QLabel()

        self.revision_label = QtGui.QLabel()
        self.revision_label.setText(tr('Revision To Merge'))

        self.revision = GitRefLineEdit()

        self.radio_local = QtGui.QRadioButton()
        self.radio_local.setText(tr('Local Branch'))
        self.radio_local.setChecked(True)

        self.radio_remote = QtGui.QRadioButton()
        self.radio_remote.setText(tr('Tracking Branch'))

        self.radio_tag = QtGui.QRadioButton()
        self.radio_tag.setText(tr('Tag'))

        self.revisions = QtGui.QListWidget()
        self.revisions.setAlternatingRowColors(True)

        self.button_viz = QtGui.QPushButton(self)
        self.button_viz.setText(tr('Visualize'))

        self.checkbox_squash = QtGui.QCheckBox(self)
        self.checkbox_squash.setText(tr('Squash'))

        self.checkbox_commit = QtGui.QCheckBox(self)
        self.checkbox_commit.setText(tr('Commit'))
        self.checkbox_commit.setChecked(True)
        self.checkbox_commit_state = True

        self.button_cancel = QtGui.QPushButton(self)
        self.button_cancel.setText(tr('Cancel'))

        self.button_merge = QtGui.QPushButton(self)
        self.button_merge.setText(tr('Merge'))

        # Layouts
        self.revlayt = QtGui.QHBoxLayout()
        self.revlayt.addWidget(self.revision_label)
        self.revlayt.addWidget(self.revision)
        self.revlayt.addStretch()
        self.revlayt.addWidget(self.title_label)

        self.radiolayt = QtGui.QHBoxLayout()
        self.radiolayt.addWidget(self.radio_local)
        self.radiolayt.addWidget(self.radio_remote)
        self.radiolayt.addWidget(self.radio_tag)

        self.buttonlayt = QtGui.QHBoxLayout()
        self.buttonlayt.addWidget(self.button_viz)
        self.buttonlayt.addStretch()
        self.buttonlayt.addWidget(self.checkbox_squash)
        self.buttonlayt.addWidget(self.checkbox_commit)
        self.buttonlayt.addWidget(self.button_cancel)
        self.buttonlayt.addWidget(self.button_merge)

        self.mainlayt = QtGui.QVBoxLayout()
        self.mainlayt.setMargin(4)
        self.mainlayt.addLayout(self.radiolayt)
        self.mainlayt.addWidget(self.revisions)
        self.mainlayt.addLayout(self.revlayt)
        self.mainlayt.addLayout(self.buttonlayt)
        self.setLayout(self.mainlayt)

        self.revision.setFocus()

        # Signal/slot connections
        self.connect(self.button_cancel, SIGNAL('clicked()'),
                     self.reject)

        self.connect(self.checkbox_squash, SIGNAL('clicked()'),
                     self.toggle_squash)

        self.connect(self.revision, SIGNAL('textChanged(QString)'),
                     self.update_title)

        self.connect(self.revisions, SIGNAL('itemSelectionChanged()'),
                     self.revision_selected)

        self.connect(self.radio_local, SIGNAL('clicked()'),
                     self.update_revisions)

        self.connect(self.radio_remote, SIGNAL('clicked()'),
                     self.update_revisions)

        self.connect(self.radio_tag, SIGNAL('clicked()'),
                     self.update_revisions)

        self.connect(self.button_merge, SIGNAL('clicked()'),
                     self.merge_revision)

        self.connect(self.button_viz, SIGNAL('clicked()'),
                     self.viz_revision)

        # Observer messages
        msg = model.message_updated
        model.add_message_observer(msg, self.update_from_model)
        self.update_from_model()

    def update_from_model(self):
        """Set the branch name for the window title and label."""
        self.update_title()
        self.update_revisions()

    def update_title(self, dummy_txt=None):
        branch = self.model.current_branch()
        revision = unicode(self.revision.text())
        if revision:
            txt = unicode(tr('Merge "%s" into "%s"')) % (revision, branch)
        else:
            txt = unicode(tr('Merge into "%s"')) % branch
        self.title_label.setText(txt)
        self.setWindowTitle(txt)

    def toggle_squash(self):
        """Toggles the commit checkbox based on the squash checkbox."""
        if self.checkbox_squash.isChecked():
            self.checkbox_commit_state =\
                self.checkbox_commit.checkState()
            self.checkbox_commit.setCheckState(Qt.Unchecked)
            self.checkbox_commit.setDisabled(True)
        else:
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
        row, selected = qtutils.selected_row(widget)
        if selected and row < len(revlist):
            revision = revlist[row]
            self.revision.setText(revision)

    def current_revisions(self):
        """Retrieve candidate items to merge"""
        if self.radio_local.isChecked():
            return self.model.local_branches()
        elif self.radio_remote.isChecked():
            return self.model.remote_branches()
        elif self.radio_tag.isChecked():
            return self.model.tags()
        return []

    def viz_revision(self):
        """Launch a gitk-like viewer on the selection revision"""
        revision = unicode(self.revision.text())
        if not revision:
            qtutils.information('No Revision Specified',
                                'You must specify a revision to view')
            return
        self.emit(SIGNAL(signals.visualize_revision), revision)

    def merge_revision(self):
        """Merge the selected revision/branch"""
        revision = unicode(self.revision.text())
        if not revision:
            qtutils.information('No Revision Specified',
                                'You must specify a revision to merge')
            return

        do_commit = self.checkbox_commit.isChecked()
        squash = self.checkbox_squash.isChecked()
        self.emit(SIGNAL(self.model.message_merge),
                  revision, not(do_commit), squash)
        self.accept()
