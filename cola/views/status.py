from PyQt4 import QtGui

import cola
from cola import qtutils


_widget = None
def widget(parent=None):
    global _widget
    if _widget:
        return _widget
    _widget = StatusWidget(parent)
    return _widget


class StatusWidget(QtGui.QDialog):
    """
    Provides a git-status-like repository widget.

    This widget observes the main model and broadcasts
    Qt signals.

    """
    # Item categories
    idx_staged = 0
    idx_modified = 1
    idx_unmerged = 2
    idx_untracked = 3
    idx_end = 4

    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.layout = QtGui.QVBoxLayout(self)
        self.setLayout(self.layout)

        self.tree = QtGui.QTreeWidget(self)
        self.layout.addWidget(self.tree)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.tree.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.tree.setAnimated(True)
        self.tree.setHeaderHidden(True)
        self.tree.setAllColumnsShowFocus(True)
        self.tree.setSortingEnabled(False)

        self.add_item('Staged', 'plus.png')
        self.add_item('Modified', 'modified.png')
        self.add_item('Unmerged', 'unmerged.png')
        self.add_item('Untracked', 'untracked.png')

        self._expanded_items = set()
        self.model = cola.model()
        self.model.add_message_observer(self.model.message_updated,
                                        self.refresh)

    def add_item(self, txt, path):
        """Create a new top-level item in the status tree."""
        item = QtGui.QTreeWidgetItem(self.tree)
        item.setText(0, self.tr(txt))
        item.setIcon(0, qtutils.icon(path))

    def refresh(self, subject, message):
        self.set_staged(self.model.staged)
        self.set_modified(self.model.modified)
        self.set_unmerged(self.model.unmerged)
        self.set_untracked(self.model.untracked)

    def set_staged(self, items, check=True):
        """Adds items to the 'Staged' subtree."""
        self._set_subtree(items, self.idx_staged, staged=True, check=check)

    def set_modified(self, items):
        """Adds items to the 'Modified' subtree."""
        self._set_subtree(items, self.idx_modified)

    def set_unmerged(self, items):
        """Adds items to the 'Unmerged' subtree."""
        self._set_subtree(items, self.idx_unmerged)

    def set_untracked(self, items):
        """Adds items to the 'Untracked' subtree."""
        self._set_subtree(items, self.idx_untracked)

    def _set_subtree(self, items, idx,
                     staged=False,
                     untracked=False,
                     check=True):
        """Add a list of items to a treewidget item."""
        parent = self.tree.topLevelItem(idx)
        parent.takeChildren()
        for item in items:
            treeitem = qtutils.create_treeitem(item,
                                               staged=staged,
                                               check=check,
                                               untracked=untracked)
            parent.addChild(treeitem)
        self.expand_items(idx, items)
        if items:
            self.tree.setItemHidden(parent, False)
        else:
            self.tree.setItemHidden(parent, True)

    def expand_items(self, idx, items):
        """Expand the top-level category "folder" once and only once."""
        # Don't do this if items is empty; this makes it so that we
        # don't add the top-level index into the expanded_items set
        # an item appears in a particular category.
        if not items:
            return
        # Only run this once; we don't want to re-expand items that
        # we've click on to re-collapse on refresh.
        if idx in self._expanded_items:
            return
        self._expanded_items.add(idx)
        for idx in xrange(self.idx_end):
            item = self.tree.topLevelItem(idx)
            if item:
                self.tree.expandItem(item)
