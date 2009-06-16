import os
import sys

from PyQt4 import QtCore
from PyQt4 import QtGui


class GitDirModel(QtCore.QAbstractItemModel):
    """A model to represent a git work tree
    """
    def __init__(self, model):
        QtCore.QAbstractItemModel.__init__(self)
        self._model = model
        self._root = GitDirEntry(path='Name', status='Status')
        self._initialize()

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
            item = self.root()
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
        """Returns the model's root item"""
        return self._root

    def columnCount(self, parent=None):
        """Returns the number of columns to display"""
        return self.root().num_columns()

    def headerData(self, section, orientation, role):
        """Returns data for the column headers"""
        if (orientation == QtCore.Qt.Horizontal and
                role == QtCore.Qt.DisplayRole):
            if section < self.root().num_columns():
                return QtCore.QVariant(self.root().data(section))
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

    def _initialize(self):
        direntries = {'': self.root()}
        for path in self._model.all_files():
            dirname = os.path.dirname(path)
            if dirname in direntries:
                parent = direntries[dirname]
            else:
                parent = self._create_dir_entry(dirname, direntries)
                direntries[dirname] = parent

            entry = GitDirEntry(path=path, parent=parent)
            parent.add_file(entry)

    def _create_dir_entry(self, dirname, direntries):
        entries = dirname.split('/')
        curdir = []
        parent = self.root()
        for entry in entries:
            curdir.append(entry)
            path = '/'.join(curdir)
            if path in direntries:
                parent = direntries[path]
            else:
                grandparent = parent
                parent_path = '/'.join(curdir[:-1])
                parent = GitDirEntry(path=path, parent=parent)
                direntries[path] = parent
                grandparent.add_directory(parent)
        return parent



class GitDirEntry(object):
    """Represents an entry in the GitDirModel
    """
    def __init__(self, path='', status='', parent=None):
        self._parent = parent
        self._children = []
        self._path = path
        self._status = status
        self._name = os.path.basename(path)
        self._dirindex = 0

    path = property(lambda self: self._path)

    def add_file(self, child):
        """Add a file to this entry.
        """
        self._children.append(child)

    def add_directory(self, dirent):
        """Add a directory to this entry.
        """
        self._children.insert(self._dirindex, dirent)
        self._dirindex += 1

    def num_columns(self):
        return 2

    def data(self, idx):
        """Returns column data for an entry"""
        return (self._name, self._status)[idx]

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
        if self._parent:
            return self._parent.child_index(self)
        else:
            return -1

    def child_index(self, child):
        return self._children.index(child)
