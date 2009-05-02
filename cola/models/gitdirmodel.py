import sys

from PyQt4 import QtCore
from PyQt4 import QtGui


class GitDirModel(QtCore.QAbstractItemModel):
    """A model to represent a git work tree
    """
    def __init__(self, model):
        QtCore.QAbstractItemModel.__init__(self)
        self._headers = ('Name', 'Status')
        self._num_columns = len(self._headers)
        self._root = GitDirEntry(-1, self._headers)

    def parent(self, child):
        """Returns the index for the parent of a child entry"""
        if not child.isValid():
            return QtCore.QModelIndex()

        child = child.internalPointer()
        parent = child.parent()

        if not parent or parent == self._root:
            return QtCore.QModelIndex()

        return self.createIndex(parent.row(), 0, parent)

    def data(self, index, role):
        """Returns the data for a specific index"""
        if not index.isValid():
            return QtCore.QVariant()

        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()

        item = index.internalPointer()
        column = index.column()

        if column >= 0 and column < self.columnCount():
            return QtCore.QVariant(item.data(column))

        return QtCore.QVariant()

    def index(self, row, column, parent):
        """Returns a QModelIndex for mapping into the DirModel"""
        if (column < 0 or column >= self.columnCount() or
                row < 0 or row >= self.rowCount(parent)):
            return QtCore.QModelIndex()

        if not parent.isValid():
            item = self._root
        else:
            item = parent.internalPointer()

        child = item.child(row)
        if child:
            return self.createIndex(row, column, child)
        else:
            return QtCore.QModelIndex()

    def flags(self, index):
        """Sets the selectable flag for dir entries"""
        if not index.isValid():
            return QtCore.Qt.ItemIsEnabled
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def root(self):
        """Returns the mode's root item"""
        return self._root

    def columnCount(self, parent=None):
        """Returns the number of columns to display"""
        return self._num_columns

    def headerData(self, section, orientation, role):
        """Returns data for the column headers"""
        if (orientation == QtCore.Qt.Horizontal and
                role == QtCore.Qt.DisplayRole):
            if section < len(self._headers):
                return QtCore.QVariant(self._root.data(section))
        return QtCore.QVariant()

    def rowCount(self, parent):
        """Returns the number of rows for a parent"""
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            item = self._root
        else:
            item = parent.internalPointer()
        return len(item._children)


class GitDirEntry(object):
    """Represents an entry in the GitDirModel
    """
    def __init__(self, row, data, parent=None):
        self._parent = parent
        self._row = row # Record the item's location within its parent.
        self._children = []
        self._data = map(QtCore.QVariant, data)

    def add_child(self, child):
        """
        Adds a child to this entry.

        Entries with children represent "tree" objects, AKA directories
        """
        self._children.append(child)

    def data(self, idx):
        """Returns column data for an entry"""
        return self._data[idx]

    def parent(self):
        """Returns the parent of an entry"""
        return self._parent

    def children(self):
        """Returns a list of child entries"""
        return self._children

    def child(self, index):
        """Returns the child entry at a given index"""
        if index >= 0 and index < len(self._children):
            return self._children[index]
        return None

    def row(self):
        """Returns this entry's row relative to its parent"""
        return self._row
