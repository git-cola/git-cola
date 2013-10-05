from PyQt4 import QtGui


class FlatTreeWidget(QtGui.QTreeWidget):

    def __init__(self, parent=None):
        QtGui.QTreeWidget.__init__(self, parent)
        self.setUniformRowHeights(True)
        self.setAllColumnsShowFocus(True)
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(False)

    def items(self):
        root = self.invisibleRootItem()
        child = root.child
        count = root.childCount()
        return [child(i) for i in range(count)]

    def selected_items(self):
        return self.selectedItems()

    def selected_item(self):
        """Return the currently selected item"""
        selected_items = self.selected_items()
        if not selected_items:
            return None
        return selected_items[0]
