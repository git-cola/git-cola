"""
Provides the git-cola startup dialog

The startup dialog is presented when no repositories can be
found at startup.

"""
import os

from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola import qtutils
from cola import guicmds


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
        self.setLayout(self._layt)

        self.connect(self._open_btn, SIGNAL('clicked()'), self._open)
        self.connect(self._clone_btn, SIGNAL('clicked()'), self._clone)
        self.connect(self._close_btn, SIGNAL('clicked()'), self.reject)

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
