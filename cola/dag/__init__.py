import os
import sys

from PyQt4 import QtCore

if __name__ == '__main__':
    # Find the source tree
    src = os.path.join(os.path.dirname(__file__), '..', '..')
    sys.path.insert(1, os.path.join(os.path.abspath(src), 'thirdparty'))
    sys.path.insert(1, os.path.abspath(src))

from cola import guicmds
from cola.dag.view import GitDAGWidget
from cola.dag.model import DAG
from cola.dag.controller import GitDAGController


def git_dag(model, parent, standalone=False):
    """Return a pre-populated git DAG widget."""
    model = DAG(model.currentbranch, 1000)
    view = GitDAGWidget(model, parent=parent)
    ctl = GitDAGController(model, view)
    if standalone:
        guicmds.install_command_wrapper(view)
    view.resize_to_desktop()
    view.show()
    view.raise_()
    view.thread.start(QtCore.QThread.LowPriority)
    return ctl


if __name__ == "__main__":
    import cola
    from cola import app

    model = cola.model()
    model.use_worktree(os.getcwd())
    model.update_status()

    app = app.ColaApplication(sys.argv)
    ctl = git_dag(model, app.activeWindow(), standalone=True)
    sys.exit(app.exec_())
