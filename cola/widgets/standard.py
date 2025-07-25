from functools import partial
import os
import time

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QDockWidget

from ..i18n import N_
from ..interaction import Interaction
from ..settings import Settings, mklist
from ..models import prefs
from .. import core
from .. import hotkeys
from .. import icons
from .. import qtcompat
from .. import qtutils
from .. import utils
from . import defs


class WidgetMixin:
    """Mix-in for common utilities and serialization of widget state"""

    closed = Signal(QtWidgets.QWidget)

    def __init__(self):
        self._unmaximized_rect = {}

    def center(self):
        parent = self.parent()
        if parent is None:
            return
        left = parent.x()
        width = parent.width()
        center_x = left + width // 2
        x = center_x - self.width() // 2
        y = parent.y()

        self.move(x, y)

    def resize_to_desktop(self):
        width, height = qtutils.desktop_size()
        if utils.is_darwin():
            self.resize(width, height)
        else:
            shown = self.isVisible()
            # earlier show() fools Windows focus stealing prevention. The main
            # window is blocked for the duration of "git rebase" and we don't
            # want to present a blocked window with git-cola-sequence-editor
            # hidden somewhere.
            self.show()
            self.setWindowState(Qt.WindowMaximized)
            if not shown:
                self.hide()

    def name(self):
        """Returns the name of the view class"""
        return self.__class__.__name__.lower()

    def save_state(self, settings=None):
        """Save tool settings to the ~/.config/git-cola/settings file"""
        save = True
        sync = True
        context = getattr(self, 'context', None)
        if context:
            cfg = context.cfg
            save = cfg.get('cola.savewindowsettings', default=True)
            sync = cfg.get('cola.sync', default=True)
        if save:
            if settings is None:
                settings = Settings.read()
            settings.save_gui_state(self, sync=sync)

    def restore_state(self, settings=None):
        """Read and apply saved tool settings"""
        if settings is None:
            settings = Settings.read()
        state = settings.get_gui_state(self)
        if state:
            result = self.apply_state(state)
        else:
            result = False
        return result

    def apply_state(self, state):
        """Import data for view save/restore"""
        width = utils.asint(state.get('width'))
        height = utils.asint(state.get('height'))
        x = utils.asint(state.get('x'))
        y = utils.asint(state.get('y'))

        geometry = state.get('geometry', '')
        if geometry:
            from_base64 = QtCore.QByteArray.fromBase64
            result = self.restoreGeometry(from_base64(core.encode(geometry)))
        elif width and height:
            # Users migrating from older versions won't have 'geometry'.
            # They'll be upgraded to the new format on shutdown.
            self.resize(width, height)
            self.move(x, y)
            result = True
        else:
            result = False
        return result

    def export_state(self):
        """Exports data for view save/restore"""
        state = {}
        geometry = self.saveGeometry()
        state['geometry'] = geometry.toBase64().data().decode('ascii')
        # Until 2020: co-exist with older versions
        state['width'] = self.width()
        state['height'] = self.height()
        state['x'] = self.x()
        state['y'] = self.y()
        return state

    def save_settings(self, settings=None):
        """Save tool state using the specified settings backend"""
        return self.save_state(settings=settings)

    def closeEvent(self, event):
        """Save settings when the top-level widget is closed"""
        self.save_settings()
        self.closed.emit(self)
        self.Base.closeEvent(self, event)

    def init_size(self, parent=None, settings=None, width=0, height=0):
        """Set a tool's initial size"""
        if not width:
            width = defs.dialog_w
        if not height:
            height = defs.dialog_h
        self.init_state(
            settings,
            self.resize_to_parent,
            parent,
            width,
            height,
            use_parent_height=True,
        )

    def init_state(self, settings, callback, *args, **kwargs):
        """Restore saved settings or set the initial location"""
        if not self.restore_state(settings=settings):
            callback(*args, **kwargs)
            self.center()

    def resize_to_parent(self, parent, w, h, use_parent_height=True):
        """Set the initial size of the widget"""
        width, height = qtutils.default_size(
            parent, w, h, use_parent_height=use_parent_height
        )
        self.resize(width, height)


class MainWindowMixin(WidgetMixin):
    def __init__(self):
        WidgetMixin.__init__(self)
        # Dockwidget options
        self.dockwidgets = []
        self.lock_layout = False
        self.widget_version = 0
        qtcompat.set_common_dock_options(self)
        self.default_state = None

    def init_state(self, settings, callback, *args, **kwargs):
        """Save the initial state before calling the parent initializer"""
        self.default_state = self.saveState(self.widget_version)
        super().init_state(settings, callback, *args, **kwargs)

    def layout_state(self):
        """Return the Qt layout state"""
        return self.saveState(self.widget_version)

    def apply_layout(self, value):
        """Apply binary Qt layout state"""
        self.restoreState(value, self.widget_version)

    def export_state(self):
        """Exports data for save/restore"""
        state = WidgetMixin.export_state(self)
        windowstate = self.saveState(self.widget_version)
        state['lock_layout'] = self.lock_layout
        state['windowstate'] = windowstate.toBase64().data().decode('ascii')
        return state

    def save_settings(self, settings=None):
        if settings is None:
            context = getattr(self, 'context', None)
            if context is None:
                settings = Settings.read()
            else:
                settings = context.settings
                settings.load()
            try:
                cwd = core.getcwd()
            except FileNotFoundError:
                pass
            else:
                settings.add_recent(cwd, prefs.maxrecent(context))
        return WidgetMixin.save_settings(self, settings=settings)

    def apply_state(self, state):
        result = WidgetMixin.apply_state(self, state)
        windowstate = state.get('windowstate', '')
        if windowstate:
            from_base64 = QtCore.QByteArray.fromBase64
            result = (
                self.restoreState(
                    from_base64(core.encode(windowstate)), self.widget_version
                )
                and result
            )
        else:
            result = False

        self.lock_layout = state.get('lock_layout', self.lock_layout)
        self.update_dockwidget_lock_state()
        self.update_dockwidget_floating_state()

        return result

    def reset_layout(self):
        self.restoreState(self.default_state, self.widget_version)

    def set_lock_layout(self, lock_layout):
        self.lock_layout = lock_layout
        self.update_dockwidget_lock_state()

    def update_dockwidget_lock_state(self):
        if self.lock_layout:
            features = QDockWidget.DockWidgetClosable
        else:
            features = (
                QDockWidget.DockWidgetClosable
                | QDockWidget.DockWidgetFloatable
                | QDockWidget.DockWidgetMovable
            )
        for widget in self.dockwidgets:
            widget.setFeatures(features)
            widget.titleBarWidget().update_floating()

    def update_dockwidget_floating_state(self):
        """Update the floating state for all dock widgets"""
        for widget in self.dockwidgets:
            widget.titleBarWidget().update_floating()


class ListWidget(QtWidgets.QListWidget):
    """QListWidget with vim j/k navigation hotkeys"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.up_action = qtutils.add_action(
            self,
            N_('Move Up'),
            self.move_up,
            hotkeys.MOVE_UP,
            hotkeys.MOVE_UP_SECONDARY,
        )

        self.down_action = qtutils.add_action(
            self,
            N_('Move Down'),
            self.move_down,
            hotkeys.MOVE_DOWN,
            hotkeys.MOVE_DOWN_SECONDARY,
        )

    def selected_item(self):
        return self.currentItem()

    def selected_items(self):
        return self.selectedItems()

    def move_up(self):
        self.move(-1)

    def move_down(self):
        self.move(1)

    def move(self, direction):
        item = self.selected_item()
        if item:
            row = (self.row(item) + direction) % self.count()
        elif self.count() > 0:
            row = (self.count() + direction) % self.count()
        else:
            return
        new_item = self.item(row)
        if new_item:
            self.setCurrentItem(new_item)


class TreeMixin:
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
        event = _create_vim_navigation_key_event(event)

        # Read the updated event key to take the mappings into account
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
        if key == Qt.Key_Right and was_collapsed and widget.isExpanded(index):
            index = widget.moveCursor(widget.MoveDown, event.modifiers())
            widget.setCurrentIndex(index)

        # Process non-root entries with valid parents only.
        elif key == Qt.Key_Left and index.parent().isValid():
            # File entries have rowCount() == 0
            model = widget.model()
            if hasattr(model, 'itemFromIndex'):
                item = model.itemFromIndex(index)
                if hasattr(item, 'rowCount') and item.rowCount() == 0:
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

    def item_from_index(self, item):
        """Return a QModelIndex from the provided item"""
        if hasattr(self, 'itemFromIndex'):
            index = self.itemFromIndex(item)
        else:
            index = self.model().itemFromIndex()
        return index

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
        if hasattr(widget, 'itemFromIndex'):
            item_from_index = widget.itemFromIndex
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

    def column_widths(self):
        """Return the tree's column widths"""
        widget = self.widget
        count = widget.header().count()
        return [widget.columnWidth(i) for i in range(count)]

    def set_column_widths(self, widths):
        """Set the tree's column widths"""
        if widths:
            widget = self.widget
            count = widget.header().count()
            if len(widths) > count:
                widths = widths[:count]
            for idx, value in enumerate(widths):
                widget.setColumnWidth(idx, value)


def _create_vim_navigation_key_event(event):
    """Support minimal Vim-like keybindings by rewriting the QKeyEvents"""
    key = event.key()
    # Remap 'H' to 'Left'
    if key == Qt.Key_H:
        event = QtGui.QKeyEvent(event.type(), Qt.Key_Left, event.modifiers())
    # Remap 'J' to 'Down'
    elif key == Qt.Key_J:
        event = QtGui.QKeyEvent(event.type(), Qt.Key_Down, event.modifiers())
    # Remap 'K' to 'Up'
    elif key == Qt.Key_K:
        event = QtGui.QKeyEvent(event.type(), Qt.Key_Up, event.modifiers())
    # Remap 'L' to 'Right'
    elif key == Qt.Key_L:
        event = QtGui.QKeyEvent(event.type(), Qt.Key_Right, event.modifiers())
    return event


class DraggableTreeMixin(TreeMixin):
    """A tree widget with internal drag+drop reordering of rows

    Expects that the widget provides an `items_moved` signal.

    """

    def __init__(self, widget, Base):
        super().__init__(widget, Base)

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

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        WidgetMixin.__init__(self)
        # Disable the Help button hint on Windows
        if hasattr(Qt, 'WindowContextHelpButtonHint'):
            help_hint = Qt.WindowContextHelpButtonHint
            flags = self.windowFlags() & ~help_hint
            self.setWindowFlags(flags)

    def accept(self):
        self.save_settings()
        self.dispose()
        return self.Base.accept(self)

    def reject(self):
        self.save_settings()
        self.dispose()
        return self.Base.reject(self)

    def dispose(self):
        """Extension method for model de-registration in sub-classes"""
        return

    def close(self):
        """save_settings() is handled by accept() and reject()"""
        self.dispose()
        self.Base.close(self)

    def closeEvent(self, event):
        """save_settings() is handled by accept() and reject()"""
        self.dispose()
        self.Base.closeEvent(self, event)


class MainWindow(MainWindowMixin, QtWidgets.QMainWindow):
    Base = QtWidgets.QMainWindow

    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        MainWindowMixin.__init__(self)


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

    def column_widths(self):
        return self._mixin.column_widths()

    def set_column_widths(self, widths):
        return self._mixin.set_column_widths(widths)


class TreeWidget(QtWidgets.QTreeWidget):
    Mixin = TreeMixin

    up = Signal()
    space = Signal()
    index_about_to_change = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
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

    def column_widths(self):
        return self._mixin.column_widths()

    def set_column_widths(self, widths):
        return self._mixin.set_column_widths(widths)


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

    A thread is spawned to animate the progress label text.

    """

    def __init__(self, title, label, parent):
        QtWidgets.QProgressDialog.__init__(self, parent)
        self._parent = parent
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.animation_thread = ProgressAnimationThread(label, self)
        self.animation_thread.updated.connect(self.set_text, type=Qt.QueuedConnection)

        self.reset()
        self.setRange(0, 0)
        self.setMinimumDuration(0)
        self.setCancelButton(None)
        self.setFont(qtutils.default_monospace_font())
        self.set_details(title, label)

    def set_details(self, title, label):
        """Update the window title and progress label"""
        self.setWindowTitle(title)
        self.setLabelText(label + '     ')
        self.animation_thread.set_text(label)

    def set_text(self, txt):
        """Set the label text"""
        self.setLabelText(txt)

    def keyPressEvent(self, event):
        """Customize keyPressEvent to remove the ESC key cancel feature"""
        if event.key() != Qt.Key_Escape:
            super().keyPressEvent(event)

    def start(self):
        """Start the animation thread and use a wait cursor"""
        self.show()
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        self.animation_thread.start()

    def stop(self):
        """Stop the animation thread and restore the normal cursor"""
        self.animation_thread.stop()
        self.animation_thread.wait()
        QtWidgets.QApplication.restoreOverrideCursor()
        self.hide()


class ProgressAnimationThread(QtCore.QThread):
    """Emits a pseudo-animated text stream for progress bars"""

    # The updated signal is emitted on each tick.
    updated = Signal(object)

    def __init__(self, txt, parent, sleep_time=0.1):
        QtCore.QThread.__init__(self, parent)
        self.running = False
        self.txt = txt
        self.sleep_time = sleep_time
        self.symbols = [
            '.  ..',
            '..  .',
            '...  ',
            ' ... ',
            '  ...',
        ]
        self.idx = -1

    def set_text(self, txt):
        """Set the text prefix"""
        self.txt = txt

    def tick(self):
        """Tick to the next animated text value"""
        self.idx = (self.idx + 1) % len(self.symbols)
        return self.txt + self.symbols[self.idx]

    def stop(self):
        """Stop the animation thread"""
        self.running = False

    def run(self):
        """Emit ticks until stopped"""
        self.running = True
        while self.running:
            self.updated.emit(self.tick())
            time.sleep(self.sleep_time)


class ProgressTickThread(QtCore.QThread):
    """Emits an int stream for progress bars"""

    # The updated signal emits progress tick values.
    updated = Signal(int)
    # The activated signal is emitted when the progress bar is displayed.
    activated = Signal()

    def __init__(
        self,
        parent,
        maximum,
        start_time=1.0,
        sleep_time=0.05,
    ):
        QtCore.QThread.__init__(self, parent)
        self.running = False
        self.sleep_time = sleep_time
        self.maximum = maximum
        self.start_time = start_time
        self.value = 0
        self.step = 1

    def tick(self):
        """Cycle to the next tick value

        Returned values are in the inclusive (0, maximum + 1) range.
        """
        self.value = (self.value + self.step) % (self.maximum + 1)
        if self.value == self.maximum:
            self.step = -1
        elif self.value == 0:
            self.step = 1
        return self.value

    def stop(self):
        """Stop the tick thread and reset to the initial state"""
        self.running = False
        self.value = 0
        self.step = 1

    def run(self):
        """Start the tick thread

        The progress bar will not be activated until after the start_time
        interval has elapsed.
        """
        initial_time = time.time()
        active = False
        self.running = True
        self.value = 0
        self.step = 1
        while self.running:
            if active:
                self.updated.emit(self.tick())
            else:
                now = time.time()
                if self.start_time < (now - initial_time):
                    active = True
                    self.activated.emit()
            time.sleep(self.sleep_time)


class SpinBox(QtWidgets.QSpinBox):
    def __init__(
        self,
        parent=None,
        value=None,
        mini=1,
        maxi=99999,
        step=0,
        prefix='',
        suffix='',
        tooltip='',
        wrap=False,
    ):
        QtWidgets.QSpinBox.__init__(self, parent)
        self.setAlignment(Qt.AlignRight)
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.PlusMinus)
        self.setPrefix(prefix)
        self.setSuffix(suffix)
        self.setWrapping(True)
        self.setMinimum(mini)
        self.setMaximum(maxi)
        self.setWrapping(wrap)
        if step:
            self.setSingleStep(step)
        if value is not None:
            self.set_value(value)
        text_width = qtutils.text_width(self.font(), 'MMMMMM')
        width = max(self.minimumWidth(), text_width)
        self.setMinimumWidth(width)
        if tooltip:
            self.setToolTip(tooltip)

    def set_value(self, value):
        """Set the spinbox value directly"""
        self.setValue(value)


class DirectoryPathLineEdit(QtWidgets.QWidget):
    """A combined line edit and file browser button"""

    def __init__(self, path, parent):
        QtWidgets.QWidget.__init__(self, parent)

        self.line_edit = QtWidgets.QLineEdit()
        self.line_edit.setText(path)

        self.browse_button = qtutils.create_button(
            tooltip=N_('Select directory'), icon=icons.folder()
        )
        layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.browse_button,
            self.line_edit,
        )
        self.setLayout(layout)

        qtutils.connect_button(self.browse_button, self._select_directory)

    def set_value(self, value):
        """Set the path value"""
        self.line_edit.setText(value)

    def value(self):
        """Return the current path value"""
        return self.line_edit.text().strip()

    def _select_directory(self):
        """Open a file browser and select a directory"""
        output_dir = qtutils.opendir_dialog(N_('Select directory'), self.value())
        if not output_dir:
            return
        # Make the directory relative only if it the current directory or
        # or subdirectory from the current directory.
        current_dir = core.getcwd()
        if output_dir == current_dir:
            output_dir = '.'
        elif output_dir.startswith(current_dir + os.sep):
            output_dir = os.path.relpath(output_dir)
        self.set_value(output_dir)


def export_header_columns(widget, state):
    """Save QHeaderView column sizes"""
    columns = []
    header = widget.horizontalHeader()
    for idx in range(header.count()):
        columns.append(header.sectionSize(idx))

    state['columns'] = columns


def apply_header_columns(widget, state):
    """Apply QHeaderView column sizes"""
    columns = mklist(state.get('columns', []))
    header = widget.horizontalHeader()
    if header.stretchLastSection():
        # Setting the size will make the section wider than necessary, which
        # defeats the purpose of the stretch flag.  Skip the last column when
        # it's stretchy so that it retains the stretchy behavior.
        columns = columns[:-1]
    for idx, size in enumerate(columns):
        header.resizeSection(idx, size)


class MessageBox(Dialog):
    """Improved QMessageBox replacement

    QMessageBox has a lot of usability issues.  It sometimes cannot be
    resized, and it brings along a lots of annoying properties that we'd have
    to workaround, so we use a simple custom dialog instead.

    """

    def __init__(
        self,
        parent=None,
        title='',
        text='',
        info='',
        details='',
        logo=None,
        default=False,
        ok_icon=None,
        ok_text='',
        cancel_text=None,
        cancel_icon=None,
    ):
        Dialog.__init__(self, parent=parent)

        if parent:
            self.setWindowModality(Qt.WindowModal)
        if title:
            self.setWindowTitle(title)

        self.logo_label = QtWidgets.QLabel()
        if logo:
            # Render into a 1-inch wide pixmap
            pixmap = logo.pixmap(defs.large_icon)
            self.logo_label.setPixmap(pixmap)
        else:
            self.logo_label.hide()

        self.text_label = QtWidgets.QLabel()
        self.text_label.setText(text)

        self.info_label = QtWidgets.QLabel()
        if info:
            self.info_label.setText(info)
        else:
            self.info_label.hide()

        ok_icon = icons.mkicon(ok_icon, icons.ok)
        self.button_ok = qtutils.create_button(text=ok_text, icon=ok_icon)

        self.button_close = qtutils.close_button(text=cancel_text, icon=cancel_icon)

        if ok_text:
            self.button_ok.setText(ok_text)
        else:
            self.button_ok.hide()

        self.details_text = QtWidgets.QPlainTextEdit()
        self.details_text.setReadOnly(True)
        if details:
            self.details_text.setFont(qtutils.default_monospace_font())
            self.details_text.setPlainText(details)
        else:
            self.details_text.hide()

        self.info_layout = qtutils.vbox(
            defs.large_margin,
            defs.button_spacing,
            self.text_label,
            self.info_label,
            qtutils.STRETCH,
        )

        self.top_layout = qtutils.hbox(
            defs.large_margin,
            defs.button_spacing,
            self.logo_label,
            self.info_layout,
            qtutils.STRETCH,
        )

        self.buttons_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            qtutils.STRETCH,
            self.button_close,
            self.button_ok,
        )

        self.main_layout = qtutils.vbox(
            defs.margin,
            defs.button_spacing,
            self.top_layout,
            self.buttons_layout,
            self.details_text,
        )
        self.main_layout.setStretchFactor(self.details_text, 2)
        self.setLayout(self.main_layout)

        if default:
            self.button_ok.setDefault(True)
            self.button_ok.setFocus()
        else:
            self.button_close.setDefault(True)
            self.button_close.setFocus()

        qtutils.connect_button(self.button_ok, self.accept)
        qtutils.connect_button(self.button_close, self.reject)
        self.init_state(None, self.set_initial_size)

    def set_initial_size(self):
        width = defs.dialog_w
        height = defs.msgbox_h
        self.resize(width, height)

    def keyPressEvent(self, event):
        """Handle Y/N hotkeys"""
        key = event.key()
        if key == Qt.Key_Y:
            QtCore.QTimer.singleShot(0, self.accept)
        elif key in (Qt.Key_N, Qt.Key_Q):
            QtCore.QTimer.singleShot(0, self.reject)
        elif key == Qt.Key_Tab:
            if self.button_ok.isVisible():
                event.accept()
                if self.focusWidget() == self.button_close:
                    self.button_ok.setFocus()
                else:
                    self.button_close.setFocus()
                return
        Dialog.keyPressEvent(self, event)

    def run(self):
        self.show()
        return self.exec_()

    def apply_state(self, state):
        """Imports data for view save/restore"""
        desktop_width, desktop_height = qtutils.desktop_size()
        width = min(desktop_width, utils.asint(state.get('width')))
        height = min(desktop_height, utils.asint(state.get('height')))
        x = min(desktop_width, utils.asint(state.get('x')))
        y = min(desktop_height, utils.asint(state.get('y')))
        result = False

        if width and height:
            self.resize(width, height)
            self.move(x, y)
            result = True

        return result

    def export_state(self):
        """Exports data for view save/restore"""
        desktop_width, desktop_height = qtutils.desktop_size()
        state = {}
        state['width'] = min(desktop_width, self.width())
        state['height'] = min(desktop_height, self.height())
        state['x'] = min(desktop_width, self.x())
        state['y'] = min(desktop_height, self.y())
        return state


def confirm(
    title,
    text,
    informative_text,
    ok_text,
    icon=None,
    default=True,
    cancel_text=None,
    cancel_icon=None,
):
    """Confirm that an action should take place"""
    cancel_text = cancel_text or N_('Cancel')
    logo = icons.from_style(QtWidgets.QStyle.SP_MessageBoxQuestion)

    mbox = MessageBox(
        parent=qtutils.active_window(),
        title=title,
        text=text,
        info=informative_text,
        ok_text=ok_text,
        ok_icon=icon,
        cancel_text=cancel_text,
        cancel_icon=cancel_icon,
        logo=logo,
        default=default,
    )

    return mbox.run() == mbox.Accepted


def critical(title, message=None, details=None):
    """Show a warning with the provided title and message."""
    if message is None:
        message = title
    logo = icons.from_style(QtWidgets.QStyle.SP_MessageBoxCritical)
    mbox = MessageBox(
        parent=qtutils.active_window(),
        title=title,
        text=message,
        details=details,
        logo=logo,
    )
    mbox.run()


def command_error(title, cmd, status, out, err):
    """Report an error message about a failed command"""
    details = Interaction.format_out_err(out, err)
    message = Interaction.format_command_status(cmd, status)
    critical(title, message=message, details=details)


def information(title, message=None, details=None, informative_text=None):
    """Show information with the provided title and message."""
    if message is None:
        message = title
    mbox = MessageBox(
        parent=qtutils.active_window(),
        title=title,
        text=message,
        info=informative_text,
        details=details,
        logo=icons.cola(),
    )
    mbox.run()


def progress(title, text, parent):
    """Create a new ProgressDialog"""
    return ProgressDialog(title, text, parent)


class ProgressBar(QtWidgets.QProgressBar):
    """An indeterminate progress bar with animated scrolling"""

    def __init__(self, parent, maximum, hide=(), disable=(), visible=False):
        super().__init__(parent)
        self.setTextVisible(False)
        self.setMaximum(maximum)
        if not visible:
            self.setVisible(False)
        self.progress_thread = ProgressTickThread(self, maximum)
        self.progress_thread.updated.connect(self.setValue, type=Qt.QueuedConnection)
        self.progress_thread.activated.connect(self.activate, type=Qt.QueuedConnection)
        self._widgets_to_hide = hide
        self._widgets_to_disable = disable

    def start(self):
        """Start the progress tick thread"""
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)

        for widget in self._widgets_to_disable:
            widget.setEnabled(False)

        self.progress_thread.start()

    def activate(self):
        """Hide widgets and display the progress bar"""
        for widget in self._widgets_to_hide:
            widget.hide()
        self.show()

    def stop(self):
        """Stop the progress tick thread, re-enable and display widgets"""
        self.progress_thread.stop()
        self.progress_thread.wait()

        for widget in self._widgets_to_disable:
            widget.setEnabled(True)

        self.hide()
        for widget in self._widgets_to_hide:
            widget.show()

        QtWidgets.QApplication.restoreOverrideCursor()


def progress_bar(parent, maximum=10, hide=(), disable=()):
    """Return a text-less progress bar"""
    widget = ProgressBar(parent, maximum, hide=hide, disable=disable)
    return widget


def question(title, text, default=True, logo=None):
    """Launches a QMessageBox question with the provided title and message.
    Passing "default=False" will make "No" the default choice."""
    parent = qtutils.active_window()
    if logo is None:
        logo = icons.from_style(QtWidgets.QStyle.SP_MessageBoxQuestion)
    msgbox = MessageBox(
        parent=parent,
        title=title,
        text=text,
        default=default,
        logo=logo,
        ok_text=N_('Yes'),
        cancel_text=N_('No'),
    )
    return msgbox.run() == msgbox.Accepted


def save_as(filename, title):
    return qtutils.save_as(filename, title=title)


def async_command(title, cmd, runtask):
    task = qtutils.SimpleTask(partial(core.run_command, cmd))
    task.connect(partial(async_command_result, title, cmd))
    runtask.start(task)


def async_command_result(title, cmd, result):
    status, out, err = result
    cmd_string = core.list2cmdline(cmd)
    Interaction.command(title, cmd_string, status, out, err)


def install():
    """Install the GUI-model interaction hooks"""
    Interaction.critical = staticmethod(critical)
    Interaction.confirm = staticmethod(confirm)
    Interaction.question = staticmethod(question)
    Interaction.information = staticmethod(information)
    Interaction.command_error = staticmethod(command_error)
    Interaction.save_as = staticmethod(save_as)
    Interaction.async_command = staticmethod(async_command)
