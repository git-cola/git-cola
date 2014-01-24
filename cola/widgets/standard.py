from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QDockWidget

from cola import core
from cola import qtcompat
from cola import qtutils
from cola import settings


class WidgetMixin(object):

    # not exported
    def __init__(self, QtClass):
        self.QtClass = QtClass

    # Mix-in for standard view operations
    def show(self):
        """Automatically centers dialogs"""
        if self.parent():
            left = self.parent().x()
            width = self.parent().width()
            center_x = left + width/2

            x = center_x - self.width()/2
            y = self.parent().y()

            self.move(x, y)
        # Call the base Qt show()
        return self.QtClass.show(self)

    def name(self):
        """Returns the name of the view class"""
        return self.__class__.__name__.lower()

    def apply_state(self, state):
        """Imports data for view save/restore"""
        result = True
        try:
            self.resize(state['width'], state['height'])
        except:
            result = False
        try:
            self.move(state['x'], state['y'])
        except:
            result = False
        try:
            if state['maximized']:
                self.showMaximized()
        except:
            result = False
        return result

    def export_state(self):
        """Exports data for view save/restore"""
        state = self.windowState()
        maximized = bool(state & Qt.WindowMaximized)
        return {
            'x': self.x(),
            'y': self.y(),
            'width': self.width(),
            'height': self.height(),
            'maximized': maximized,
        }

    def closeEvent(self, event):
        s = settings.Settings()
        s.add_recent(core.getcwd())
        qtutils.save_state(self, handler=s)
        self.QtClass.closeEvent(self, event)


class MainWindowMixin(WidgetMixin):

    def __init__(self, QtClass):
        WidgetMixin.__init__(self, QtClass)
        # Dockwidget options
        self.dockwidgets = []
        self.lock_layout = False
        qtcompat.set_common_dock_options(self)
        self.widget_version = 0

    def export_state(self):
        """Exports data for save/restore"""
        state = WidgetMixin.export_state(self)
        state['lock_layout'] = self.lock_layout
        return qtutils.export_window_state(self, state, self.widget_version)

    def apply_state(self, state):
        WidgetMixin.apply_state(self, state)
        result = qtutils.apply_window_state(self, state, self.widget_version)
        self.lock_layout = state.get('lock_layout', self.lock_layout)
        self.update_dockwidget_lock_state()
        self.update_dockwidget_tooltips()
        return result

    def set_lock_layout(self, lock_layout):
        self.lock_layout = lock_layout
        self.update_dockwidget_lock_state()

    def update_dockwidget_lock_state(self):
        if self.lock_layout:
            features = (QDockWidget.DockWidgetClosable |
                        QDockWidget.DockWidgetFloatable)
        else:
            features = (QDockWidget.DockWidgetClosable |
                        QDockWidget.DockWidgetFloatable |
                        QDockWidget.DockWidgetMovable)
        for widget in self.dockwidgets:
            widget.titleBarWidget().update_tooltips()
            widget.setFeatures(features)

    def update_dockwidget_tooltips(self):
        for widget in self.dockwidgets:
            widget.titleBarWidget().update_tooltips()


class TreeMixin(object):

    def __init__(self, QtClass):
        self.QtClass = QtClass
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setAllColumnsShowFocus(True)
        self.setAnimated(True)
        self.setRootIsDecorated(False)

    def keyPressEvent(self, event):
        """
        Make LeftArrow to work on non-directories.

        When LeftArrow is pressed on a file entry or an unexpanded
        directory, then move the current index to the parent directory.

        This simplifies navigation using the keyboard.
        For power-users, we support Vim keybindings ;-P

        """
        # Check whether the item is expanded before calling the base class
        # keyPressEvent otherwise we end up collapsing and changing the
        # current index in one shot, which we don't want to do.
        index = self.currentIndex()
        was_expanded = self.isExpanded(index)
        was_collapsed = not was_expanded

        # Vim keybindings...
        # Rewrite the event before marshalling to QTreeView.event()
        key = event.key()

        # Remap 'H' to 'Left'
        if key == Qt.Key_H:
            event = QtGui.QKeyEvent(event.type(),
                                    Qt.Key_Left,
                                    event.modifiers())
        # Remap 'J' to 'Down'
        elif key == Qt.Key_J:
            event = QtGui.QKeyEvent(event.type(),
                                    Qt.Key_Down,
                                    event.modifiers())
        # Remap 'K' to 'Up'
        elif key == Qt.Key_K:
            event = QtGui.QKeyEvent(event.type(),
                                    Qt.Key_Up,
                                    event.modifiers())
        # Remap 'L' to 'Right'
        elif key == Qt.Key_L:
            event = QtGui.QKeyEvent(event.type(),
                                    Qt.Key_Right,
                                    event.modifiers())

        # Re-read the event key to take the remappings into account
        key = event.key()
        result = self.QtClass.keyPressEvent(self, event)

        # Let others hook in here before we change the indexes
        self.emit(SIGNAL('indexAboutToChange()'))

        # Automatically select the first entry when expanding a directory
        if (key == Qt.Key_Right and was_collapsed and
                self.isExpanded(index)):
            index = self.moveCursor(self.MoveDown, event.modifiers())
            self.setCurrentIndex(index)

        # Process non-root entries with valid parents only.
        elif key == Qt.Key_Left and index.parent().isValid():

            # File entries have rowCount() == 0
            if self.model().itemFromIndex(index).rowCount() == 0:
                self.setCurrentIndex(index.parent())

            # Otherwise, do this for collapsed directories only
            elif was_collapsed:
                self.setCurrentIndex(index.parent())

        # If it's a movement key ensure we have a selection
        elif key in (Qt.Key_Left, Qt.Key_Up, Qt.Key_Right, Qt.Key_Down):
            # Try to select the first item if the model index is invalid
            item = self.selected_item()
            if item is None or not index.isValid():
                index = self.model().index(0, 0, QtCore.QModelIndex())
                if index.isValid():
                    self.setCurrentIndex(index)

        return result

    def items(self):
        root = self.invisibleRootItem()
        child = root.child
        count = root.childCount()
        return [child(i) for i in range(count)]

    def selected_items(self):
        """Return all selected items"""
        if hasattr(self, 'selectedItems'):
            return self.selectedItems()
        else:
            item_from_index = self.model().itemFromIndex
            return [item_from_index(i) for i in self.selectedIndexes()]

    def selected_item(self):
        """Return the first selected item"""
        selected_items = self.selected_items()
        if not selected_items:
            return None
        return selected_items[0]


class DraggableTreeMixin(TreeMixin):
    """A tree widget with internal drag+drop reordering of rows"""

    def __init__(self, QtClass):
        super(DraggableTreeMixin, self).__init__(QtClass)
        self._inner_drag = False
        self.setAcceptDrops(True)
        self.setSelectionMode(self.SingleSelection)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        self.setSortingEnabled(False)

    def dragEnterEvent(self, event):
        """Accept internal drags only"""
        self.QtClass.dragEnterEvent(self, event)
        self._inner_drag = event.source() == self
        if self._inner_drag:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.QtClass.dragLeaveEvent(self, event)
        if self._inner_drag:
            event.accept()
        else:
            event.ignore()
        self._inner_drag = False

    def dropEvent(self, event):
        """Add dropped patches"""
        if not self._inner_drag:
            event.ignore()
            return

        clicked_items = self.selected_items()

        event.setDropAction(Qt.MoveAction)
        self.QtClass.dropEvent(self, event)

        if clicked_items:
            self.clearSelection()
            for item in clicked_items:
                self.setItemSelected(item, True)

        self._inner_drag = False
        event.accept() # must be called after dropEvent()

    def mousePressEvent(self, event):
        clicked_item = self.itemAt(event.pos())
        if clicked_item is None:
            self.clearSelection()

        return self.QtClass.mousePressEvent(self, event)


class Widget(WidgetMixin, QtGui.QWidget):

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        WidgetMixin.__init__(self, QtGui.QWidget)


class Dialog(WidgetMixin, QtGui.QDialog):

    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)
        WidgetMixin.__init__(self, QtGui.QDialog)


class MainWindow(MainWindowMixin, QtGui.QMainWindow):

    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        MainWindowMixin.__init__(self, QtGui.QMainWindow)


class TreeView(TreeMixin, QtGui.QTreeView):

    def __init__(self, parent=None):
        QtGui.QTreeView.__init__(self, parent)
        TreeMixin.__init__(self, QtGui.QTreeView)


class TreeWidget(TreeMixin, QtGui.QTreeWidget):

    def __init__(self, parent=None):
        QtGui.QTreeWidget.__init__(self, parent)
        TreeMixin.__init__(self, QtGui.QTreeWidget)


class DraggableTreeWidget(DraggableTreeMixin, QtGui.QTreeWidget):
    
    def __init__(self, parent=None):
        QtGui.QTreeWidget.__init__(self, parent)
        DraggableTreeMixin.__init__(self, QtGui.QTreeWidget)
