from PyQt4 import QtCore

import os

from cola.models.gitdirmodel import GitDirModel
from cola.models.gitdirmodel import GitDirEntry

class ClassicController(QtCore.QObject):
    def __init__(self, model, view=None):
        QtCore.QObject.__init__(self, view)
        self._model = model
        self._view = view
        self._dirmodel = None
        self._dircount = {}

    def initialize(self, dirmodel):
        self._dirmodel = dirmodel
        direntries = {'': dirmodel.root()}
        self._dircount[''] = 0

        for name in self._model.all_files():
            dirname = os.path.dirname(name)
            if dirname in direntries:
                parent = direntries[dirname]
            else:
                parent = self._create_dir_entry(dirname, direntries)
                direntries[dirname] = parent
                self._dircount[dirname] = 0
            row = self._dircount[dirname]
            self._dircount[dirname] = row + 1
            entry = GitDirEntry(row, [os.path.basename(name), 'file'], parent)
            parent.add_child(entry)
        self._view.setModel(dirmodel)

    def _create_dir_entry(self, dirname, direntries):
        # FIXME: fix row# problem for entries
        entries = dirname.split('/')
        curdir = []
        parent = self._dirmodel.root()
        for entry in entries:
            curdir.append(entry)
            path = '/'.join(curdir)
            print path
            if path in direntries:
                parent = direntries[path]
            else:
                grandparent = parent
                parent_path = '/'.join(curdir[:-1])
                row = self._dircount[parent_path]
                self._dircount[parent_path] = row + 1
                parent = GitDirEntry(row, [os.path.basename(path), 'good'], parent)
                direntries[path] = parent
                self._dircount[path] = 0
                grandparent.add_child(parent)
        return parent

if __name__ == '__main__':
    import sys
    from PyQt4 import QtGui
    from cola.models import main

    app = QtGui.QApplication(sys.argv)
    model = main.MainModel()
    dirmodel = GitDirModel(model)

    view = QtGui.QTreeView()

    ctl = ClassicController(model, view)
    ctl.initialize(dirmodel)

    view.setWindowTitle(view.tr('classic'))
    view.setModel(dirmodel)
    view.show()

    sys.exit(app.exec_())
