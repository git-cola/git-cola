from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

import cola
import cola.utils
import cola.difftool

from cola import gitcmds
from cola import qtutils
from cola import signals
from cola.controllers.selectcommits import select_commits
from cola.classic.view import RepoDialog
from cola.classic.model import GitRepoModel
from cola.classic.model import GitRepoEntryManager
from cola.compat import set


def widget(parent=None, update=True):
    """Return a widget for immediate use."""
    view = RepoDialog(parent=parent, update=update)
    view.tree.setModel(GitRepoModel(view.tree))
    controller = ClassicController(view.tree)
    return view


def cola_classic(parent=None, update=True):
    """Launch a new cola classic session."""
    view = widget(parent=parent, update=update)
    if not parent:
        qtutils.center_on_screen(view)
    view.show()
    return view


class ClassicController(QtCore.QObject):
    def __init__(self, view=None):
        QtCore.QObject.__init__(self, view)
        self.model = cola.model()
        self.view = view
        self.updated = set()
        self.connect(view, SIGNAL('history(QStringList)'),
                     self.view_history)
        self.connect(view, SIGNAL('expanded(QModelIndex)'),
                     self.query_model)
        self.connect(view, SIGNAL('difftool_predecessor'),
                     self.difftool_predecessor)

    def view_history(self, entries):
        """Launch the configured history browser path-limited to entries."""
        entries = map(unicode, entries)
        cola.notifier().broadcast(signals.visualize_paths, entries)

    def query_model(self, model_index):
        """Update information about a directory as it is expanded."""
        item = self.view.item_from_index(model_index)
        path = item.path
        if path in self.updated:
            return
        self.updated.add(path)
        GitRepoEntryManager.entry(path).update()
        entry = GitRepoEntryManager.entry
        for row in xrange(item.rowCount()):
            path = item.child(row, 0).path
            entry(path).update()

    def difftool_predecessor(self, paths):
        """Prompt for an older commit and launch difftool against it."""
        args = ['--'] + paths
        revs, summaries = gitcmds.log_helper(all=True, extra_args=args)
        commits = select_commits('Select Previous Version',
                                 revs, summaries, multiselect=False)
        if not commits:
            return
        commit = commits[0]
        cola.difftool.launch([commit, '--'] + paths)


if __name__ == '__main__':
    import sys

    app = QtGui.QApplication(sys.argv)
    cola_classic()
    result = app.exec_()
    QtCore.QThreadPool.globalInstance().waitForDone()
    sys.exit(result)
