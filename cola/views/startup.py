"""
Provides the git-cola startup dialog

The startup dialog is presented when no repositories can be
found at startup.

"""
import os

from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import qtutils
from cola import guicmds
from cola import settings

class StartupDialog(QtGui.QDialog):
    """Provides a GUI to Open or Clone a git repository."""

    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle(self.tr('git-cola'))
        self._gitdir = None

        self._layt = QtGui.QHBoxLayout()
        self._open_btn = QtGui.QPushButton('Open...')
        self._clone_btn = QtGui.QPushButton('Clone...')
        self._close_btn = QtGui.QPushButton('Close')

        self._layt.addWidget(self._open_btn)
        self._layt.addWidget(self._clone_btn)
        self._layt.addWidget(self._close_btn)

        self.model = settings.SettingsManager.settings()

        self._vlayt = QtGui.QVBoxLayout()

        self._bookmark_label = QtGui.QLabel(self.tr('Select Repository...'))
        self._bookmark_label.setAlignment(Qt.AlignCenter)

        self._bookmark_model = QtGui.QStandardItemModel()

        item = QtGui.QStandardItem('Select manually...')
        item.setEditable(False)
        self._bookmark_model.appendRow(item)

        for bookmark in self.model.bookmarks:
            item = QtGui.QStandardItem(bookmark)
            item.setEditable(False)
            self._bookmark_model.appendRow(item)

        selection_mode = QtGui.QAbstractItemView.SingleSelection

        self._bookmark_list = QtGui.QListView()
        self._bookmark_list.setSelectionMode(selection_mode)
        self._bookmark_list.setModel(self._bookmark_model)

        if not self.model.bookmarks:
            self._bookmark_label.setMinimumHeight(1)
            self._bookmark_list.setMinimumHeight(1)
            self._bookmark_label.hide()
            self._bookmark_list.hide()

        self._vlayt.addWidget(self._bookmark_label)
        self._vlayt.addWidget(self._bookmark_list)
        self._vlayt.addLayout(self._layt)

        self.setLayout(self._vlayt)

        self.connect(self._open_btn, SIGNAL('clicked()'), self._open)
        self.connect(self._clone_btn, SIGNAL('clicked()'), self._clone)
        self.connect(self._close_btn, SIGNAL('clicked()'), self.reject)
        self.connect(self._bookmark_list,
                     SIGNAL('activated(const QModelIndex &)'),
                     self._open_bookmark)


    def find_git_repo(self):
        """
        Return a path to a git repository

        This is the entry point for external callers.
        This method finds a git repository by allowing the
        user to browse to one on the filesystem or by creating
        a new one with git-clone.

        """
        self.raise_()
        self.show()
        if self.exec_() == QtGui.QDialog.Accepted:
            return self._gitdir
        return None

    def _open(self):
        self._gitdir = self._get_selected_bookmark()
        if not self._gitdir:
            self._gitdir = qtutils.opendir_dialog(self,
                                              'Open Git Repository...',
                                              os.getcwd())
        if self._gitdir:
            self.accept()

    def _clone(self):
        gitdir = guicmds.clone_repo(self, spawn=False)
        if gitdir:
            self._gitdir = gitdir
            self.accept()

    def _open_bookmark(self, index):
        if(index.row() == 0):
            self._open()
        else:
            self._gitdir = unicode(self._bookmark_model.data(index).toString())
            if self._gitdir:
                self.accept()

    def _get_selected_bookmark(self):
        selected = self._bookmark_list.selectedIndexes()
        if(len(selected) > 0 and selected[0].row() != 0):
            return unicode(self._bookmark_model.data(selected[0]).toString())
        return None
