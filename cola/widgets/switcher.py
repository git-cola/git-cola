"""Provides quick switcher"""
from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtCore
from qtpy import QtGui
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import qtutils
from ..widgets import defs
from ..widgets import standard
from ..widgets import text


def switcher(
    context, entries, title, place_holder=None, enter_action=None, parent=None
):
    widget = SwitcherDialog(context, entries, title, place_holder, enter_action, parent)
    widget.show()
    return widget


def switcher_item(key, icon=None, name=None):
    return SwitcherListItem(key, icon, name)


class SwitcherDialog(standard.Dialog):
    """
    Quick switcher dialog class. This contains input field, filter proxy model and quick
    switcher list view(OPTIONALLY by show_lsit).

    list_fitlered signal is for the event that user input strings to input field and
    filtered items by proxy model.
    switcher_selection_move signal is for the event that selecttion move key like UP,
    DOWN has pressed.
    These signals will only be emitted when this class does not have switcher_list
    class.
    """

    def __init__(
        self, context, entries, title, place_holder=None, enter_action=None, parent=None
    ):
        standard.Dialog.__init__(self, parent=parent)
        self.setModal(False)
        self.setWindowTitle(title)

        self.context = context
        self.entries = entries
        self.enter_action = enter_action

        self.filter_input = SwitcherLineEdit(place_holder=place_holder, parent=self)

        self.proxy_model = SwitcherSortFilterProxyModel(entries, parent=self)

        if enter_action:
            self.switcher_list = SwitcherTreeView(
                self.proxy_model, self.enter_selected_item, parent=self
            )
        else:
            self.switcher_list = None

        self.filter_input.switcher_selection_move.connect(self.switcher_selection_moved)
        self.filter_input.textChanged.connect(self.filter_input_changed)

        self.main_layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.filter_input, self.switcher_list
        )
        self.setLayout(self.main_layout)

    def resizeEvent(self, event):
        parent = self.parent()
        if parent is None:
            return
        left = parent.x()
        width = parent.width()
        center_x = left + width // 2
        x = center_x - self.width() // 2
        y = parent.y()

        self.move(x, y)

    def filter_input_changed(self):
        text = self.filter_input.text()
        self.proxy_model.setFilterRegExp(text)

    def switcher_selection_moved(self, event):
        if self.switcher_list:
            self.switcher_list.keyPressEvent(event)

    def enter_selected_item(self, index):
        item = self.switcher_list.model().itemFromIndex(index)
        if item:
            self.enter_action(item)
        self.close()


class SwitcherLineEdit(text.LineEdit):
    """Quick switcher input line class"""

    switcher_selection_move = Signal(QtGui.QKeyEvent)

    def __init__(self, place_holder=None, parent=None):
        text.LineEdit.__init__(self, parent=parent)
        if place_holder:
            self.setPlaceholderText(place_holder)

    def keyPressEvent(self, event):
        selection_move_keys = [
            Qt.Key_Enter,
            Qt.Key_Return,
            Qt.Key_Up,
            Qt.Key_Down,
            Qt.Key_Home,
            Qt.Key_End,
            Qt.Key_PageUp,
            Qt.Key_PageDown,
        ]

        pressed_key = event.key()
        if pressed_key in selection_move_keys:
            self.switcher_selection_move.emit(event)
        else:
            super().keyPressEvent(event)


class SwitcherSortFilterProxyModel(QtCore.QSortFilterProxyModel):
    """Filtering class for candidate items."""

    def __init__(self, entries, parent=None):
        QtCore.QSortFilterProxyModel.__init__(self, parent)

        self.entries = entries

        self.setDynamicSortFilter(True)
        self.setSourceModel(entries)
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def itemFromIndex(self, index):
        return self.entries.itemFromIndex(self.mapToSource(index))


class SwitcherTreeView(standard.TreeView):
    """Tree view class for showing proxy items in SwitcherSortFilterProxyModel"""

    def __init__(self, entries, enter_action, parent=None):
        standard.TreeView.__init__(self, parent)

        self.setHeaderHidden(True)
        self.setModel(entries)

        self.activated.connect(enter_action)
        self.doubleClicked.connect(enter_action)
        self.entered.connect(enter_action)


class SwitcherListItem(QtGui.QStandardItem):
    """Item class for SwitcherTreeView and SwitcherSortFilterProxyModel"""

    def __init__(self, key, icon=None, name=None):
        QtGui.QStandardItem.__init__(self)

        self.key = key
        if not name:
            name = key

        self.setText(name)
        if icon:
            self.setIcon(icon)
