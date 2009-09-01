from PyQt4 import QtGui

from cola.gui.search import Ui_search
from cola.views.standard import create_standard_view
from cola.views.syntax import DiffSyntaxHighlighter

SearchViewBase = create_standard_view(Ui_search, QtGui.QDialog)
class SearchView(SearchViewBase):
    def __init__(self, parent=None):
        SearchViewBase.__init__(self, parent)
        self.query.setFocus()
        self.syntax = DiffSyntaxHighlighter(self.commit_text.document(),
                                            whitespace=False)
