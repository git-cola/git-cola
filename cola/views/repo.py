from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola.utils

class RepoTreeView(QtGui.QTreeView):
    """Provides a filesystem-like view of a git repository."""
    def __init__(self, parent=None):
        QtGui.QTreeView.__init__(self, parent)
        self.setWindowTitle(self.tr('classic'))
        self.setSortingEnabled(False)
        self.setAllColumnsShowFocus(True)
        self.setAlternatingRowColors(True)
        self.setAnimated(True)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)

        self.connect(self, SIGNAL('expanded(QModelIndex)'),
                     lambda: self.resizeColumnToContents(0))

        self.connect(self, SIGNAL('collapsed(QModelIndex)'),
                     lambda: self.resizeColumnToContents(0))

        self.action_history =\
                self._create_action('View History...',
                                    'View history for selected path(s).',
                                    self.view_history,
                                    Qt.Key_H)

        self.action_stage =\
                self._create_action('Stage Selected',
                                    'Stage selected path(s) for commit.',
                                    self.stage_selected,
                                    Qt.Key_S)

        self.action_unstage =\
                self._create_action('Unstage Selected',
                                    'Remove selected path(s) from '
                                    'the staging area.',
                                    self.unstage_selected,
                                    Qt.Key_U)

        self.action_difftool =\
                self._create_action('View Diff...',
                                    'Launch git-difftool on the current path.',
                                    self.difftool,
                                    Qt.Key_D)

    def update_actions(self):
        """Enable/disable actions."""
        selection = self.selected_paths()
        selected = bool(selection)
        staged = bool(self.selected_staged_paths(selection=selection))
        unstaged = bool(self.selected_unstaged_paths(selection=selection))
        tracked = bool(self.selected_tracked_paths())

        self.action_history.setEnabled(selected)
        self.action_stage.setEnabled(unstaged)
        self.action_unstage.setEnabled(staged)
        self.action_difftool.setEnabled(tracked)

    def contextMenuEvent(self, event):
        """Create a context menu."""
        self.update_actions()
        menu = QtGui.QMenu(self)
        menu.addAction(self.action_stage)
        menu.addAction(self.action_unstage)
        menu.addSeparator()
        menu.addAction(self.action_difftool)
        menu.addAction(self.action_history)
        menu.exec_(self.mapToGlobal(event.pos()))

    def keyPressEvent(self, event):
        """
        Override keyPressEvent to allow LeftArrow to work on non-directories.

        When LeftArrow is pressed on a file entry or an unexpanded directory,
        then move the current index to the parent directory.

        This simplifies navigation using the keyboard.

        """
        # Check whether the item is expanded before calling the base class
        # keyPressEvent otherwise we end up collapsing and changing the
        # current index in one shot, which we don't want to do.
        index = self.currentIndex()
        is_expanded = index.isValid() and self.isExpanded(index)

        # Process the keyPressEvent before changing the current index
        # otherwise the event will affect the new index set here
        # instead of the original index.
        result = QtGui.QTreeView.keyPressEvent(self, event)

        # Process non-root entries with valid parents only.
        if (index.isValid() and event.key() == QtCore.Qt.Key_Left and
                index.parent() and index.parent().isValid()):

            # File entries have rowCount() == 0
            if self.item_from_index(index).rowCount() == 0:
                self.setCurrentIndex(index.parent())

            # Otherwise, only add this behavior for collapsed directories
            elif not is_expanded:
                self.setCurrentIndex(index.parent())

        return result

    def selectionChanged(self, old_selection, new_selection):
        """Override selectionChanged to update available actions."""
        result = QtGui.QTreeView.selectionChanged(self, old_selection, new_selection)
        self.update_actions()
        return result

    def setModel(self, model):
        """Set the concrete QDirModel instance."""
        QtGui.QTreeView.setModel(self, model)
        self.resizeColumnToContents(0)
        app_model = model.app_model
        app_model.add_message_observer(app_model.message_paths_staged,
                                       self._paths_updated)
        app_model.add_message_observer(app_model.message_paths_unstaged,
                                       self._paths_updated)

    def item_from_index(self, model_index):
        """Return the item corresponding to the model index."""
        index = model_index.sibling(model_index.row(), 0)
        return self.model().itemFromIndex(index)

    def selected_paths(self):
        """Return the selected paths."""
        items = map(self.model().itemFromIndex, self.selectedIndexes())
        return [i.path for i in items if i.type() > 0]

    def selected_staged_paths(self, selection=None):
        """Return selected staged paths."""
        if not selection:
            selection = self.selected_paths()
        staged = cola.utils.add_parents(set(self.model().app_model.staged))
        return [p for p in selection if p in staged]

    def selected_modified_paths(self, selection=None):
        """Return selected modified paths."""
        if not selection:
            selection = self.selected_paths()
        model = self.model().app_model
        modified = cola.utils.add_parents(set(model.modified))
        return [p for p in selection if p in modified]

    def selected_unstaged_paths(self, selection=None):
        """Return selected unstaged paths."""
        if not selection:
            selection = self.selected_paths()
        model = self.model().app_model
        modified = cola.utils.add_parents(set(model.modified))
        untracked = cola.utils.add_parents(set(model.untracked))
        unstaged = modified.union(untracked)
        return [p for p in selection if p in unstaged]

    def selected_tracked_paths(self, selection=None):
        """Return selected tracked paths."""
        if not selection:
            selection = self.selected_paths()
        staged = set(self.selected_staged_paths())
        modified = set(self.selected_modified_paths())
        tracked = staged.union(modified)
        return list(tracked)

    def _create_action(self, name, tooltip, slot, shortcut):
        """Create an action with a shortcut, tooltip, and callback slot."""
        action = QtGui.QAction(self.tr(name), self)
        action.setStatusTip(self.tr(tooltip))
        action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        action.setShortcut(shortcut)
        self.addAction(action)
        self.connect(action, SIGNAL('triggered()'), slot)
        return action

    def view_history(self):
        """Signal that we should view history for paths."""
        self.emit(SIGNAL('history(QStringList)'), self.selected_paths())

    def stage_selected(self):
        """Signal that we should stage selected paths."""
        self.emit(SIGNAL('stage(QStringList)'), self.selected_unstaged_paths())

    def unstage_selected(self):
        """Signal that we should stage selected paths."""
        self.emit(SIGNAL('unstage(QStringList)'), self.selected_staged_paths())

    def difftool(self):
        """Signal that we should launch difftool on a path."""
        paths = self.selected_tracked_paths()
        self.emit(SIGNAL('difftool(QStringList)'), paths)

    def _paths_updated(self, model, message, paths=None):
        """Observes paths that are staged and reacts accordingly."""
        for path in paths:
            self.model().entry(path).update()
            while path and '/' in path:
                path = cola.utils.dirname(path)
                self.model().entry(path).update()

    def current_path(self):
        """Return the path for the current item."""
        index = self.currentIndex()
        if not index.isValid():
            return None
        return self.item_from_index(index).path
