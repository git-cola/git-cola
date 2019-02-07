from __future__ import division, absolute_import, unicode_literals

import sys

from .. import core
from .. import hidpi
from .. import observable
from .. import utils
from ..cmd import Command


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
THEME = 'cola.theme'
HIDPI = 'cola.hidpi'


class Defaults(object):
    """Read-only class for holding defaults that get overridden"""
    # These should match Git's defaults for git-defined values.
    blame_viewer = 'git gui blame'
    bold_headers = False
    check_conflicts = True
    comment_char = '#'
    display_untracked = True
    diff_context = 5
    difftool = 'xxdiff'
    editor = 'gvim'
    expandtab = False
    history_browser = 'gitk'
    linebreak = True
    maxrecent = 8
    mergetool = difftool
    merge_diffstat = True
    merge_keep_backup = True
    merge_summary = True
    merge_verbosity = 4
    save_window_settings = True
    safe_mode = False
    show_path = True
    sort_bookmarks = True
    spellcheck = False
    tabwidth = 8
    textwidth = 72
    theme = 'default'
    hidpi = hidpi.EChoice.AUTO


def blame_viewer(context):
    default = Defaults.blame_viewer
    return context.cfg.get(BLAME_VIEWER, default=default)


def bold_headers(context):
    return context.cfg.get(BOLD_HEADERS, default=Defaults.bold_headers)


def check_conflicts(context):
    return context.cfg.get(CHECKCONFLICTS, default=Defaults.check_conflicts)


def display_untracked(context):
    return context.cfg.get(DISPLAY_UNTRACKED,
                           default=Defaults.display_untracked)


def editor(context):
    app = context.cfg.get(EDITOR, default=Defaults.editor)
    return _remap_editor(app)


def background_editor(context):
    app = context.cfg.get(BACKGROUND_EDITOR, default=editor(context))
    return _remap_editor(app)


def _remap_editor(app):
    return {'vim': 'gvim -f'}.get(app, app)


def comment_char(context):
    return context.cfg.get(COMMENT_CHAR, default=Defaults.comment_char)


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
        default = Defaults.history_browser
    return default


def history_browser(context):
    default = default_history_browser()
    return context.cfg.get(HISTORY_BROWSER, default=default)


def linebreak(context):
    return context.cfg.get(LINEBREAK, default=Defaults.linebreak)


def maxrecent(context):
    value = Defaults.maxrecent
    if context:
        value = context.cfg.get(MAXRECENT, default=value)
    return value


def spellcheck(context):
    return context.cfg.get(SPELL_CHECK, default=Defaults.spellcheck)


def expandtab(context):
    return context.cfg.get(EXPANDTAB, default=Defaults.expandtab)


def sort_bookmarks(context):
    return context.cfg.get(SORT_BOOKMARKS, default=Defaults.sort_bookmarks)


def tabwidth(context):
    return context.cfg.get(TABWIDTH, default=Defaults.tabwidth)


def textwidth(context):
    return context.cfg.get(TEXTWIDTH, default=Defaults.textwidth)


class PreferencesModel(observable.Observable):
    message_config_updated = 'config_updated'

    def __init__(self, context):
        observable.Observable.__init__(self)
        self.context = context
        self.config = context.cfg

    def set_config(self, source, config, value):
        if source == 'repo':
            self.config.set_repo(config, value)
        else:
            self.config.set_user(config, value)
        message = self.message_config_updated
        self.notify_observers(message, source, config, value)

    def get_config(self, source, config):
        if source == 'repo':
            value = self.config.get_repo(config)
        else:
            value = self.config.get(config)
        return value


class SetConfig(Command):
    """Store a gitconfig value"""

    UNDOABLE = True

    def __init__(self, model, source, config, value):
        self.source = source
        self.config = config
        self.value = value
        self.old_value = None
        self.model = model

    def do(self):
        self.old_value = self.model.get_config(self.source, self.config)
        self.model.set_config(self.source, self.config, self.value)

    def undo(self):
        if self.old_value is None:
            return
        self.model.set_config(self.source, self.config, self.old_value)
