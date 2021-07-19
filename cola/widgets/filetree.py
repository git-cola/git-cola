from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import QtCore
from qtpy import QtWidgets

from .. import icons
from . import standard


# pylint: disable=too-many-ancestors
class FileTree(standard.TreeWidget):
    def __init__(self, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)
        self.setSelectionMode(self.ExtendedSelection)
        self.setHeaderHidden(True)

    def set_filenames(self, filenames, select=False):
        self.clear()
        if not filenames:
            return
        items = []
        from_filename = icons.from_filename
        for filename in filenames:
            icon = from_filename(filename)
            item = QtWidgets.QTreeWidgetItem()
            item.setIcon(0, icon)
            item.setText(0, filename)
            item.setData(0, QtCore.Qt.UserRole, filename)
            items.append(item)
        self.addTopLevelItems(items)
        if select and items:
            items[0].setSelected(True)

    def has_selection(self):
        return bool(self.selectedItems())

    def selected_filenames(self):
        items = self.selectedItems()
        if not items:
            return []
        return [filename_from_item(i) for i in items]


def filename_from_item(item):
    return item.data(0, QtCore.Qt.UserRole)
