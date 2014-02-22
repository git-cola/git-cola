"""
Provides the git-cola startup dialog

The startup dialog is presented when no repositories can be
found at startup.

"""
from __future__ import division, absolute_import

import os

from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import guicmds
from cola import settings
from cola import qtutils
from cola.i18n import N_
from cola.widgets import defs


class StartupDialog(QtGui.QDialog):
    """Provides a GUI to Open or Clone a git repository."""

    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        self.setWindowTitle(N_('git-cola'))
        self._gitdir = None

        self._layt = QtGui.QHBoxLayout()
        self._layt.setMargin(defs.margin)
        self._layt.setSpacing(defs.spacing)

        self._new_btn = QtGui.QPushButton(N_('New...'))
        self._new_btn.setIcon(qtutils.new_icon())

        self._open_btn = QtGui.QPushButton(N_('Open...'))
        self._open_btn.setIcon(qtutils.open_icon())

        self._clone_btn = QtGui.QPushButton(N_('Clone...'))
        self._clone_btn.setIcon(qtutils.git_icon())

        self._close_btn = QtGui.QPushButton(N_('Close'))

        self._layt.addWidget(self._open_btn)
        self._layt.addWidget(self._clone_btn)
        self._layt.addWidget(self._new_btn)
        self._layt.addStretch()
        self._layt.addWidget(self._close_btn)

        self.model = settings.Settings()

        self._vlayt = QtGui.QVBoxLayout()
        self._vlayt.setMargin(defs.margin)
        self._vlayt.setSpacing(defs.margin)

        self._bookmark_label = QtGui.QLabel(N_('Select Repository...'))
        self._bookmark_label.setAlignment(Qt.AlignCenter)

        self._bookmark_model = QtGui.QStandardItemModel()

        item = QtGui.QStandardItem(N_('Select manually...'))
        item.setEditable(False)
        self._bookmark_model.appendRow(item)

        added = set()
        all_repos = self.model.bookmarks + self.model.recent

        for repo in all_repos:
            if repo in added:
                continue
            added.add(repo)
            item = QtGui.QStandardItem(repo)
            item.setEditable(False)
            self._bookmark_model.appendRow(item)

        selection_mode = QtGui.QAbstractItemView.SingleSelection

        self._bookmark_list = QtGui.QListView()
        self._bookmark_list.setSelectionMode(selection_mode)
        self._bookmark_list.setAlternatingRowColors(True)
        self._bookmark_list.setModel(self._bookmark_model)

        if not all_repos:
            self._bookmark_label.setMinimumHeight(1)
            self._bookmark_list.setMinimumHeight(1)
            self._bookmark_label.hide()
            self._bookmark_list.hide()

        self._vlayt.addWidget(self._bookmark_label)
        self._vlayt.addWidget(self._bookmark_list)
        self._vlayt.addLayout(self._layt)

        self.setLayout(self._vlayt)

        qtutils.connect_button(self._open_btn, self._open)
        qtutils.connect_button(self._clone_btn, self._clone)
        qtutils.connect_button(self._new_btn, self._new)
        qtutils.connect_button(self._close_btn, self.reject)

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
        self.show()
        self.raise_()
        if self.exec_() == QtGui.QDialog.Accepted:
            return self._gitdir
        return None

    def _open(self):
        self._gitdir = self._get_selected_bookmark()
        if not self._gitdir:
            self._gitdir = qtutils.opendir_dialog(N_('Open Git Repository...'),
                                                  os.getcwd())
        if self._gitdir:
            self.accept()

    def _clone(self):
        gitdir = guicmds.clone_repo(spawn=False)
        if gitdir:
            self._gitdir = gitdir
            self.accept()

    def _new(self):
        gitdir = guicmds.new_repo()
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
