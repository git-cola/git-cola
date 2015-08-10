from __future__ import division, absolute_import, unicode_literals

import sys
import subprocess

from cola import core
from cola import gitcfg
from cola import observable
from cola import utils


CHECKCONFLICTS = 'cola.checkconflicts'
COMMENT_CHAR = 'core.commentchar'
DIFFCONTEXT = 'gui.diffcontext'
DIFFTOOL = 'diff.tool'
DISPLAY_UNTRACKED = 'gui.displayuntracked'
EDITOR = 'gui.editor'
FONTDIFF = 'cola.fontdiff'
HISTORY_BROWSER = 'gui.historybrowser'
LINEBREAK = 'cola.linebreak'
MERGE_DIFFSTAT = 'merge.diffstat'
MERGE_KEEPBACKUP = 'merge.keepbackup'
MERGE_SUMMARY = 'merge.summary'
MERGE_VERBOSITY = 'merge.verbosity'
MERGETOOL = 'merge.tool'
SAVEWINDOWSETTINGS = 'cola.savewindowsettings'
SORT_BOOKMARKS = 'cola.sortbookmarks'
TABWIDTH = 'cola.tabwidth'
TEXTWIDTH = 'cola.textwidth'
USER_EMAIL = 'user.email'
USER_NAME = 'user.name'


def check_conflicts():
    return gitcfg.current().get(CHECKCONFLICTS, True)


def display_untracked():
    return gitcfg.current().get(DISPLAY_UNTRACKED, True)


def editor():
    app = gitcfg.current().get(EDITOR, 'gvim')
    return {'vim': 'gvim -f'}.get(app, app)


def comment_char():
    return gitcfg.current().get(COMMENT_CHAR, '#')


def default_history_browser():
    if utils.is_win32():
        # On Windows, a sensible default is "python git-cola dag"
        # which is different than `gitk` below, but is preferred
        # because we don't have to guess paths.
        git_cola = sys.argv[0]
        python = sys.executable
        argv = [python, git_cola, 'dag']
        argv = core.prep_for_subprocess(argv)
        default = core.decode(subprocess.list2cmdline(argv))
    else:
        # The `gitk` script can be launched as-is on unix
        default = 'gitk'
    return default


def history_browser():
    default = default_history_browser()
    return gitcfg.current().get(HISTORY_BROWSER, default)


def linebreak():
    return gitcfg.current().get(LINEBREAK, True)


def sort_bookmarks():
    return gitcfg.current().get(SORT_BOOKMARKS, True)


def tabwidth():
    return gitcfg.current().get(TABWIDTH, 8)


def textwidth():
    return gitcfg.current().get(TEXTWIDTH, 72)



class PreferencesModel(observable.Observable):
    message_config_updated = 'config_updated'

    def __init__(self):
        observable.Observable.__init__(self)
        self.config = gitcfg.current()

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
