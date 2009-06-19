import os
import sys

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt

from cola import qtutils

class GitRepoModel(QtGui.QStandardItemModel):
    """Provides an interface into a git repository for browsing purposes."""
    def __init__(self, parent, model):
        QtGui.QStandardItem.__init__(self, parent)
        self._model = model
        self.setColumnCount(2)
        self.setHeaderData(0, Qt.Horizontal, QtCore.QVariant('Name'))
        self.setHeaderData(1, Qt.Horizontal, QtCore.QVariant('Status'))
        self._dir_indexes = {}
        self._initialize()

    # Read-only property for accessing the passed-in git model.
    app_model = property(lambda self: self._model)

    def add_file(self, parent, path):
        """Add a file entry to the model."""
        file_entry = GitRepoItem(path=path, parent=parent)
        file_entry.setIcon(qtutils.file_icon())
        status_entry = GitRepoStatusItem(path=path, parent=parent)
        nb_rows = parent.rowCount()
        parent.setChild(nb_rows, 0, file_entry)
        parent.setChild(nb_rows, 1, status_entry)

    def add_directory(self, parent, path):
        """Add a directory entry to the model."""
        entry = GitRepoItem(path=path, parent=parent)
        entry.setIcon(qtutils.dir_icon())
        dir_index = self._dir_indexes.setdefault(parent, 0)
        parent.setChild(dir_index, 0, entry)
        parent.setChild(dir_index, 1, QtGui.QStandardItem())
        self._dir_indexes[parent] += 1
        return entry

    def _initialize(self):
        """Iterate over the cola model and create GitRepoItems."""
        direntries = {'': self.invisibleRootItem()}
        for path in self._model.all_files():
            dirname = os.path.dirname(path)
            if dirname in direntries:
                parent = direntries[dirname]
            else:
                parent = self._create_dir_entry(dirname, direntries)
                direntries[dirname] = parent
            self.add_file(parent, path)

    def _create_dir_entry(self, dirname, direntries):
        """
        Create a directory entry for the model.

        This ensures that directories are always listed before files.

        """
        entries = dirname.split('/')
        curdir = []
        parent = self.invisibleRootItem()
        for entry in entries:
            curdir.append(entry)
            path = '/'.join(curdir)
            if path in direntries:
                parent = direntries[path]
            else:
                grandparent = parent
                parent_path = '/'.join(curdir[:-1])
                parent = self.add_directory(grandparent, path)
                direntries[path] = parent
        return parent


# These items represent cells in the tree view.
# There are separate items for the file and status entry

class GitRepoItem(QtGui.QStandardItem):
    def __init__(self, path=None, parent=None):
        QtGui.QStandardItem.__init__(self)
        self._path = path
        self._parent = parent
        self.setEditable(False)
        self.setDragEnabled(False)
        self.setText(os.path.basename(path))
    # Read-only 'path' property
    path = property(lambda self: self._path)

    def type(self):
        return QtGui.QStandardItem.UserType + 1


class GitRepoStatusItem(QtGui.QStandardItem):
    def __init__(self, path=None, parent=None):
        QtGui.QStandardItem.__init__(self)
        self._path = path
        self._parent = parent
        self.setEditable(False)
        self.setDragEnabled(False)
        self.setText('todo: status')
    # Read-only 'path' property
    path = property(lambda self: self._path)
