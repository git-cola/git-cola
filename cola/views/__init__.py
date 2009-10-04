"""Provides access to view classes."""


import sys
import time

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QListWidget
from PyQt4.QtGui import qApp
from PyQt4.QtCore import SIGNAL

from cola import core
from cola.views.standard import create_standard_view
from cola.views.bookmark import BookmarkView
from cola.views.option import OptionsView
from cola.views.syntax import DiffSyntaxHighlighter

try:
    from cola.gui.remote import Ui_remote
except ImportError:
    sys.stderr.write('\nThe cola gui modules have not been built.\n'
                     'Try running "make" in the cola source tree.\n')
    sys.exit(-1)


from cola.views.compare import CompareView
from cola.views.compare import BranchCompareView
from cola.views.combo import ComboView
from cola.views.createbranch import CreateBranchView
from cola.views.stash import StashView
from cola.views.itemlist import ListView


RemoteViewBase = create_standard_view(Ui_remote, QDialog)
class RemoteView(RemoteViewBase):
    """Dialog used by Fetch, Push and Pull"""

    def __init__(self, parent, action):
        """Customizes the dialog based on the remote action
        """
        RemoteViewBase.__init__(self, parent)
        if action:
            self.action_button.setText(action.title())
            self.setWindowTitle(action.title())
        if action == 'pull':
            self.tags_checkbox.hide()
            self.ffwd_only_checkbox.hide()
            self.local_label.hide()
            self.local_branch.hide()
            self.local_branches.hide()
        if action != 'pull':
            self.rebase_checkbox.hide()

    def select_first_remote(self):
        """Selects the first remote in the list view"""
        return self.select_remote(0)

    def select_remote(self, idx):
        """Selects a remote by index"""
        item = self.remotes.item(idx)
        if item:
            self.remotes.setItemSelected(item, True)
            self.remotes.setCurrentItem(item)
            self.remotename.setText(item.text())
            return True
        else:
            return False

    def select_local_branch(self, idx):
        """Selects a local branch by index in the list view"""
        item = self.local_branches.item(idx)
        if not item:
            return False
        self.local_branches.setItemSelected(item, True)
        self.local_branches.setCurrentItem(item)
        self.local_branch.setText(item.text())
        return True
