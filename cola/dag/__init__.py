from cola.dag.view import DAGView
from cola.dag.model import DAG


def git_dag(model, args=None):
    """Return a pre-populated git DAG widget."""
    dag = DAG(model.currentbranch, 1000)
    dag.set_arguments(args)

    view = DAGView(model, dag, None)
    if dag.ref:
        view.display()
    return view
