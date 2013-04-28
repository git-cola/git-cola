from cola.dag.view import DAGView
from cola.dag.model import DAG


def git_dag(model, opts=None, args=None):
    """Return a pre-populated git DAG widget."""
    dag = DAG(model.currentbranch, 1000)
    dag.set_options(opts, args)

    view = DAGView(model, dag, None)
    if dag.ref:
        view.display()
    return view
