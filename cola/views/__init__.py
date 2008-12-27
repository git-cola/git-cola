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

from cola.syntax import DiffSyntaxHighlighter
from cola.syntax import LogSyntaxHighlighter
from cola.views.standard import create_standard_view
from cola.core import decode

try:
    from main import View
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

# These are views that do not contain any custom methods
OptionsView = create_standard_view(Ui_options, QDialog)
BranchCompareView = create_standard_view(Ui_branchview, QDialog)
CreateBranchView = create_standard_view(Ui_createbranch, QDialog)
BookmarkView = create_standard_view(Ui_bookmark, QDialog)
StashView = create_standard_view(Ui_stash, QDialog)
CompareView = create_standard_view(Ui_compare, QDialog)

class LogView(create_standard_view(Ui_logger, QDialog)):
    """A simple dialog to display command logs."""
    def init(self, parent=None, output=None):
        self.setWindowTitle(self.tr('Git Command Log'))
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
        for line in unicode(decode(output)).splitlines():
            cursor.insertText(line + '\n')
        cursor.insertText('\n')
        cursor.movePosition(cursor.End)
        text.setTextCursor(cursor)

class ItemView(object):
    def init(self, parent, title="", items=[], dblclick=None):
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

class ComboView(create_standard_view(Ui_combo, QDialog, ItemView), ItemView):
    """A dialog for choosing branches."""
    def idx(self):
        return self.items_widget.currentIndex()
    def value(self):
        return str(self.items_widget.currentText())

class ListView(create_standard_view(Ui_items, QDialog, ItemView), ItemView):
    """A dialog for an item from a list."""
    def idx(self):
        return self.items_widget.currentRow()
    def value(self):
        item = self.items_widget.currentItem()
        if not item:
            return None
        return str(item.text())

class CommitView(create_standard_view(Ui_commit, QDialog)):
    def init(self, parent=None, title=None):
        if title: self.setWindowTitle(title)
        # Make the list widget slighty larger
        self.splitter.setSizes([ 50, 200 ])
        self.syntax = DiffSyntaxHighlighter(self.commit_text.document(),
                                            whitespace=False)

class SearchView(create_standard_view(Ui_search, QDialog)):
    def init(self, parent=None):
        self.input.setFocus()
        self.syntax = DiffSyntaxHighlighter(self.commit_text.document(),
                                            whitespace=False)

class MergeView(create_standard_view(Ui_merge, QDialog)):
    def init(self, parent=None):
        self.revision.setFocus()

class RemoteView(create_standard_view(Ui_remote, QDialog)):
    def init(self, parent=None, button_text=''):
        if button_text:
            self.action_button.setText(button_text)
            self.setWindowTitle(button_text)
    def select_first_remote(self):
        item = self.remotes.item(0)
        if item:
            self.remotes.setItemSelected(item, True)
            self.remotes.setCurrentItem(item)
            self.remotename.setText(item.text())
            return True
        else:
            return False
