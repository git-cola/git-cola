import os

from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

import cola.utils
from cola.models.gitdirmodel import GitDirModel
from cola.models.gitdirmodel import GitDirEntry

class ClassicController(QtCore.QObject):
    def __init__(self, model, view=None):
        QtCore.QObject.__init__(self, view)
        self.model = model
        self.view = view
        self.connect(view, SIGNAL('history(QStringList)'),
                     self._view_history)


    def _view_history(self, entries):
        """Launch the configured history browser path-limited to entries."""
        entries = map(unicode, entries)
        cmd = [self.model.get_history_browser(), '--all', '--']
        cola.utils.fork(cmd + entries)


if __name__ == '__main__':
    import sys
    from PyQt4 import QtGui
    from cola.models import main
    from cola.views import repo

    app = QtGui.QApplication(sys.argv)
    model = main.MainModel()
    model.use_worktree(os.getcwd())
    dirmodel = GitDirModel(model)

    view = repo.RepoTreeView()
    view.setModel(dirmodel)
    view.resize(720, 300)

    controller = ClassicController(model, view)

    view.show()
    view.raise_()

    sys.exit(app.exec_())
