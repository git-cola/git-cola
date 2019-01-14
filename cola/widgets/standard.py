from __future__ import division, absolute_import, unicode_literals
import time
from functools import partial

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


class WidgetMixin(object):
    """Mix-in for common utilities and serialization of widget state"""

    def __init__(self):
        self._unmaximized_rect = {}

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
        if utils.is_darwin():
            self.resize(width, height)
        else:
            shown = self.isVisible()
            # earlier show() fools Windows focus stealing prevention. the main
            # window is blocked for the duration of "git rebase" and we don't
            # want to present a blocked window with git-xbase hidden somewhere.
            self.show()
            self.setWindowState(Qt.WindowMaximized)
            if not shown:
                self.hide()

    def name(self):
        """Returns the name of the view class"""
        return self.__class__.__name__.lower()

    def save_state(self, settings=None):
        save = True
        context = getattr(self, 'context', None)
        if context:
            cfg = context.cfg
            save = cfg.get('cola.savewindowsettings', default=True)
        if save:
            if settings is None:
                settings = Settings()
                settings.load()
            settings.save_gui_state(self)

    def restore_state(self, settings=None):
        if settings is None:
            settings = Settings()
            settings.load()
        state = settings.get_gui_state(self)
        if state:
            result = self.apply_state(state)
        else:
            result = False
        return result

    def apply_state(self, state):
        """Imports data for view save/restore"""

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
        return self.save_state(settings=settings)

    def closeEvent(self, event):
        self.save_settings()
        self.Base.closeEvent(self, event)

    def init_size(self, parent=None, settings=None, width=0, height=0):
        if not width:
            width = defs.dialog_w
        if not height:
            height = defs.dialog_h
        self.init_state(settings, self.resize_to_parent, parent, width, height)

    def init_state(self, settings, callback, *args, **kwargs):
        """Restore saved settings or set the initial location"""
        if not self.restore_state(settings=settings):
            callback(*args, **kwargs)
            self.center()

    def resize_to_parent(self, parent, w, h):
        """Set the initial size of the widget"""
        width, height = qtutils.default_size(parent, w, h)
        self.resize(width, height)


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

    def save_settings(self, settings=None):
        if settings is None:
            context = getattr(self, 'context', None)
            settings = Settings()
            settings.load()
            settings.add_recent(core.getcwd(), prefs.maxrecent(context))
        return WidgetMixin.save_settings(self, settings=settings)

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


class ListWidget(QtWidgets.QListWidget):
    """QListWidget with vim j/k navigation hotkeys"""

    def __init__(self, parent=None):
        super(ListWidget, self).__init__(parent)

        self.up_action = qtutils.add_action(
            self, N_('Move Up'), self.move_up,
            hotkeys.MOVE_UP, hotkeys.MOVE_UP_SECONDARY)

        self.down_action = qtutils.add_action(
            self, N_('Move Down'), self.move_down,
            hotkeys.MOVE_DOWN, hotkeys.MOVE_DOWN_SECONDARY)

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
            model = widget.model()
            if (hasattr(model, 'itemFromIndex')
                    and model.itemFromIndex(index).rowCount() == 0):
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
        else:
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

    def __init__(self, parent=None):
        QtWidgets.QDialog.__init__(self, parent)
        WidgetMixin.__init__(self)
        # Disable the Help button hint on Windows
        if hasattr(Qt, 'WindowContextHelpButtonHint'):
            help_hint = Qt.WindowContextHelpButtonHint
            flags = self.windowFlags() & ~help_hint
            self.setWindowFlags(flags)

    def setLayout(self, layout):
        frame = QtWidgets.QFrame(self)
        frame.setLayout(layout)
        main_layout = qtutils.vbox(0, 0, frame)
        self.Base.setLayout(self, main_layout)

    def accept(self):
        self.save_settings()
        return self.Base.accept(self)

    def reject(self):
        self.save_settings()
        return self.Base.reject(self)

    def close(self):
        """save_settings() is handled by accept() and reject()"""
        self.Base.close(self)

    def closeEvent(self, event):
        """save_settings() is handled by accept() and reject()"""
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
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)
        self.reset()
        self.setRange(0, 0)
        self.setMinimumDuration(0)
        self.setCancelButton(None)
        self.setFont(qtutils.default_monospace_font())
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

    def __init__(self, parent=None, value=None,
                 mini=1, maxi=99999, step=0, prefix='', suffix=''):
        QtWidgets.QSpinBox.__init__(self, parent)
        self.setPrefix(prefix)
        self.setSuffix(suffix)
        self.setWrapping(True)
        self.setMinimum(mini)
        self.setMaximum(maxi)
        if step:
            self.setSingleStep(step)
        if value is not None:
            self.setValue(value)


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
    def __init__(self, parent=None, title='', text='',
                 info='', details='', logo=None, default=False,
                 ok_icon=None, ok_text='', cancel_text=None, cancel_icon=None):

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

        self.button_toggle_details = qtutils.create_button(
            text=N_('Show Details...'))

        self.button_close = qtutils.close_button(
            text=cancel_text, icon=cancel_icon)

        if ok_text:
            self.button_ok.setText(ok_text)
        else:
            self.button_ok.hide()

        if default:
            self.button_ok.setDefault(True)
            self.button_ok.setFocus()
        else:
            self.button_close.setDefault(True)
            self.button_close.setFocus()

        self.details_text = QtWidgets.QPlainTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.hide()
        if details:
            self.details_text.setFont(qtutils.default_monospace_font())
            self.details_text.setPlainText(details)
        else:
            self.button_toggle_details.hide()

        self.info_layout = qtutils.vbox(
            defs.large_margin, defs.button_spacing,
            self.text_label, self.info_label, qtutils.STRETCH)

        self.top_layout = qtutils.hbox(
            defs.large_margin, defs.button_spacing,
            self.logo_label, self.info_layout, qtutils.STRETCH)

        self.buttons_layout = qtutils.hbox(
            defs.no_margin, defs.button_spacing, qtutils.STRETCH,
            self.button_toggle_details, self.button_close, self.button_ok)

        self.main_layout = qtutils.vbox(
            defs.margin, defs.button_spacing,
            self.top_layout,
            self.buttons_layout,
            self.details_text)
        self.main_layout.setStretchFactor(self.details_text, 2)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.button_ok, self.accept)
        qtutils.connect_button(self.button_close, self.reject)
        qtutils.connect_button(self.button_toggle_details, self.toggle_details)
        self.init_state(None, self.set_initial_size)

    def set_initial_size(self):
        width = defs.dialog_w
        height = defs.msgbox_h
        self.resize(width, height)

    def toggle_details(self):
        if self.details_text.isVisible():
            text = N_('Show Details...')
            self.details_text.hide()
            QtCore.QTimer.singleShot(
                0, lambda: self.resize(self.width(), defs.msgbox_h))
        else:
            text = N_('Hide Details..')
            self.details_text.show()
            new_height = defs.msgbox_h * 4
            if self.height() < new_height:
                QtCore.QTimer.singleShot(
                    0, lambda: self.resize(self.width(), new_height))

        self.button_toggle_details.setText(text)

    def keyPressEvent(self, event):
        """Handle Y/N hotkeys"""
        key = event.key()
        if key == Qt.Key_Y:
            QtCore.QTimer.singleShot(0, self.accept)
        elif key in (Qt.Key_N, Qt.Key_Q):
            QtCore.QTimer.singleShot(0, self.reject)
        return Dialog.keyPressEvent(self, event)

    def run(self):
        self.show()
        return self.exec_()


def confirm(title, text, informative_text, ok_text,
            icon=None, default=True,
            cancel_text=None, cancel_icon=None):
    """Confirm that an action should take place"""
    cancel_text = cancel_text or N_('Cancel')
    logo = icons.from_style(QtWidgets.QStyle.SP_MessageBoxQuestion)

    mbox = MessageBox(
        parent=qtutils.active_window(), title=title, text=text,
        info=informative_text, ok_text=ok_text, ok_icon=icon,
        cancel_text=cancel_text, cancel_icon=cancel_icon,
        logo=logo, default=default)

    return mbox.run() == mbox.Accepted


def critical(title, message=None, details=None):
    """Show a warning with the provided title and message."""
    if message is None:
        message = title
    logo = icons.from_style(QtWidgets.QStyle.SP_MessageBoxCritical)
    mbox = MessageBox(
        parent=qtutils.active_window(), title=title, text=message,
        details=details, logo=logo)
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
        parent=qtutils.active_window(), title=title, text=message,
        info=informative_text, details=details, logo=icons.cola())
    mbox.run()


def question(title, text, default=True):
    """Launches a QMessageBox question with the provided title and message.
    Passing "default=False" will make "No" the default choice."""
    parent = qtutils.active_window()
    logo = icons.from_style(QtWidgets.QStyle.SP_MessageBoxQuestion)
    msgbox = MessageBox(
        parent=parent, title=title, text=text, default=default, logo=logo,
        ok_text=N_('Yes'), cancel_text=N_('No'))
    return msgbox.run() == msgbox.Accepted


def save_as(filename, title):
    return qtutils.save_as(filename, title=title)


def async_command(title, cmd, runtask):
    parent = qtutils.active_window()
    task = qtutils.SimpleTask(parent, partial(core.run_command, cmd))
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
