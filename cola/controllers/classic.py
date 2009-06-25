import os

from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

import cola.utils
import cola.difftool

from cola.models import gitrepo
from cola.controllers.selectcommits import select_commits


class ClassicController(QtCore.QObject):
    def __init__(self, model, view=None):
        QtCore.QObject.__init__(self, view)
        self.model = model
        self.view = view
        self.updated = set()
        self.connect(view, SIGNAL('history(QStringList)'),
                     self._view_history)
        self.connect(view, SIGNAL('expanded(QModelIndex)'),
                     self._query_model)
        self.connect(view, SIGNAL('stage(QStringList)'),
                     self._stage)
        self.connect(view, SIGNAL('unstage(QStringList)'),
                     self._unstage)
        self.connect(view, SIGNAL('difftool(QStringList)'),
                     self._difftool)
        self.connect(view, SIGNAL('difftool_predecessor(QStringList)'),
                     self._difftool_predecessor)
        self.connect(view, SIGNAL('revert(QStringList)'),
                     self._revert)

    def _view_history(self, entries):
        """Launch the configured history browser path-limited to entries."""
        entries = map(unicode, entries)
        cmd = [self.model.get_history_browser(), '--all', '--']
        cola.utils.fork(cmd + entries)

    def _query_model(self, model_index):
        """Update information about a directory as it is expanded."""
        item = self.view.item_from_index(model_index)
        path = item.path
        if path in self.updated:
            return
        self.updated.add(path)
        item.entry.update()
        for row in xrange(item.rowCount()):
            item.child(row, 0).entry.update()

    def _stage(self, qstrings):
        """Stage files for commit."""
        paths = map(unicode, qstrings)
        self.model.stage_paths(paths)

    def _unstage(self, qstrings):
        """Unstage files for commit."""
        paths = map(unicode, qstrings)
        self.model.unstage_paths(paths)

    def _difftool(self, qstrings):
        """Launch difftool on a path."""
        paths = map(unicode, qstrings)
        cola.difftool.launch(['HEAD', '--'] + paths)

    def _difftool_predecessor(self, qstrings):
        """Prompt for an older commit and launch difftool against it."""
        paths = map(unicode, qstrings)
        args = ['--'] + paths
        revs, summaries = self.model.log_helper(all=True, extra_args=args)
        commits = select_commits(self.model, self.view,
                                 'Select Previous Version',
                                 revs, summaries, multiselect=False)
        if not commits:
            return
        commit = commits[0]
        cola.difftool.launch([commit, '--'] + paths)

    def _revert(self, qstrings):
        """Revert paths to HEAD."""
        paths = map(unicode, qstrings)
        self.model.revert_paths(paths)



if __name__ == '__main__':
    import sys

    from PyQt4 import QtGui

    from cola.models.classic import ClassicModel
    from cola.models.gitrepo import GitRepoModel

    from cola.views import repo

    app = QtGui.QApplication(sys.argv)
    model = ClassicModel()

    view = repo.RepoTreeView()
    view.setModel(GitRepoModel(view, model))
    view.resize(720, 300)

    controller = ClassicController(model, view)

    view.show()
    view.raise_()

    result = app.exec_()
    QtCore.QThreadPool.globalInstance().waitForDone()
    sys.exit(result)
