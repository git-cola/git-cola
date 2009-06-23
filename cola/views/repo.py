from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

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

        self.action_history = self._create_action('View History...',
                                                  'View history limited to selected path(s).',
                                                  self.view_history,
                                                  Qt.Key_H)

        self.action_stage = self._create_action('Stage Selected...',
                                                'Stage selected path(s) for commit.',
                                                self.stage_selected,
                                                Qt.Key_S)

    def update_actions(self):
        """Enable/disable actions."""
        selection = self.selected_paths()
        self.action_history.setEnabled(bool(selection))

    def contextMenuEvent(self, event):
        """Create a context menu."""
        self.update_actions()
        menu = QtGui.QMenu(self)
        menu.addAction(self.action_history)
        menu.exec_(self.mapToGlobal(event.pos()))

    def setModel(self, model):
        """Set the concrete QDirModel instance."""
        QtGui.QTreeView.setModel(self, model)
        self.resizeColumnToContents(0)

    def item_from_index(self, model_index):
        """Return the item corresponding to the model index."""
        index = model_index.sibling(model_index.row(), 0)
        return self.model().itemFromIndex(index)

    def selected_paths(self):
        """Return the selected paths."""
        items = map(self.model().itemFromIndex, self.selectedIndexes())
        return [i.path for i in items if i.type() > 0]

    def view_history(self):
        """Signal that we should view history for paths."""
        self.emit(SIGNAL('history(QStringList)'), self.selected_paths())

    def stage_selected(self):
        """Signal that we should stage selected paths."""
        self.emit(SIGNAL('stage(QStringList)'), self.selected_paths())

    def _create_action(self, name, tooltip, slot, shortcut):
        """Create an action with a shortcut, tooltip, and callback slot."""
        action = QtGui.QAction(self.tr(name), self)
        action.setStatusTip(self.tr(tooltip))
        action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        action.setShortcut(shortcut)
        self.addAction(action)
        self.connect(action, SIGNAL('triggered()'), slot)
        return action
