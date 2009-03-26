"""This module creates simple wrapper classes around the auto-generated
.ui classes.
"""


import sys
import time

from PyQt4 import QtCore
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QListWidget
from PyQt4.QtGui import qApp
from PyQt4.QtCore import SIGNAL

from cola import core
from cola.views.standard import create_standard_view
from cola.views.syntax import DiffSyntaxHighlighter
from cola.views.syntax import LogSyntaxHighlighter

try:
    from main import View
    from cola.gui.about import Ui_about
    from cola.gui.bookmark import Ui_bookmark
    from cola.gui.branchview import Ui_branchview
    from cola.gui.combo import Ui_combo
    from cola.gui.commit import Ui_commit
    from cola.gui.compare import Ui_compare
    from cola.gui.createbranch import Ui_createbranch
    from cola.gui.items import Ui_items
    from cola.gui.logger import Ui_logger
    from cola.gui.merge import Ui_merge
    from cola.gui.options import Ui_options
    from cola.gui.remote import Ui_remote
    from cola.gui.search import Ui_search
    from cola.gui.stash import Ui_stash
except ImportError:
    sys.stderr.write('\nThe cola gui modules have not been built.\n'
                     'Try running "make" in the cola source tree.\n')
    sys.exit(-1)

class AboutView(Ui_about, QDialog):
    def __init__(self, parent):
        QDialog.__init__(self, parent)
        Ui_about.__init__(self)
        self.setupUi(self)
    def set_version(self, version):
        self.spam.setText(self.spam.text().replace('$VERSION', version))

OptionsView = create_standard_view(Ui_options, QDialog)
BranchCompareView = create_standard_view(Ui_branchview, QDialog)
CreateBranchView = create_standard_view(Ui_createbranch, QDialog)
BookmarkView = create_standard_view(Ui_bookmark, QDialog)
StashView = create_standard_view(Ui_stash, QDialog)
CompareView = create_standard_view(Ui_compare, QDialog)

LogViewBase = create_standard_view(Ui_logger, QDialog)
class LogView(LogViewBase):
    """A simple dialog to display command logs."""
    def __init__(self, parent=None, output=None):
        LogViewBase.__init__(self, parent)
        self.syntax = LogSyntaxHighlighter(self.output_text.document())
        if output:
            self.set_output(output)
    def clear(self):
        self.output_text.clear()
    def set_output(self, output):
        self.output_text.setText(output)
    def log(self, output):
        if not output:
            return
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        text = self.output_text
        cursor.insertText(time.asctime() + '\n')
        for line in unicode(core.decode(output)).splitlines():
            cursor.insertText(line + '\n')
        cursor.insertText('\n')
        cursor.movePosition(cursor.End)
        text.setTextCursor(cursor)

class ItemView(object):
    def __init__(self, parent, title="", items=[], dblclick=None):
        self.setWindowTitle(title)
        self.items_widget.addItems(items)
        if dblclick and type(self.items_widget) is QListWidget:
            self.connect(self.items_widget,
                         SIGNAL('itemDoubleClicked(QListWidgetItem*)'),
                         dblclick)
    def idx(self):
        return 0
    def get_selected(self):
        geom = qApp.desktop().screenGeometry()
        width = geom.width()
        height = geom.height()
        x = self.parent_view.x() + self.parent_view.width()/2 - self.width()/2
        y = self.parent_view.y() + self.parent_view.height()/3 - self.height()/2
        self.move(x, y)
        self.show()
        if self.exec_() == QDialog.Accepted:
            return self.value()
        else:
            return None

ComboViewBase = create_standard_view(Ui_combo, QDialog, ItemView)
class ComboView(ComboViewBase, ItemView):
    """A dialog for choosing branches."""
    def idx(self):
        return self.items_widget.currentIndex()
    def value(self):
        return str(self.items_widget.currentText())

ListViewBase = create_standard_view(Ui_items, QDialog, ItemView)
class ListView(ListViewBase, ItemView):
    """A dialog for an item from a list."""
    def idx(self):
        return self.items_widget.currentRow()
    def value(self):
        item = self.items_widget.currentItem()
        if not item:
            return None
        return str(item.text())

CommitViewBase = create_standard_view(Ui_commit, QDialog)
class CommitView(CommitViewBase):
    def __init__(self, parent=None, title=None):
        CommitViewBase.__init__(self, parent)
        if title:
            self.setWindowTitle(title)
        # Make the list widget slighty larger
        self.splitter.setSizes([ 50, 200 ])
        self.syntax = DiffSyntaxHighlighter(self.commit_text.document(),
                                            whitespace=False)

SearchViewBase = create_standard_view(Ui_search, QDialog)
class SearchView(SearchViewBase):
    def __init__(self, parent=None):
        SearchViewBase.__init__(self, parent)
        self.input.setFocus()
        self.syntax = DiffSyntaxHighlighter(self.commit_text.document(),
                                            whitespace=False)

MergeViewBase = create_standard_view(Ui_merge, QDialog)
class MergeView(MergeViewBase):
    def __init__(self, parent=None):
        MergeViewBase.__init__(self, parent)
        self.revision.setFocus()

RemoteViewBase = create_standard_view(Ui_remote, QDialog)
class RemoteView(RemoteViewBase):
    def __init__(self, parent, action): 
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
        return self.select_remote(0)
    def select_remote(self, idx):
        item = self.remotes.item(idx)
        if item:
            self.remotes.setItemSelected(item, True)
            self.remotes.setCurrentItem(item)
            self.remotename.setText(item.text())
            return True
        else:
            return False
