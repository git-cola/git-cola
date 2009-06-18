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
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.connect(self, SIGNAL("expanded(QModelIndex)"),
                     lambda: self.resizeColumnToContents(0))

        self.action_history = QtGui.QAction('View History...', self)
        self.action_history.setShortcut(Qt.Key_H)
        self.action_history.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self.action_history.setStatusTip('Launch a history view for this path.')
        self.addAction(self.action_history)
        self.connect(self.action_history, SIGNAL('triggered()'),
                     self.view_history)

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

    def selected_paths(self):
        """Return the selected paths."""
        items = map(self.model().itemFromIndex, self.selectedIndexes())
        return [i.path for i in items if i.type() > 0]

    def view_history(self):
        """Signal that we should view history for paths."""
        self.emit(SIGNAL('history(QStringList)'), self.selected_paths())
