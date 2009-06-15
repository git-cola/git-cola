from PyQt4 import QtCore

import os

from cola.models.gitdirmodel import GitDirModel
from cola.models.gitdirmodel import GitDirEntry

class ClassicController(QtCore.QObject):
    def __init__(self, model, view=None):
        QtCore.QObject.__init__(self, view)
        self._model = model
        self._view = view


if __name__ == '__main__':
    import sys
    from PyQt4 import QtGui
    from cola.models import main

    app = QtGui.QApplication(sys.argv)
    model = main.MainModel()
    dirmodel = GitDirModel(model)

    view = QtGui.QTreeView()
    view.setWindowTitle(view.tr('classic'))
    view.setAlternatingRowColors(True)
    view.setModel(dirmodel)
    view.resize(720, 300)
    view.show()
    view.raise_()

    sys.exit(app.exec_())
