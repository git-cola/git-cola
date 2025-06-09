from qtpy import QtCore
from qtpy import QtWidgets

from .. import icons
from . import standard


class FileTree(standard.TreeWidget):
    """A flag list of files presented using a tree widget"""

    def __init__(self, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)
        self.setSelectionMode(self.ExtendedSelection)
        self.setHeaderHidden(True)

    def set_filenames(self, filenames, select=False):
        """Update the tree to match the specified filenames"""
        self.clear()
        if not filenames:
            return
        items = []
        from_filename = icons.from_filename
        role = QtCore.Qt.UserRole
        for filename in filenames:
            icon = from_filename(filename)
            item = QtWidgets.QTreeWidgetItem()
            item.setIcon(0, icon)
            item.setText(0, filename)
            item.setData(0, role, filename)
            items.append(item)
        self.addTopLevelItems(items)
        if select and items:
            items[0].setSelected(True)

    def has_selection(self):
        """Does the tree have an item currently selected?"""
        return bool(self.selectedItems())

    def selected_filenames(self):
        """Return the currently selected filenames"""
        items = self.selectedItems()
        if not items:
            return []
        return [filename_from_item(i) for i in items]


def filename_from_item(item):
    """Extract the filename user data from the QTreeWidgetItem"""
    return item.data(0, QtCore.Qt.UserRole)
