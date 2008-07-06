import os

from cola import utils
from cola import qtutils
from cola.qobserver import QObserver
from cola.views import StashView

def stash(model, parent):
    model = model.clone()
    model.create( stash_list=[], stash_revids=[] )
    view = StashView(parent)
    ctl = StashController(model, view)
    view.show()

class StashController(QObserver):
    def init (self, model, view):
        self.add_observables('stash_list')
        self.add_callbacks(button_stash_show  = self.stash_show,
                           button_stash_apply = self.stash_apply,
                           button_stash_drop  = self.stash_drop,
                           button_stash_clear = self.stash_clear,
                           button_stash_save  = self.stash_save)
        self.update_model()

    def update_model(self):
        self.model.set_stash_list(self.model.parse_stash_list())
        self.model.set_stash_revids(self.model.parse_stash_list(revids=True))
        self.refresh_view()

    def get_selected_stash(self):
        list_widget = self.view.stash_list
        stash_list = self.model.get_stash_revids()
        return qtutils.get_selected_item(list_widget, stash_list)

    def stash_save(self):
        if not qtutils.question(self.view,
                                self.tr('Stash Changes?'),
                                self.tr('This will stash your current '
                                        'changes away for later use.\n'
                                        'Continue?')):
            return

        stash_name, ok = qtutils.input(self.tr('Enter a name for this stash'))
        if not ok:
            return
        while stash_name in self.model.get_stash_list():
            qtutils.information(self.tr("Oops!"),
                                self.tr('That name already exists.  '
                                        'Please enter another name.'))
            stash_name, ok = qtutils.input(self.tr("Enter a name for this stash"))
            if not ok:
                return

        if not stash_name:
            return

        # Sanitize our input, just in case
        stash_name = utils.sanitize_input(stash_name)
        qtutils.log(self.model.stash('save', stash_name),
                    quiet=False,
                    doraise=True)
        self.view.accept()

    def stash_show(self):
        """Shows the current stash in the main view."""
        selection = self.get_selected_stash()
        if not selection:
            return
        diffstat = self.model.stash('show', selection)
        diff = self.model.stash('show', '-p', selection)
        self.view.parent_view.display('%s\n\n%s' % (diffstat, diff))

    def stash_apply(self):
        selection = self.get_selected_stash()
        if not selection:
            return
        (status, stdout, stderr) = self.model.stash('pop', selection,
                                                    with_extended_output=True)
        qtutils.log(stdout + stderr,
                    quiet=False,
                    doraise=True)
        self.view.accept()

    def stash_drop(self):
        selection = self.get_selected_stash()
        if not selection:
            return
        if not qtutils.question(self.view,
                                self.tr('Drop Stash?'),
                                self.tr('This will permanently remove the '
                                        'selected stash.\n'
                                        'Recovering these changes may not '
                                        'be possible.\n\n'
                                        'Continue?')):
            return
        qtutils.log(self.model.stash('drop', selection),
                    quiet=False,
                    doraise=True)
        self.update_model()

    def stash_clear(self):
        if not qtutils.question(self.view,
                                self.tr('Drop All Stashes?'),
                                self.tr('This will permanently remove '
                                        'ALL stashed changes.\n'
                                        'Recovering these changes may not '
                                        'be possible.\n\n'
                                        'Continue?')):
            return
        self.model.stash('clear'),
        self.update_model()
