from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

import cola
from cola import signals
from cola import qtutils
from cola.qtutils import SLOT


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
    idx_header = -1
    idx_staged = 0
    idx_modified = 1
    idx_unmerged = 2
    idx_untracked = 3
    idx_end = 4

    mode = property(lambda self: self.model.mode,
                    lambda self, m: self.model.set_mode(m))

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

        self.expanded_items = set()
        self.model = cola.model()
        self.model.add_message_observer(self.model.message_updated,
                                        self.refresh)
        # Handle these events here
        self.tree.contextMenuEvent = self.tree_context_menu_event
        self.tree.mousePressEvent = self.tree_click

        self.connect(self.tree, SIGNAL('itemSelectionChanged()'),
                     self.tree_selection)

    def add_item(self, txt, path):
        """Create a new top-level item in the status tree."""
        item = QtGui.QTreeWidgetItem(self.tree)
        item.setText(0, self.tr(txt))
        item.setIcon(0, qtutils.icon(path))

    def refresh(self, subject, message):
        """Update display from model data."""
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
        if idx in self.expanded_items:
            return
        self.expanded_items.add(idx)
        for idx in xrange(self.idx_end):
            item = self.tree.topLevelItem(idx)
            if item:
                self.tree.expandItem(item)

    def tree_context_menu_event(self, event):
        """Create context menus for the repo status tree."""
        menu = self.tree_context_menu_setup()
        menu.exec_(self.tree.mapToGlobal(event.pos()))

    def tree_context_menu_setup(self):
        """Set up the status menu for the repo status tree."""
        staged, modified, unmerged, untracked = self.selection()
        menu = QtGui.QMenu(self)

        if staged:
            menu.addAction(self.tr('Unstage Selected'),
                           SLOT(signals.unstage, self.staged()))
            menu.addSeparator()
            menu.addAction(self.tr('Launch Editor'),
                           SLOT(signals.edit, self.staged()))
            menu.addAction(self.tr('Launch Diff Tool'),
                           SLOT(signals.difftool, self.staged()))
            return menu

        if unmerged:
            if not utils.is_broken():
                menu.addAction(self.tr('Launch Merge Tool'),
                               SLOT(signals.mergetool, self.unmerged()))
            menu.addAction(self.tr('Launch Editor'),
                           SLOT(signals.edit, self.unmerged()))
            menu.addSeparator()
            menu.addAction(self.tr('Stage Selected'),
                           SLOT(signals.stage, self.unmerged()))
            return menu

        enable_staging = self.model.enable_staging()
        if enable_staging:
            menu.addAction(self.tr('Stage Selected'),
                           SLOT(signals.stage, self.modified()))
            menu.addSeparator()

        menu.addAction(self.tr('Launch Editor'),
                       SLOT(signals.edit, self.unstaged()))

        if modified and enable_staging:
            menu.addAction(self.tr('Launch Diff Tool'),
                           SLOT(signals.difftool, self.modified()))
            menu.addSeparator()
            menu.addAction(self.tr('Undo All Changes'),
                           SLOT(signals.checkout, self.modified()))

        if untracked:
            menu.addSeparator()
            menu.addAction(self.tr('Delete File(s)'),
                           SLOT(signals.delete, self.untracked()))

        return menu

    def selected_indexes(self):
        """Returns a list of (category, row) representing the tree selection."""
        selected = self.tree.selectedIndexes()
        result = []
        for idx in selected:
            if idx.parent().isValid():
                parent_idx = idx.parent()
                entry = (parent_idx.row(), idx.row())
            else:
                entry = (-1, idx.row())
            result.append(entry)
        return result
    def staged(self):
        return self._subtree_selection(self.idx_staged, self.model.staged)

    def unstaged(self):
        return self.modified() + self.unmerged() + self.untracked()

    def modified(self):
        return self._subtree_selection(self.idx_modified, self.model.modified)

    def unmerged(self):
        return self._subtree_selection(self.idx_unmerged, self.model.unmerged)

    def untracked(self):
        return self._subtree_selection(self.idx_untracked, self.model.untracked)

    def _subtree_selection(self, idx, items):
        item = self.tree.topLevelItem(idx)
        return qtutils.tree_selection(item, items)

    def tree_click(self, event):
        """
        Called when a repo status tree item is clicked.

        This handles the behavior where clicking on the icon invokes
        the same appropriate action.

        """
        # Get the item that was clicked
        result = QtGui.QTreeWidget.mousePressEvent(self.tree, event)
        item = self.tree.itemAt(event.pos())
        if not item:
            # Nothing was clicked -- reset the display and return
            cola.notifier().broadcast(signals.reset_mode)
            items = self.tree.selectedItems()
            self.tree.blockSignals(True)
            for i in items:
                i.setSelected(False)
            self.tree.blockSignals(False)
            return result

        # An item was clicked -- get its index in the model
        staged, idx = self.index_for_item(item)
        if idx == self.idx_header:
            return result

        if self.model.read_only():
            return result

        # handle when the icons are clicked
        xpos = event.pos().x()
        if xpos > 42 and xpos < 58:
            if staged:
                # A staged item was clicked
                cola.notifier().broadcast(signals.unstage, self.staged())
                #self.log(*self.model.reset_helper(selected))
                #self.rescan()
            else:
                # An unstaged item was clicked
                selected = self.unstaged()
                if selected:
                    cola.notifier().broadcast(signals.stage, selected)
                    #self.log(*self.model.add_or_remove(selected))
                    #self.rescan()
        return result

    def tree_selection(self):
        """Show a data for the selected item."""
        selection = self.selected_indexes()
        if not selection:
            return
        category, idx = selection[0]
        # A header item e.g. 'Staged', 'Modified', etc.
        if category == self.idx_header:
            signal = {
                self.idx_staged: signals.staged_summary,
                self.idx_modified: signals.modified_summary,
                self.idx_unmerged: signals.unmerged_summary,
                self.idx_untracked: signals.untracked_summary,
            }.get(idx, signals.diffstat)
            cola.notifier().broadcast(signal)
            #diff = self.generate_header_data(idx)
            #self.view.set_display(diff)
        # A staged file
        elif category == self.idx_staged:
            #self.view_diff(staged=True)
            cola.notifier().broadcast(signals.diff_staged, self.staged())

        # A modified file
        elif category == self.idx_modified:
            cola.notifier().broadcast(signals.diff, self.modified())

        elif category == self.idx_unmerged:
            cola.notifier().broadcast(signals.diff, self.unmerged())

        elif category == self.idx_untracked:
            cola.notifier().broadcast(signals.show_untracked, self.unstaged())

    def index_for_item(self, item):
        """
        Given an item, returns the index of the item.

        The indexes for unstaged items are grouped such that
        the index of unmerged[1] = len(modified) + 1, etc.

        """
        if not item:
            return False, -1

        parent = item.parent()
        if not parent:
            return False, -1

        pidx = self.tree.indexOfTopLevelItem(parent)
        if pidx == self.idx_staged:
            return True, parent.indexOfChild(item)
        elif pidx == self.idx_modified:
            return False, parent.indexOfChild(item)

        count = self.tree.topLevelItem(self.idx_modified).childCount()
        if pidx == self.idx_unmerged:
            return False, count + parent.indexOfChild(item)

        count += self.tree.topLevelItem(self.idx_unmerged).childCount()
        if pidx == self.idx_untracked:
            return False, count + parent.indexOfChild(item)

        return False, -1
