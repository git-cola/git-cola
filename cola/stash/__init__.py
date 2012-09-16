from cola import qtutils
from cola.stash.model import StashModel
from cola.stash.view import StashView


def stash():
    """Launches a stash dialog using the provided model + view
    """
    model = StashModel()
    view = StashView(model, qtutils.active_window())
    view.show()
    view.raise_()
    return view


if __name__ == '__main__':
    from cola.app import ColaApplication
    import cola

    cola.model().update_status()
    app = ColaApplication([])
    view = stash()
    app.exec_()
