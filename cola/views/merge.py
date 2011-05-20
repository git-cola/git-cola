from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola.qtutils import tr

class MergeView(QtGui.QDialog):
    """Provides a dialog for merging branches."""
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowModality(Qt.WindowModal)
        self.setWindowTitle(tr('Merge'))
        self.resize(673, 339)
        self.vboxlayout = QtGui.QVBoxLayout(self)
        self.vboxlayout.setMargin(3)

        self.merge_target_label = QtGui.QLabel(self)
        self.merge_target_label.setAlignment(Qt.AlignCenter)
        self.vboxlayout.addWidget(self.merge_target_label)

        self.groupbox = QtGui.QGroupBox(self)
        self.groupbox.setTitle(tr('Revision To Merge'))

        self.gridlayout = QtGui.QGridLayout(self.groupbox)
        self.gridlayout.setContentsMargins(5, 5, 5, 5)

        self.revision_label = QtGui.QLabel(self.groupbox)
        self.revision_label.setText(tr('Revision Expression:'))
        self.gridlayout.addWidget(self.revision_label, 0, 0, 1, 1)

        self.revision = QtGui.QLineEdit(self.groupbox)
        self.gridlayout.addWidget(self.revision, 0, 1, 1, 2)

        self.radio_local = QtGui.QRadioButton(self.groupbox)
        self.radio_local.setText(tr('Local Branch'))
        self.radio_local.setChecked(True)
        self.gridlayout.addWidget(self.radio_local, 1, 0, 1, 1)

        self.radio_remote = QtGui.QRadioButton(self.groupbox)
        self.radio_remote.setText(tr('Tracking Branch'))
        self.gridlayout.addWidget(self.radio_remote, 1, 1, 1, 1)

        self.radio_tag = QtGui.QRadioButton(self.groupbox)
        self.radio_tag.setText(tr('Tag'))
        self.gridlayout.addWidget(self.radio_tag, 1, 2, 1, 1)

        self.revisions = QtGui.QListWidget(self.groupbox)
        self.revisions.setAlternatingRowColors(True)
        self.gridlayout.addWidget(self.revisions, 2, 0, 1, 3)

        self.vboxlayout.addWidget(self.groupbox)

        self.hboxlayout = QtGui.QHBoxLayout()

        self.button_viz = QtGui.QPushButton(self)
        self.button_viz.setText(tr('Visualize'))
        self.hboxlayout.addWidget(self.button_viz)

        self.spacer = QtGui.QSpacerItem(231, 24, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.hboxlayout.addItem(self.spacer)

        self.checkbox_squash = QtGui.QCheckBox(self)
        self.checkbox_squash.setText(tr('Squash'))
        self.hboxlayout.addWidget(self.checkbox_squash)

        self.checkbox_commit = QtGui.QCheckBox(self)
        self.checkbox_commit.setText(tr('Commit'))
        self.checkbox_commit.setChecked(True)
        self.checkbox_commit_state = True
        self.hboxlayout.addWidget(self.checkbox_commit)

        self.button_cancel = QtGui.QPushButton(self)
        self.button_cancel.setText(tr('Cancel'))
        self.hboxlayout.addWidget(self.button_cancel)

        self.button_merge = QtGui.QPushButton(self)
        self.button_merge.setText(tr('Merge'))
        self.hboxlayout.addWidget(self.button_merge)

        self.vboxlayout.addLayout(self.hboxlayout)

        self.connect(self.button_cancel, SIGNAL('clicked()'),
                     self.reject)

        self.connect(self.checkbox_squash, SIGNAL('clicked()'),
                     self.toggle_squash)

        self.set_branch('master')
        self.revision.setFocus()

    def set_branch(self, branch):
        """Set the branch name for the window title and label."""
        txt = unicode(tr('Merge into %s')) % branch
        self.merge_target_label.setText(txt)

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


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    merge = MergeView()
    merge.raise_()
    merge.show()
    sys.exit(app.exec_())
