import os
import sys

if __name__ == '__main__':
    # Find the source tree
    src = os.path.join(os.path.dirname(__file__), '..', '..')
    sys.path.insert(1, os.path.abspath(src))

from cola.dag.view import DAGView
from cola.dag.model import DAG


def git_dag(model, opts=None, args=None):
    """Return a pre-populated git DAG widget."""
    dag = DAG(model.currentbranch, 1000)
    dag.set_options(opts, args)

    view = DAGView(model, dag, None)
    view.show()
    if dag.ref:
        view.display()
    return view
