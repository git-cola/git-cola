from __future__ import absolute_import, division, print_function, unicode_literals
import sys

from .. import core
from .. import hidpi
from .. import observable
from .. import utils
from ..cmd import Command


AUTOCOMPLETE_PATHS = 'cola.autocompletepaths'
AUTOTEMPLATE = 'cola.autoloadcommittemplate'
BACKGROUND_EDITOR = 'cola.backgroundeditor'
BLAME_VIEWER = 'cola.blameviewer'
BOLD_HEADERS = 'cola.boldheaders'
CHECK_CONFLICTS = 'cola.checkconflicts'
CHECK_PUBLISHED_COMMITS = 'cola.checkpublishedcommits'
COMMENT_CHAR = 'core.commentchar'
DIFFCONTEXT = 'gui.diffcontext'
DIFFTOOL = 'diff.tool'
DISPLAY_UNTRACKED = 'gui.displayuntracked'
EDITOR = 'gui.editor'
EXPANDTAB = 'cola.expandtab'
FONTDIFF = 'cola.fontdiff'
HIDPI = 'cola.hidpi'
HISTORY_BROWSER = 'gui.historybrowser'
ICON_THEME = 'cola.icontheme'
LINEBREAK = 'cola.linebreak'
MAXRECENT = 'cola.maxrecent'
MERGE_DIFFSTAT = 'merge.diffstat'
MERGE_KEEPBACKUP = 'merge.keepbackup'
MERGE_SUMMARY = 'merge.summary'
MERGE_VERBOSITY = 'merge.verbosity'
MERGETOOL = 'merge.tool'
RESIZE_BROWSER_COLUMNS = 'cola.resizebrowsercolumns'
SAFE_MODE = 'cola.safemode'
SAVEWINDOWSETTINGS = 'cola.savewindowsettings'
SHOW_PATH = 'cola.showpath'
SORT_BOOKMARKS = 'cola.sortbookmarks'
SPELL_CHECK = 'cola.spellcheck'
STATUS_INDENT = 'cola.statusindent'
STATUS_SHOW_TOTALS = 'cola.statusshowtotals'
THEME = 'cola.theme'
TABWIDTH = 'cola.tabwidth'
TEXTWIDTH = 'cola.textwidth'
USER_EMAIL = 'user.email'
USER_NAME = 'user.name'


class Defaults(object):
    """Read-only class for holding defaults that get overridden"""

    # These should match Git's defaults for git-defined values.
    autotemplate = False
    blame_viewer = 'git gui blame'
    bold_headers = False
    check_conflicts = True
    check_published_commits = True
    comment_char = '#'
    display_untracked = True
    diff_context = 5
    difftool = 'xxdiff'
    editor = 'gvim'
    expandtab = False
    history_browser = 'gitk'
    icon_theme = 'default'
    linebreak = True
    maxrecent = 8
    mergetool = difftool
    merge_diffstat = True
    merge_keep_backup = True
    merge_summary = True
    merge_verbosity = 2
    resize_browser_columns = False
    save_window_settings = True
    safe_mode = False
    autocomplete_paths = True
    show_path = True
    sort_bookmarks = True
    spellcheck = False
    tabwidth = 8
    textwidth = 72
    theme = 'default'
    hidpi = hidpi.Option.AUTO
    status_indent = False
    status_show_totals = False


def blame_viewer(context):
    """Return the configured "blame" viewer"""
    default = Defaults.blame_viewer
    return context.cfg.get(BLAME_VIEWER, default=default)


def bold_headers(context):
    """Should we bold the Status column headers?"""
    return context.cfg.get(BOLD_HEADERS, default=Defaults.bold_headers)


def check_conflicts(context):
    """Should we check for merge conflict markers in unmerged files?"""
    return context.cfg.get(CHECK_CONFLICTS, default=Defaults.check_conflicts)


def check_published_commits(context):
    """Should we check for published commits when amending?"""
    return context.cfg.get(
        CHECK_PUBLISHED_COMMITS, default=Defaults.check_published_commits
    )


def display_untracked(context):
    """Should we display untracked files?"""
    return context.cfg.get(DISPLAY_UNTRACKED, default=Defaults.display_untracked)


def editor(context):
    """Return the configured editor"""
    app = context.cfg.get(EDITOR, default=Defaults.editor)
    return _remap_editor(app)


def background_editor(context):
    """Return the configured non-blocking background editor"""
    app = context.cfg.get(BACKGROUND_EDITOR, default=editor(context))
    return _remap_editor(app)


def _remap_editor(app):
    """Remap a configured editorinto a visual editor name"""
    # We do this for vim users because this configuration is convenient.
    return {'vim': 'gvim -f'}.get(app, app)


def comment_char(context):
    """Return the configured git commit comment character"""
    return context.cfg.get(COMMENT_CHAR, default=Defaults.comment_char)


def default_history_browser():
    """Return the default history browser (e.g. git-dag, gitk)"""
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
    """Return the configured history browser"""
    default = default_history_browser()
    return context.cfg.get(HISTORY_BROWSER, default=default)


def linebreak(context):
    """Should we word-wrap lines in the commit message editor?"""
    return context.cfg.get(LINEBREAK, default=Defaults.linebreak)


def maxrecent(context):
    """Return the configured maximum number of Recent Repositories"""
    value = Defaults.maxrecent
    if context:
        value = context.cfg.get(MAXRECENT, default=value)
    return value


def spellcheck(context):
    """Should we spellcheck commit messages?"""
    return context.cfg.get(SPELL_CHECK, default=Defaults.spellcheck)


def expandtab(context):
    """Should we expand tabs in commit messages?"""
    return context.cfg.get(EXPANDTAB, default=Defaults.expandtab)


def sort_bookmarks(context):
    """Should we sort bookmarks by name?"""
    return context.cfg.get(SORT_BOOKMARKS, default=Defaults.sort_bookmarks)


def tabwidth(context):
    """Return the configured tab width in the commit message editor"""
    return context.cfg.get(TABWIDTH, default=Defaults.tabwidth)


def textwidth(context):
    """Return the configured text width for word wrapping commit messages"""
    return context.cfg.get(TEXTWIDTH, default=Defaults.textwidth)


def status_indent(context):
    """Should we indent items in the status widget?"""
    return context.cfg.get(STATUS_INDENT, default=Defaults.status_indent)


def status_show_totals(context):
    """Should we display count totals in the status widget headers?"""
    return context.cfg.get(STATUS_SHOW_TOTALS, default=Defaults.status_show_totals)


class PreferencesModel(observable.Observable):
    """Interact with repo-local and user-global git config preferences"""

    message_config_updated = 'config_updated'

    def __init__(self, context):
        observable.Observable.__init__(self)
        self.context = context
        self.config = context.cfg

    def set_config(self, source, config, value):
        """Set a configuration value"""
        if source == 'repo':
            self.config.set_repo(config, value)
        else:
            self.config.set_user(config, value)
        message = self.message_config_updated
        self.notify_observers(message, source, config, value)

    def get_config(self, source, config):
        """Get a configured value"""
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
        """Modify the model and store the updated configuration"""
        self.old_value = self.model.get_config(self.source, self.config)
        self.model.set_config(self.source, self.config, self.value)

    def undo(self):
        """Restore the configuration change to its original value"""
        if self.old_value is None:
            return
        self.model.set_config(self.source, self.config, self.old_value)
