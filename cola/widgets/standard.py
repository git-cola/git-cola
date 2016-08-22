from __future__ import division, absolute_import, unicode_literals

import time

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QDockWidget

from .. import core
from .. import gitcfg
from .. import qtcompat
from .. import qtutils
from ..settings import Settings
from . import defs


class WidgetMixin(object):
    """Mix-in for common utilities and serialization of widget state"""

    def center(self):
        parent = self.parent()
        if parent is None:
            return
        left = parent.x()
        width = parent.width()
        center_x = left + width//2
        x = center_x - self.width()//2
        y = parent.y()

        self.move(x, y)

    def resize_to_desktop(self):
        desktop = QtWidgets.QApplication.instance().desktop()
        width = desktop.width()
        height = desktop.height()
        self.resize(width, height)

    def name(self):
        """Returns the name of the view class"""
        return self.__class__.__name__.lower()

    def save_state(self, settings=None):
        if settings is None:
            settings = Settings()
            settings.load()
        if gitcfg.current().get('cola.savewindowsettings', True):
            settings.save_gui_state(self)

    def restore_state(self, settings=None):
        if settings is None:
            settings = Settings()
            settings.load()
        state = settings.get_gui_state(self)
        return bool(state) and self.apply_state(state)

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
        self._apply_state_applied = result
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

    def save_settings(self):
        settings = Settings()
        settings.load()
        settings.add_recent(core.getcwd())
        return self.save_state(settings=settings)

    def closeEvent(self, event):
        self.save_settings()
        self.Base.closeEvent(self, event)

    def init_state(self, settings, callback, *args, **kwargs):
        """Restore saved settings or set the initial location"""
        if not self.restore_state(settings=settings):
            callback(*args, **kwargs)
            self.center()


class MainWindowMixin(WidgetMixin):

    def __init__(self):
        WidgetMixin.__init__(self)
        # Dockwidget options
        self.dockwidgets = []
        self.lock_layout = False
        self.widget_version = 0
        qtcompat.set_common_dock_options(self)

    def export_state(self):
        """Exports data for save/restore"""
        state = WidgetMixin.export_state(self)
        windowstate = self.saveState(self.widget_version)
        state['lock_layout'] = self.lock_layout
        state['windowstate'] = windowstate.toBase64().data().decode('ascii')
        return state

    def apply_state(self, state):
        result = WidgetMixin.apply_state(self, state)
        windowstate = state.get('windowstate', None)
        if windowstate is None:
            result = False
        else:
            from_base64 = QtCore.QByteArray.fromBase64
            result = self.restoreState(
                    from_base64(core.encode(windowstate)),
                    self.widget_version) and result
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

    def __init__(self, widget, Base):
        self.widget = widget
        self.Base = Base

        widget.setAlternatingRowColors(True)
        widget.setUniformRowHeights(True)
        widget.setAllColumnsShowFocus(True)
        widget.setAnimated(True)
        widget.setRootIsDecorated(False)

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
        widget = self.widget
        index = widget.currentIndex()
        was_expanded = widget.isExpanded(index)
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
        if key == Qt.Key_Up:
            idxs = widget.selectedIndexes()
            rows = [idx.row() for idx in idxs]
            if len(rows) == 1 and rows[0] == 0:
                # The cursor is at the beginning of the line.
                # If we have selection then simply reset the cursor.
                # Otherwise, emit a signal so that the parent can
                # change focus.
                widget.up.emit()

        elif key == Qt.Key_Space:
            widget.space.emit()

        result = self.Base.keyPressEvent(widget, event)

        # Let others hook in here before we change the indexes
        widget.index_about_to_change.emit()

        # Automatically select the first entry when expanding a directory
        if (key == Qt.Key_Right and was_collapsed and
                widget.isExpanded(index)):
            index = widget.moveCursor(widget.MoveDown, event.modifiers())
            widget.setCurrentIndex(index)

        # Process non-root entries with valid parents only.
        elif key == Qt.Key_Left and index.parent().isValid():

            # File entries have rowCount() == 0
            if widget.model().itemFromIndex(index).rowCount() == 0:
                widget.setCurrentIndex(index.parent())

            # Otherwise, do this for collapsed directories only
            elif was_collapsed:
                widget.setCurrentIndex(index.parent())

        # If it's a movement key ensure we have a selection
        elif key in (Qt.Key_Left, Qt.Key_Up, Qt.Key_Right, Qt.Key_Down):
            # Try to select the first item if the model index is invalid
            item = self.selected_item()
            if item is None or not index.isValid():
                index = widget.model().index(0, 0, QtCore.QModelIndex())
                if index.isValid():
                    widget.setCurrentIndex(index)

        return result

    def items(self):
        root = self.widget.invisibleRootItem()
        child = root.child
        count = root.childCount()
        return [child(i) for i in range(count)]

    def selected_items(self):
        """Return all selected items"""
        widget = self.widget
        if hasattr(widget, 'selectedItems'):
            return widget.selectedItems()
        else:
            item_from_index = widget.model().itemFromIndex
            return [item_from_index(i) for i in widget.selectedIndexes()]

    def selected_item(self):
        """Return the first selected item"""
        selected_items = self.selected_items()
        if not selected_items:
            return None
        return selected_items[0]

    def current_item(self):
        item = None
        widget = self.widget
        if hasattr(widget, 'currentItem'):
            item = widget.currentItem()
        else:
            index = widget.currentIndex()
            if index.isValid():
                item = widget.model().itemFromIndex(index)
        return item


class DraggableTreeMixin(TreeMixin):
    """A tree widget with internal drag+drop reordering of rows

    Expects that the widget provides an `items_moved` signal.

    """
    def __init__(self, widget, Base):
        super(DraggableTreeMixin, self).__init__(widget, Base)

        self._inner_drag = False
        widget.setAcceptDrops(True)
        widget.setSelectionMode(widget.SingleSelection)
        widget.setDragEnabled(True)
        widget.setDropIndicatorShown(True)
        widget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        widget.setSortingEnabled(False)

    def dragEnterEvent(self, event):
        """Accept internal drags only"""
        widget = self.widget
        self.Base.dragEnterEvent(widget, event)
        self._inner_drag = event.source() == widget
        if self._inner_drag:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        widget = self.widget
        self.Base.dragLeaveEvent(widget, event)
        if self._inner_drag:
            event.accept()
        else:
            event.ignore()
        self._inner_drag = False

    def dropEvent(self, event):
        """Re-select selected items after an internal move"""
        if not self._inner_drag:
            event.ignore()
            return
        widget = self.widget
        clicked_items = self.selected_items()
        event.setDropAction(Qt.MoveAction)
        self.Base.dropEvent(widget, event)

        if clicked_items:
            widget.clearSelection()
            for item in clicked_items:
                item.setSelected(True)
            widget.items_moved.emit(clicked_items)
        self._inner_drag = False
        event.accept()  # must be called after dropEvent()

    def mousePressEvent(self, event):
        """Clear the selection when a mouse click hits no item"""
        widget = self.widget
        clicked_item = widget.itemAt(event.pos())
        if clicked_item is None:
            widget.clearSelection()
        return self.Base.mousePressEvent(widget, event)


class Widget(WidgetMixin, QtWidgets.QWidget):
    Base = QtWidgets.QWidget

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent)
        WidgetMixin.__init__(self)


class Dialog(WidgetMixin, QtWidgets.QDialog):
    Base = QtWidgets.QDialog

    def __init__(self, parent=None, save_settings=False):
        QtWidgets.QDialog.__init__(self, parent)
        WidgetMixin.__init__(self)
        self._save_settings = save_settings

    def reject(self):
        if self._save_settings:
            self.save_settings()
        return self.Base.reject(self)


class MainWindow(MainWindowMixin, QtWidgets.QMainWindow):
    Base = QtWidgets.QMainWindow

    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        MainWindowMixin.__init__(self)

        self.setStyleSheet("""
            QMainWindow::separator {
                width: %(separator)spx;
                height: %(separator)spx;
            }
            QMainWindow::separator:hover {
                background: white;
            }
            """ % dict(separator=defs.separator))


class TreeView(QtWidgets.QTreeView):
    Mixin = TreeMixin

    up = Signal()
    space = Signal()
    index_about_to_change = Signal()

    def __init__(self, parent=None):
        QtWidgets.QTreeView.__init__(self, parent)
        self._mixin = self.Mixin(self, QtWidgets.QTreeView)

    def keyPressEvent(self, event):
        return self._mixin.keyPressEvent(event)

    def current_item(self):
        return self._mixin.current_item()

    def selected_item(self):
        return self._mixin.selected_item()

    def selected_items(self):
        return self._mixin.selected_items()

    def items(self):
        return self._mixin.items()


class TreeWidget(QtWidgets.QTreeWidget):
    Mixin = TreeMixin

    up = Signal()
    space = Signal()
    index_about_to_change = Signal()

    def __init__(self, parent=None):
        super(TreeWidget, self).__init__(parent)
        self._mixin = self.Mixin(self, QtWidgets.QTreeWidget)

    def keyPressEvent(self, event):
        return self._mixin.keyPressEvent(event)

    def current_item(self):
        return self._mixin.current_item()

    def selected_item(self):
        return self._mixin.selected_item()

    def selected_items(self):
        return self._mixin.selected_items()

    def items(self):
        return self._mixin.items()


class DraggableTreeWidget(TreeWidget):
    Mixin = DraggableTreeMixin
    items_moved = Signal(object)

    def mousePressEvent(self, event):
        return self._mixin.mousePressEvent(event)

    def dropEvent(self, event):
        return self._mixin.dropEvent(event)

    def dragLeaveEvent(self, event):
        return self._mixin.dragLeaveEvent(event)

    def dragEnterEvent(self, event):
        return self._mixin.dragEnterEvent(event)


class ProgressDialog(QtWidgets.QProgressDialog):
    """Custom progress dialog

    This dialog ignores the ESC key so that it is not
    prematurely closed.

    An thread is spawned to animate the progress label text.

    """
    def __init__(self, title, label, parent):
        QtWidgets.QProgressDialog.__init__(self, parent)
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)
        self.reset()
        self.setRange(0, 0)
        self.setMinimumDuration(0)
        self.setCancelButton(None)
        self.setFont(qtutils.diff_font())
        self.thread = ProgressAnimationThread(label, self)
        self.thread.updated.connect(self.refresh, type=Qt.QueuedConnection)

        self.set_details(title, label)

    def set_details(self, title, label):
        self.setWindowTitle(title)
        self.setLabelText(label + '     ')
        self.thread.set_text(label)

    def refresh(self, txt):
        self.setLabelText(txt)

    def keyPressEvent(self, event):
        if event.key() != Qt.Key_Escape:
            super(ProgressDialog, self).keyPressEvent(event)

    def show(self):
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        super(ProgressDialog, self).show()
        self.thread.start()

    def hide(self):
        QtWidgets.QApplication.restoreOverrideCursor()
        self.thread.stop()
        self.thread.wait()
        super(ProgressDialog, self).hide()


class ProgressAnimationThread(QtCore.QThread):
    """Emits a pseudo-animated text stream for progress bars

    """
    updated = Signal(object)

    def __init__(self, txt, parent, timeout=0.1):
        QtCore.QThread.__init__(self, parent)
        self.running = False
        self.txt = txt
        self.timeout = timeout
        self.symbols = [
            '.  ..',
            '..  .',
            '...  ',
            ' ... ',
            '  ...',
        ]
        self.idx = -1

    def set_text(self, txt):
        self.txt = txt

    def cycle(self):
        self.idx = (self.idx + 1) % len(self.symbols)
        return self.txt + self.symbols[self.idx]

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            self.updated.emit(self.cycle())
            time.sleep(self.timeout)


class SpinBox(QtWidgets.QSpinBox):
    def __init__(self, parent=None):
        QtWidgets.QSpinBox.__init__(self, parent)
        self.setMinimum(1)
        self.setMaximum(99999)
        self.setPrefix('')
        self.setSuffix('')
