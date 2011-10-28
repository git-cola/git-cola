import os
import sys

from PyQt4 import QtCore

if __name__ == '__main__':
    # Find the source tree
    src = os.path.join(os.path.dirname(__file__), '..', '..')
    sys.path.insert(1, os.path.join(os.path.abspath(src), 'thirdparty'))
    sys.path.insert(1, os.path.abspath(src))

from cola.dag.view import DAGView
from cola.dag.model import DAG
from cola.dag.controller import DAGController


def git_dag(model, parent):
    """Return a pre-populated git DAG widget."""
    dag = DAG(model.currentbranch, 1000)
    view = DAGView(model, dag, parent=parent)
    ctl = DAGController(dag, view)
    view.show()
    view.raise_()
    if dag.ref:
        view.thread.start(QtCore.QThread.LowPriority)
    return ctl


if __name__ == "__main__":
    import cola
    from cola import app

    model = cola.model()
    model.use_worktree(os.getcwd())
    model.update_status()

    app = app.ColaApplication(sys.argv)
    ctl = git_dag(model, app.activeWindow())
    sys.exit(app.exec_())
