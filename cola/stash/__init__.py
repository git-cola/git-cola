from PyQt4 import QtGui

from cola import qtutils
from cola.stash.controller import StashController
from cola.stash.model import StashModel
from cola.stash.view import StashView


def stash(parent=None):
    """Launches a stash dialog using the provided model + view
    """
    if parent is None:
        parent = qtutils.active_window()
    model = StashModel()
    view = StashView(model, parent)
    ctl = StashController(model, view)
    view.show()
    return ctl


if __name__ == '__main__':
    from cola.app import ColaApplication
    import cola

    cola.model().update_status()
    app = ColaApplication([])
    ctl = stash()
    app.exec_()
