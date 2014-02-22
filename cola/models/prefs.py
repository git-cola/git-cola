from __future__ import division, absolute_import

from cola import gitcfg
from cola import observable


FONTDIFF = 'cola.fontdiff'
DIFFCONTEXT = 'gui.diffcontext'
DIFFTOOL = 'diff.tool'
DISPLAY_UNTRACKED = 'gui.displayuntracked'
EDITOR = 'gui.editor'
LINEBREAK = 'cola.linebreak'
TABWIDTH = 'cola.tabwidth'
TEXTWIDTH = 'cola.textwidth'
HISTORY_BROWSER = 'gui.historybrowser'
MERGE_SUMMARY = 'merge.summary'
MERGE_DIFFSTAT = 'merge.diffstat'
MERGE_KEEPBACKUP = 'merge.keepbackup'
MERGE_VERBOSITY = 'merge.verbosity'
MERGETOOL = 'merge.tool'
SAVEWINDOWSETTINGS = 'cola.savewindowsettings'
USER_EMAIL = 'user.email'
USER_NAME = 'user.name'



def config():
    return gitcfg.instance()


def display_untracked():
    return config().get(DISPLAY_UNTRACKED, True)


def editor():
    app = config().get(EDITOR, 'gvim')
    return {'vim': 'gvim -f'}.get(app, app)


def history_browser():
    return config().get(HISTORY_BROWSER, 'gitk')


def linebreak():
    return config().get(LINEBREAK, True)


def tabwidth():
    return config().get(TABWIDTH, 8)


def textwidth():
    return config().get(TEXTWIDTH, 72)



class PreferencesModel(observable.Observable):
    message_config_updated = 'config_updated'

    def __init__(self):
        observable.Observable.__init__(self)
        self.config = gitcfg.instance()

    def set_config(self, source, config, value):
        if source == 'repo':
            self.config.set_repo(config, value)
        else:
            self.config.set_user(config, value)
        message = self.message_config_updated
        self.notify_observers(message, source, config, value)

    def get_config(self, source, config):
        if source == 'repo':
            return self.config.get_repo(config)
        else:
            return self.config.get(config)


class SetConfig(object):

    def __init__(self, model, source, config, value):
        self.source = source
        self.config = config
        self.value = value
        self.old_value = None
        self.model = model

    def is_undoable(self):
        return True

    def do(self):
        self.old_value = self.model.get_config(self.source, self.config)
        self.model.set_config(self.source, self.config, self.value)

    def undo(self):
        if self.old_value is None:
            return
        self.model.set_config(self.source, self.config, self.old_value)
