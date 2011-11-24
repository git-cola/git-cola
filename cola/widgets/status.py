import os
import copy
import subprocess
import itertools

from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

import cola
from cola import signals
from cola import qtutils
from cola.compat import set
from cola.qtutils import SLOT


def select_item(tree, item):
    if not item:
        return
    tree.setItemSelected(item, True)
    parent = item.parent()
    if parent:
        tree.scrollToItem(parent)
    tree.scrollToItem(item)


class StatusWidget(QtGui.QWidget):
    """
    Provides a git-status-like repository widget.

    This widget observes the main model and broadcasts
    Qt signals.

    """
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.layout = QtGui.QVBoxLayout(self)
        self.setLayout(self.layout)

        self.tree = StatusTreeWidget(self)
        self.layout.addWidget(self.tree)
        self.layout.setContentsMargins(0, 0, 0, 0)


class StatusTreeWidget(QtGui.QTreeWidget):
    # Item categories
    idx_header = -1
    idx_staged = 0
    idx_modified = 1
    idx_unmerged = 2
    idx_untracked = 3
    idx_end = 4

    # Read-only access to the mode state
    mode = property(lambda self: self.m.mode)

    def __init__(self, parent):
        QtGui.QTreeWidget.__init__(self, parent)

        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.headerItem().setHidden(True)
        self.setAllColumnsShowFocus(True)
        self.setSortingEnabled(False)
        self.setUniformRowHeights(True)
        self.setAnimated(True)

        self.add_item('Staged', 'plus.png', hide=True)
        self.add_item('Modified', 'modified.png', hide=True)
        self.add_item('Unmerged', 'unmerged.png', hide=True)
        self.add_item('Untracked', 'untracked.png', hide=True)

        # Used to restore the selection
        self.old_scroll = None
        self.old_selection = None
        self.old_contents = None

        self.expanded_items = set()

        self.connect(self, SIGNAL('about_to_update'), self._about_to_update)
        self.connect(self, SIGNAL('updated'), self._updated)

        self.m = cola.model()
        self.m.add_message_observer(self.m.message_about_to_update,
                                    self.about_to_update)
        self.m.add_message_observer(self.m.message_updated, self.updated)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self.show_selection)
        self.connect(self,
                     SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self.double_clicked)
        self.connect(self,
                     SIGNAL('itemClicked(QTreeWidgetItem*,int)'),
                     self.clicked)

    def add_item(self, txt, path, hide=False):
        """Create a new top-level item in the status tree."""
        item = QtGui.QTreeWidgetItem(self)
        item.setText(0, self.tr(txt))
        item.setIcon(0, qtutils.icon(path))
        if hide:
            self.setItemHidden(item, True)

    def restore_selection(self):
        if not self.old_selection or not self.old_contents:
            return

        (staged, modified, unmerged, untracked) = self.old_contents

        (staged_sel, modified_sel,
         unmerged_sel, untracked_sel) = self.old_selection

        (updated_staged, updated_modified,
         updated_unmerged, updated_untracked) = self.contents()

        def select_modified(item):
            idx = updated_modified.index(item)
            select_item(self, self.modified_item(idx))

        def select_unmerged(item):
            idx = updated_unmerged.index(item)
            select_item(self, self.unmerged_item(idx))

        def select_untracked(item):
            idx = updated_untracked.index(item)
            select_item(self, self.untracked_item(idx))

        def select_staged(item):
            idx = updated_staged.index(item)
            select_item(self, self.staged_item(idx))

        restore_selection_actions = (
            (updated_modified, modified, modified_sel, select_modified),
            (updated_unmerged, unmerged, unmerged_sel, select_unmerged),
            (updated_untracked, untracked, untracked_sel, select_untracked),
            (updated_staged, staged, staged_sel, select_staged),
        )

        for (new, old, selection, action) in restore_selection_actions:
            # When modified is staged, select the next modified item
            # When unmerged is staged, select the next unmerged item
            # When untracked is staged, select the next untracked item
            # When something is unstaged we should select the next staged item
            new_set = set(new)
            if len(new) < len(old) and old:
                for idx, i in enumerate(old):
                    if i not in new_set:
                        for j in itertools.chain(old[idx+1:],
                                                 reversed(old[:idx])):
                            if j in new_set:
                                action(j)
                                return

        for (new, old, selection, action) in restore_selection_actions:
            # Reselect items when doing partial-staging
            new_set = set(new)
            for item in selection:
                if item in new_set:
                    action(item)

    def staged_item(self, itemidx):
        return self._subtree_item(self.idx_staged, itemidx)

    def modified_item(self, itemidx):
        return self._subtree_item(self.idx_modified, itemidx)

    def unmerged_item(self, itemidx):
        return self._subtree_item(self.idx_unmerged, itemidx)

    def untracked_item(self, itemidx):
        return self._subtree_item(self.idx_untracked, itemidx)

    def unstaged_item(self, itemidx):
        # is it modified?
        item = self.topLevelItem(self.idx_modified)
        count = item.childCount()
        if itemidx < count:
            return item.child(itemidx)
        # is it unmerged?
        item = self.topLevelItem(self.idx_unmerged)
        count += item.childCount()
        if itemidx < count:
            return item.child(itemidx)
        # is it untracked?
        item = self.topLevelItem(self.idx_untracked)
        count += item.childCount()
        if itemidx < count:
            return item.child(itemidx)
        # Nope..
        return None

    def _subtree_item(self, idx, itemidx):
        parent = self.topLevelItem(idx)
        return parent.child(itemidx)

    def about_to_update(self):
        self.emit(SIGNAL('about_to_update'))

    def _about_to_update(self):
        self.old_selection = copy.deepcopy(self.selection())
        self.old_contents = copy.deepcopy(self.contents())

        self.old_scroll = None
        vscroll = self.verticalScrollBar()
        if vscroll:
            self.old_scroll = vscroll.value()

    def updated(self):
        """Update display from model data."""
        self.emit(SIGNAL('updated'))

    def _updated(self):
        self.set_staged(self.m.staged)
        self.set_modified(self.m.modified)
        self.set_unmerged(self.m.unmerged)
        self.set_untracked(self.m.untracked)

        vscroll = self.verticalScrollBar()
        if vscroll and self.old_scroll is not None:
            vscroll.setValue(self.old_scroll)
            self.old_scroll = None

        self.restore_selection()

        if not self.m.staged:
            return

        staged = self.topLevelItem(self.idx_staged)
        if self.mode in self.m.modes_read_only:
            staged.setText(0, self.tr('Changed'))
        else:
            staged.setText(0, self.tr('Staged'))

    def set_staged(self, items):
        """Adds items to the 'Staged' subtree."""
        self._set_subtree(items, self.idx_staged, staged=True,
                          check=not self.m.read_only())

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
        parent = self.topLevelItem(idx)
        if items:
            self.setItemHidden(parent, False)
        else:
            self.setItemHidden(parent, True)
        parent.takeChildren()
        for item in items:
            treeitem = qtutils.create_treeitem(item,
                                               staged=staged,
                                               check=check,
                                               untracked=untracked)
            parent.addChild(treeitem)
        self.expand_items(idx, items)

    def expand_items(self, idx, items):
        """Expand the top-level category "folder" once and only once."""
        # Don't do this if items is empty; this makes it so that we
        # don't add the top-level index into the expanded_items set
        # until an item appears in a particular category.
        if not items:
            return
        # Only run this once; we don't want to re-expand items that
        # we've clicked on to re-collapse on updated().
        if idx in self.expanded_items:
            return
        self.expanded_items.add(idx)
        item = self.topLevelItem(idx)
        if item:
            self.expandItem(item)

    def contextMenuEvent(self, event):
        """Create context menus for the repo status tree."""
        menu = self.create_context_menu()
        menu.exec_(self.mapToGlobal(event.pos()))

    def create_context_menu(self):
        """Set up the status menu for the repo status tree."""
        staged, modified, unmerged, untracked = self.selection()
        menu = QtGui.QMenu(self)

        enable_staging = self.m.enable_staging()
        if not enable_staging:
            menu.addAction(qtutils.icon('remove.svg'),
                           self.tr('Unstage Selected'),
                           SLOT(signals.unstage, self.staged()))

        if staged and staged[0] in self.m.submodules:
            menu.addAction(qtutils.git_icon(),
                           self.tr('Launch git-cola'),
                           SLOT(signals.open_repo, os.path.abspath(staged[0])))
            return menu
        elif staged:
            menu.addSeparator()
            menu.addAction(qtutils.icon('open.svg'),
                           self.tr('Launch Editor'),
                           SLOT(signals.edit, self.staged()))
            menu.addAction(qtutils.git_icon(),
                           self.tr('Launch Diff Tool'),
                           SLOT(signals.difftool, True, self.staged()))
            menu.addSeparator()
            menu.addAction(qtutils.icon('undo.svg'),
                           self.tr('Revert Unstaged Edits...'),
                           lambda: self._revert_unstaged_edits(use_staged=True))
            return menu

        if unmerged:
            menu.addAction(qtutils.git_icon(),
                           self.tr('Launch Merge Tool'),
                           SLOT(signals.mergetool, self.unmerged()))
            menu.addAction(qtutils.icon('open.svg'),
                           self.tr('Launch Editor'),
                           SLOT(signals.edit, self.unmerged()))
            menu.addSeparator()
            menu.addAction(qtutils.icon('add.svg'),
                           self.tr('Stage Selected'),
                           SLOT(signals.stage, self.unmerged()))
            return menu

        modified_submodule = (modified and
                              modified[0] in self.m.submodules)
        if enable_staging:
            menu.addAction(qtutils.icon('add.svg'),
                           self.tr('Stage Selected'),
                           SLOT(signals.stage, self.unstaged()))
            menu.addSeparator()

        if modified_submodule:
            menu.addAction(qtutils.git_icon(),
                           self.tr('Launch git-cola'),
                           SLOT(signals.open_repo,
                                os.path.abspath(modified[0])))
        elif self.unstaged():
            menu.addAction(qtutils.icon('open.svg'),
                           self.tr('Launch Editor'),
                           SLOT(signals.edit, self.unstaged()))

        if modified and enable_staging and not modified_submodule:
            menu.addAction(qtutils.git_icon(),
                           self.tr('Launch Diff Tool'),
                           SLOT(signals.difftool, False, self.modified()))
            menu.addSeparator()
            menu.addAction(qtutils.icon('undo.svg'),
                           self.tr('Revert Unstaged Edits...'),
                           self._revert_unstaged_edits)
            menu.addAction(qtutils.icon('undo.svg'),
                           self.tr('Revert Uncommited Edits...'),
                           self._revert_uncommitted_edits)

        if untracked:
            menu.addSeparator()
            menu.addAction(qtutils.discard_icon(),
                           self.tr('Delete File(s)...'), self._delete_files)
            menu.addSeparator()
            menu.addAction(qtutils.icon('edit-clear.svg'),
                           self.tr('Add to .gitignore'),
                           SLOT(signals.ignore,
                                map(lambda x: '/' + x, self.untracked())))
        return menu

    def _delete_files(self):
        files = self.untracked()
        count = len(files)
        if count == 0:
            return

        title = 'Delete Files?'
        msg = self.tr('The following files will be deleted:\n\n')

        fileinfo = subprocess.list2cmdline(files)
        if len(fileinfo) > 2048:
            fileinfo = fileinfo[:2048].rstrip() + '...'
        msg += fileinfo

        info_txt = unicode(self.tr('Delete %d file(s)?')) % count
        ok_txt = 'Delete Files'

        if qtutils.confirm(title, msg, info_txt, ok_txt,
                           default=False,
                           icon=qtutils.discard_icon()):
            cola.notifier().broadcast(signals.delete, files)

    def _revert_unstaged_edits(self, use_staged=False):
        if not self.m.undoable():
            return
        if use_staged:
            items_to_undo = self.staged()
        else:
            items_to_undo = self.modified()

        if items_to_undo:
            if not qtutils.confirm('Revert Unstaged Changes?',
                                   'This operation drops unstaged changes.'
                                   '\nThese changes cannot be recovered.',
                                   'Revert the unstaged changes?',
                                   'Revert Unstaged Changes',
                                   default=False,
                                   icon=qtutils.icon('undo.svg')):
                return
            cola.notifier().broadcast(signals.checkout,
                                      ['--'] + items_to_undo)
        else:
            qtutils.log(1, self.tr('No files selected for '
                                   'checkout from HEAD.'))

    def _revert_uncommitted_edits(self):
        if not self.m.undoable():
            return
        items_to_undo = self.modified()
        if items_to_undo:
            if not qtutils.confirm('Revert Uncommitted Changes?',
                                   'This operation drops uncommitted changes.'
                                   '\nThese changes cannot be recovered.',
                                   'Revert the uncommitted changes?',
                                   'Revert Uncommitted Changes',
                                   default=False,
                                   icon=qtutils.icon('undo.svg')):
                return
            cola.notifier().broadcast(signals.checkout,
                                      ['HEAD', '--'] + items_to_undo)
        else:
            qtutils.log(1, self.tr('No files selected for '
                                   'checkout from HEAD.'))

    def single_selection(self):
        """Scan across staged, modified, etc. and return a single item."""
        staged, modified, unmerged, untracked = self.selection()
        s = None
        m = None
        um = None
        ut = None
        if staged:
            s = staged[0]
        elif modified:
            m = modified[0]
        elif unmerged:
            um = unmerged[0]
        elif untracked:
            ut = untracked[0]
        return s, m, um, ut

    def selected_indexes(self):
        """Returns a list of (category, row) representing the tree selection."""
        selected = self.selectedIndexes()
        result = []
        for idx in selected:
            if idx.parent().isValid():
                parent_idx = idx.parent()
                entry = (parent_idx.row(), idx.row())
            else:
                entry = (-1, idx.row())
            result.append(entry)
        return result

    def selection(self):
        """Return the current selection in the repo status tree."""
        return (self.staged(), self.modified(),
                self.unmerged(), self.untracked())

    def contents(self):
        return (self.m.staged, self.m.modified,
                self.m.unmerged, self.m.untracked)

    def staged(self):
        return self._subtree_selection(self.idx_staged, self.m.staged)

    def unstaged(self):
        return self.modified() + self.unmerged() + self.untracked()

    def modified(self):
        return self._subtree_selection(self.idx_modified, self.m.modified)

    def unmerged(self):
        return self._subtree_selection(self.idx_unmerged, self.m.unmerged)

    def untracked(self):
        return self._subtree_selection(self.idx_untracked, self.m.untracked)

    def _subtree_selection(self, idx, items):
        item = self.topLevelItem(idx)
        return qtutils.tree_selection(item, items)

    def mouseReleaseEvent(self, event):
        result = QtGui.QTreeWidget.mouseReleaseEvent(self, event)
        self.clicked()
        return result

    def clicked(self, item=None, idx=None):
        """Called when a repo status tree item is clicked.

        This handles the behavior where clicking on the icon invokes
        the a context-specific action.

        """
        if self.m.read_only():
            return

        # Sync the selection model
        staged, modified, unmerged, untracked = self.selection()
        cola.selection_model().set_selection(staged, modified,
                                             unmerged, untracked)

        # Clear the selection if an empty area was clicked
        selection = self.selected_indexes()
        if not selection:
            if self.mode == self.m.mode_amend:
                cola.notifier().broadcast(signals.set_diff_text, '')
            else:
                cola.notifier().broadcast(signals.reset_mode)
            self.blockSignals(True)
            self.clearSelection()
            self.blockSignals(False)
            return

        if staged:
            qtutils.set_clipboard(staged[0])
        elif modified:
            qtutils.set_clipboard(modified[0])
        elif unmerged:
            qtutils.set_clipboard(unmerged[0])
        elif untracked:
            qtutils.set_clipboard(untracked[0])

    def double_clicked(self, item, idx):
        """Called when an item is double-clicked in the repo status tree."""
        self._process_selection()

    def _process_selection(self):
        if self.m.read_only():
            return
        staged, modified, unmerged, untracked = self.selection()
        if staged:
            cola.notifier().broadcast(signals.unstage, staged)
        elif modified:
            cola.notifier().broadcast(signals.stage, modified)
        elif unmerged:
            cola.notifier().broadcast(signals.stage, unmerged)
        elif untracked:
            cola.notifier().broadcast(signals.stage, untracked)

    def show_selection(self):
        """Show the selected item."""
        # Sync the selection model
        s, m, um, ut = self.selection()
        cola.selection_model().set_selection(s, m, um, ut)

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
        # A staged file
        elif category == self.idx_staged:
            cola.notifier().broadcast(signals.diff_staged, self.staged())

        # A modified file
        elif category == self.idx_modified:
            cola.notifier().broadcast(signals.diff, self.modified())

        elif category == self.idx_unmerged:
            cola.notifier().broadcast(signals.diff, self.unmerged())

        elif category == self.idx_untracked:
            cola.notifier().broadcast(signals.show_untracked, self.unstaged())
