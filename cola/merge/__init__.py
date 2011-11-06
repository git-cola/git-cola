from PyQt4 import QtGui

from cola import gitcmds
from cola import qtutils
from cola.merge.controller import MergeController
from cola.merge.model import MergeModel
from cola.merge.view import MergeView


def local_merge():
    """Provides a dialog for merging branches"""
    model = MergeModel()
    view = MergeView(model, qtutils.active_window())
    ctl = MergeController(model, view)
    view.show()
    view.raise_()
    return ctl


def abort_merge():
    """Prompts before aborting a merge in progress
    """
    title = 'Abort Merge...'
    txt = ('Abort merge?\n\n'
           'Aborting the current merge will cause '
           '*ALL* uncommitted changes to be lost.\n\n'
           'Continue with aborting the current merge?')
    info = 'Recovering uncommitted changes will not be possible'
    ok_text = qtutils.tr('Abort Merge...')
    if ok_text.endswith(unichr(0x2026)):
        ok_text = ok_text[:-1]
    elif ok_text.endswith('...'):
        ok_text = ok_text[:-3]
    parent = qtutils.active_window()
    answer = qtutils.confirm(parent, title, txt, info, ok_text)
    if answer:
        gitcmds.abort_merge()


if __name__ == '__main__':
    from cola import app

    app = app.ColaApplication([])
    ctl = local_merge()
    ctl.model.update_status()
    app.exec_()
