from PyQt4 import QtCore
from PyQt4 import QtGui

from cola import decorators
from cola import qtutils
from cola.compat import ustr
from cola.widgets import standard


class FileTree(standard.TreeWidget):

    def __init__(self, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)
        self.icon_from_filename = decorators.memoize(qtutils.icon_from_filename)
        self.setSelectionMode(self.ExtendedSelection)
        self.setHeaderHidden(True)

    def set_filenames(self, filenames, select=False):
        self.clear()
        if not filenames:
            return
        items = []
        for filename in filenames:
            icon = self.icon_from_filename(filename)
            item = QtGui.QTreeWidgetItem()
            item.setIcon(0, icon)
            item.setText(0, filename)
            item.setData(0, QtCore.Qt.UserRole, QtCore.QVariant(filename))
            items.append(item)
        self.addTopLevelItems(items)
        if select:
            self.setItemSelected(items[0], True)

    def filename_from_item(self, item):
        return ustr(item.data(0, QtCore.Qt.UserRole).toPyObject())

    def has_selection(self):
        return bool(self.selectedItems())

    def selected_filenames(self):
        items = self.selectedItems()
        if not items:
            return []
        filename_from_item = self.filename_from_item
        return [filename_from_item(i) for i in items]
