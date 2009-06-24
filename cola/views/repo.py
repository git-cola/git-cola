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
                self._create_action('Stage Selected...',
                                    'Stage selected path(s) for commit.',
                                    self.stage_selected,
                                    Qt.Key_S)

    def update_actions(self):
        """Enable/disable actions."""
        selection = self.selected_paths()
        unstaged = self.selected_unstaged_paths(selection=selection)

        self.action_history.setEnabled(bool(selection))
        self.action_stage.setEnabled(bool(unstaged))

    def contextMenuEvent(self, event):
        """Create a context menu."""
        self.update_actions()
        menu = QtGui.QMenu(self)
        menu.addAction(self.action_stage)
        menu.addSeparator()
        menu.addAction(self.action_history)
        menu.exec_(self.mapToGlobal(event.pos()))

    def setModel(self, model):
        """Set the concrete QDirModel instance."""
        QtGui.QTreeView.setModel(self, model)
        self.resizeColumnToContents(0)
        app_model = model.app_model
        app_model.add_message_observer(app_model.message_paths_staged,
                                       self._paths_updated)

    def item_from_index(self, model_index):
        """Return the item corresponding to the model index."""
        index = model_index.sibling(model_index.row(), 0)
        return self.model().itemFromIndex(index)

    def selected_paths(self):
        """Return the selected paths."""
        items = map(self.model().itemFromIndex, self.selectedIndexes())
        return [i.path for i in items if i.type() > 0]

    def selected_unstaged_paths(self, selection=None):
        """Return selected unstaged paths."""
        if not selection:
            selection = self.selected_paths()
        model = self.model().app_model
        modified = cola.utils.add_parents(set(model.modified))
        untracked = cola.utils.add_parents(set(model.untracked))
        unstaged = modified.union(untracked)
        return [p for p in selection if p in unstaged]

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


    def _paths_updated(self, model, message, paths=None):
        """Observes paths that are staged and reacts accordingly."""
        for path in paths:
            self.model().entry(path).update()
            while path and '/' in path:
                path = cola.utils.dirname(path)
                self.model().entry(path).update()
