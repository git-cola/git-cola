from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import qtcompat


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
        try:
            self.resize(state['width'], state['height'])
        except:
            pass
        try:
            self.move(state['x'], state['y'])
        except:
            pass
        if state.get('maximized', False):
            self.showMaximized()

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


class MainWindowMixin(WidgetMixin):
    def __init__(self, QtClass):
        WidgetMixin.__init__(self, QtClass)
        # Dockwidget options
        qtcompat.set_common_dock_options(self)


class TreeMixin(object):

    def __init__(self, QtClass):
        self.QtClass = QtClass
        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        self.setAllColumnsShowFocus(True)
        self.setAnimated(True)

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

        # Try to select the first item if the model index is invalid
        if not index.isValid():
            index = self.model().index(0, 0, QtCore.QModelIndex())
            if index.isValid():
                self.setCurrentIndex(index)

        # Automatically select the first entry when expanding a directory
        elif (key == Qt.Key_Right and was_collapsed and
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

        return result


def bind_mixin(Mixin, QtClass):
    """Construct a class which composes the Mixin over the Qt class"""

    class BoundMixin(Mixin, QtClass):
        """A concrete class tied to a specific Qt class"""

        def __init__(self, parent=None):
            QtClass.__init__(self, parent)
            Mixin.__init__(self, QtClass)
            self.Mixin = BoundMixin

    return BoundMixin


Widget = bind_mixin(WidgetMixin, QtGui.QWidget)
Dialog = bind_mixin(WidgetMixin, QtGui.QDialog)
MainWindow = bind_mixin(MainWindowMixin, QtGui.QMainWindow)

TreeView = bind_mixin(TreeMixin, QtGui.QTreeView)
TreeWidget = bind_mixin(TreeMixin, QtGui.QTreeWidget)
