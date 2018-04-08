from __future__ import division, absolute_import, unicode_literals

import sys

from .. import core
from .. import gitcfg
from .. import observable
from .. import utils


BACKGROUND_EDITOR = 'cola.backgroundeditor'
BLAME_VIEWER = 'cola.blameviewer'
BOLD_HEADERS = 'cola.boldheaders'
CHECKCONFLICTS = 'cola.checkconflicts'
COMMENT_CHAR = 'core.commentchar'
DIFFCONTEXT = 'gui.diffcontext'
DIFFTOOL = 'diff.tool'
DISPLAY_UNTRACKED = 'gui.displayuntracked'
EDITOR = 'gui.editor'
FONTDIFF = 'cola.fontdiff'
HISTORY_BROWSER = 'gui.historybrowser'
LINEBREAK = 'cola.linebreak'
MAXRECENT = 'cola.maxrecent'
MERGE_DIFFSTAT = 'merge.diffstat'
MERGE_KEEPBACKUP = 'merge.keepbackup'
MERGE_SUMMARY = 'merge.summary'
MERGE_VERBOSITY = 'merge.verbosity'
MERGETOOL = 'merge.tool'
EXPANDTAB = 'cola.expandtab'
SAVEWINDOWSETTINGS = 'cola.savewindowsettings'
SORT_BOOKMARKS = 'cola.sortbookmarks'
TABWIDTH = 'cola.tabwidth'
TEXTWIDTH = 'cola.textwidth'
USER_EMAIL = 'user.email'
USER_NAME = 'user.name'
SAFE_MODE = 'cola.safemode'
SHOW_PATH = 'cola.showpath'
SPELL_CHECK = 'cola.spellcheck'


def default_blame_viewer():
    return 'git gui blame'


def blame_viewer():
    default = default_blame_viewer()
    return gitcfg.current().get(BLAME_VIEWER, default=default)


def bold_headers():
    return gitcfg.current().get(BOLD_HEADERS, default=False)


def check_conflicts():
    return gitcfg.current().get(CHECKCONFLICTS, default=True)


def display_untracked():
    return gitcfg.current().get(DISPLAY_UNTRACKED, default=True)


def editor():
    app = gitcfg.current().get(EDITOR, default='gvim')
    return _remap_editor(app)


def background_editor():
    app = gitcfg.current().get(BACKGROUND_EDITOR, default=editor())
    return _remap_editor(app)


def _remap_editor(app):
    return {'vim': 'gvim -f'}.get(app, app)


def comment_char():
    return gitcfg.current().get(COMMENT_CHAR, default='#')


def default_history_browser():
    if utils.is_win32():
        # On Windows, a sensible default is "python git-cola dag"
        # which is different than `gitk` below, but is preferred
        # because we don't have to guess paths.
        git_cola = sys.argv[0].replace('\\', '/')
        python = sys.executable.replace('\\', '/')
        cwd = core.getcwd().replace('\\', '/')
        argv = [python, git_cola, 'dag', '--repo', cwd]
        argv = core.prep_for_subprocess(argv)
        default = core.list2cmdline(argv)
    else:
        # The `gitk` script can be launched as-is on unix
        default = 'gitk'
    return default


def history_browser():
    default = default_history_browser()
    return gitcfg.current().get(HISTORY_BROWSER, default=default)


def linebreak():
    return gitcfg.current().get(LINEBREAK, default=True)


def maxrecent():
    return gitcfg.current().get(MAXRECENT, default=8)


def spellcheck():
    return gitcfg.current().get(SPELL_CHECK, default=False)


def expandtab():
    return gitcfg.current().get(EXPANDTAB, default=False)


def sort_bookmarks():
    return gitcfg.current().get(SORT_BOOKMARKS, default=True)


def tabwidth():
    return gitcfg.current().get(TABWIDTH, default=8)


def textwidth():
    return gitcfg.current().get(TEXTWIDTH, default=72)


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
