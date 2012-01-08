import os
import sys

from PyQt4 import QtCore

if __name__ == '__main__':
    # Find the source tree
    src = os.path.join(os.path.dirname(__file__), '..', '..')
    sys.path.insert(1, os.path.abspath(src))

from cola.dag.view import DAGView
from cola.dag.model import DAG
from cola.dag.controller import DAGController


def git_dag(model, opts=None, args=None):
    """Return a pre-populated git DAG widget."""
    dag = DAG(model.currentbranch, 1000)
    dag.set_options(opts, args)

    view = DAGView(model, dag, None)
    ctl = DAGController(dag, view)
    view.show()
    if dag.ref:
        view.display()
    return ctl
