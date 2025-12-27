import sys

from qtpy import QtCore
from qtpy.QtCore import Signal

from .. import core
from .. import hidpi
from .. import utils
from ..cmd import Command


ABBREV = 'core.abbrev'
ASPELL_ENABLED = 'cola.aspell.enabled'
ASPELL_LANG = 'cola.aspell.lang'
AUTOCOMPLETE_PATHS = 'cola.autocompletepaths'
AUTODETECT_PROXY = 'cola.autodetectproxy'
AUTOTEMPLATE = 'cola.autoloadcommittemplate'
BACKGROUND_EDITOR = 'cola.backgroundeditor'
BLAME_VIEWER = 'cola.blameviewer'
BLOCK_CURSOR = 'cola.blockcursor'
BOLD_FONTS = 'cola.boldfonts'
BOLD_HEADERS = 'cola.boldheaders'
CHECK_CONFLICTS = 'cola.checkconflicts'
CHECK_PUBLISHED_COMMITS = 'cola.checkpublishedcommits'
COMMENT_CHAR = 'core.commentchar'
COMMIT_CLEANUP = 'commit.cleanup'
DICTIONARY = 'cola.dictionary'
DIFFCONTEXT = 'gui.diffcontext'
DIFFTOOL = 'diff.tool'
DISPLAY_UNTRACKED = 'gui.displayuntracked'
EDITOR = 'gui.editor'
ENABLE_GRAVATAR = 'cola.gravatar'
ENABLE_POPUPS = 'cola.enablepopups'
EXPANDTAB = 'cola.expandtab'
FONTDIFF = 'cola.fontdiff'
FONTSIZE = 'cola.fontsize'
HIDPI = 'cola.hidpi'
HISTORY_BROWSER = 'gui.historybrowser'
HTTP_PROXY = 'http.proxy'
ICON_THEME = 'cola.icontheme'
INOTIFY = 'cola.inotify'
INOTIFY_DELAY = 'cola.inotifydelay'
NOTIFY_ON_PUSH = 'cola.notifyonpush'
LINEBREAK = 'cola.linebreak'
LOGDATE = 'cola.logdate'
MAXRECENT = 'cola.maxrecent'
MERGE_DIFFSTAT = 'merge.diffstat'
MERGE_KEEPBACKUP = 'merge.keepbackup'
MERGE_SUMMARY = 'merge.summary'
MERGE_VERBOSITY = 'merge.verbosity'
MERGETOOL = 'merge.tool'
MOUSE_ZOOM = 'cola.mousezoom'
PATCHES_DIRECTORY = 'cola.patchesdirectory'
PULL_REBASE = 'pull.rebase'
REBASE_UPDATE_REFS = 'rebase.updaterefs'
REFRESH_ON_FOCUS = 'cola.refreshonfocus'
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
UPDATE_INDEX = 'cola.updateindex'
VERBOSITY = 'cola.verbosity'


class DateFormat:
    DEFAULT = 'default'
    RELATIVE = 'relative'
    LOCAL = 'local'
    ISO = 'iso8601'
    ISO_STRICT = 'iso8601-strict'
    RFC = 'rfc2822'
    SHORT = 'short'
    RAW = 'raw'
    HUMAN = 'human'
    UNIX = 'unix'
    FORMAT = 'format:'

    @classmethod
    def is_custom(cls, value):
        """Is the log format a custom log format?"""
        return value.startswith(cls.FORMAT)

    @classmethod
    def get_custom_format(cls, value):
        """Return the custom format in a format:<...> string"""
        return value[len(cls.FORMAT) :]


def date_formats():
    """Return valid values for git config cola.logdate"""
    return [
        DateFormat.DEFAULT,
        DateFormat.RELATIVE,
        DateFormat.LOCAL,
        DateFormat.ISO,
        DateFormat.ISO_STRICT,
        DateFormat.RFC,
        DateFormat.SHORT,
        DateFormat.RAW,
        DateFormat.HUMAN,
        DateFormat.UNIX,
    ]


class Verbosity:
    """Verbosity levels"""

    SILENT = 0
    SIMPLE_COMMANDS = 1


def commit_cleanup_modes():
    """Return valid values for the git config commit.cleanup"""
    return [
        'default',
        'whitespace',
        'strip',
        'scissors',
        'verbatim',
    ]


class Defaults:
    """Read-only class for holding defaults that get overridden"""

    # These should match Git's defaults for git-defined values.
    abbrev = 12
    aspell_enabled = False
    autotemplate = False
    autodetect_proxy = True
    background_editor = ''
    blame_viewer = 'git gui blame'
    block_cursor = True
    bold_fonts = False
    bold_headers = False
    check_conflicts = True
    check_published_commits = True
    comment_char = '#'
    commit_cleanup = 'default'
    display_untracked = True
    diff_context = 5
    difftool = 'xxdiff'
    editor = 'gvim'
    enable_gravatar = True
    enable_popups = False
    expandtab = False
    history_browser = 'gitk'
    http_proxy = ''
    icon_theme = 'default'
    inotify = True
    inotify_delay = 888
    notifyonpush = False
    linebreak = True
    maxrecent = 8
    mergetool = difftool
    merge_diffstat = True
    merge_keep_backup = True
    merge_summary = True
    merge_verbosity = 2
    mouse_zoom = True
    rebase_update_refs = False
    refresh_on_focus = False
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
    patches_directory = 'patches'
    status_indent = False
    status_show_totals = False
    logdate = DateFormat.DEFAULT
    update_index = True
    verbosity = 0


def abbrev(context):
    """Return the configured length for shortening commit IDs"""
    default = Defaults.abbrev
    value = context.cfg.get(ABBREV, default=default)
    if value == 'no':
        result = context.model.oid_len
    else:
        try:
            result = max(4, int(value))
        except ValueError:
            result = default
    return result


def spelling_dictionaries(context):
    """Return the list of additional spelling dictionaries"""
    return context.cfg.get_all(DICTIONARY)


def aspell_enabled(context):
    """Return True when aspell should be used as the spelling dictionary source"""
    return context.cfg.get(ASPELL_ENABLED, default=Defaults.aspell_enabled)


def aspell_languages(context):
    """Return the currently configured list of aspell languages"""
    return context.cfg.get_all(ASPELL_LANG)


def autodetect_proxy(context):
    """Return True when proxy settings should be automatically configured"""
    return context.cfg.get(AUTODETECT_PROXY, default=Defaults.autodetect_proxy)


def blame_viewer(context):
    """Return the configured "blame" viewer"""
    default = Defaults.blame_viewer
    return context.cfg.get(BLAME_VIEWER, default=default)


def block_cursor(context):
    """Should we display a block cursor in diff editors?"""
    return context.cfg.get(BLOCK_CURSOR, default=Defaults.block_cursor)


def bold_fonts(context):
    """Should we bold all fonts?"""
    return context.cfg.get(BOLD_FONTS, default=Defaults.bold_fonts)


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
    app = context.cfg.get(EDITOR, default=fallback_editor())
    return _remap_editor(app)


def background_editor(context):
    """Return the configured non-blocking background editor"""
    app = context.cfg.get(BACKGROUND_EDITOR, default=editor(context))
    return _remap_editor(app)


def enable_popups(context):
    """Should popups be used instead of notifications/logs?"""
    return context.cfg.get(ENABLE_POPUPS, default=Defaults.enable_popups)


def fallback_editor():
    """Return a fallback editor for cases where one is not configured

    GIT_VISUAL and VISUAL are consulted before GIT_EDITOR and EDITOR to allow
    configuring a visual editor for Git Cola using $GIT_VISUAL and an alternative
    editor for the Git CLI.
    """
    editor_variables = (
        'GIT_VISUAL',
        'VISUAL',
        'GIT_EDITOR',
        'EDITOR',
    )
    for env in editor_variables:
        env_editor = core.getenv(env)
        if env_editor:
            return env_editor

    return Defaults.editor


def _remap_editor(app):
    """Remap a configured editor into a visual editor name"""
    # We do this for vim users because this configuration is convenient for new users.
    return {
        'vim': 'gvim -f',
        'nvim': 'nvim-qt --nofork',
    }.get(app, app)


def comment_char(context):
    """Return the configured git commit comment character"""
    return context.cfg.get(COMMENT_CHAR, default=Defaults.comment_char)


def commit_cleanup(context):
    """Return the configured git commit cleanup mode"""
    return context.cfg.get(COMMIT_CLEANUP, default=Defaults.commit_cleanup)


def enable_gravatar(context):
    """Is gravatar enabled?"""
    return context.cfg.get(ENABLE_GRAVATAR, default=Defaults.enable_gravatar)


def default_history_browser():
    """Return the default history browser (e.g. git-dag, gitk)"""
    if utils.is_win32():
        # On Windows, a sensible default is "python git-cola dag"
        # which is different than `gitk` below, but is preferred
        # because we don't have to guess paths.
        git_cola = sys.argv[0].replace('\\', '/')
        python = sys.executable.replace('\\', '/')
        argv = core.prep_for_subprocess([python, git_cola, 'dag'])
        default = core.list2cmdline(argv)
    else:
        # The `gitk` script can be launched as-is on unix
        default = Defaults.history_browser
    return default


def history_browser(context):
    """Return the configured history browser"""
    default = default_history_browser()
    return context.cfg.get(HISTORY_BROWSER, default=default)


def http_proxy(context):
    """Return the configured http proxy"""
    return context.cfg.get(HTTP_PROXY, default=Defaults.http_proxy)


def notify_on_push(context):
    """Return whether to notify upon push or not"""
    default = Defaults.notifyonpush
    return context.cfg.get(NOTIFY_ON_PUSH, default=default)


def linebreak(context):
    """Should we word-wrap lines in the commit message editor?"""
    return context.cfg.get(LINEBREAK, default=Defaults.linebreak)


def logdate(context):
    """Return the configured log date format"""
    return context.cfg.get(LOGDATE, default=Defaults.logdate)


def maxrecent(context):
    """Return the configured maximum number of Recent Repositories"""
    value = Defaults.maxrecent
    if context:
        value = context.cfg.get(MAXRECENT, default=value)
    return value


def mouse_zoom(context):
    """Should we zoom text when using Ctrl + MouseWheel scroll"""
    return context.cfg.get(MOUSE_ZOOM, default=Defaults.mouse_zoom)


def inotify_delay(context):
    """How long to wait, in milliseconds, between inotify events"""
    return context.cfg.get(INOTIFY_DELAY, default=Defaults.inotify_delay)


def spellcheck(context):
    """Should we spellcheck commit messages?"""
    return context.cfg.get(SPELL_CHECK, default=Defaults.spellcheck)


def expandtab(context):
    """Should we expand tabs in commit messages?"""
    return context.cfg.get(EXPANDTAB, default=Defaults.expandtab)


def patches_directory(context):
    """Return the patches output directory"""
    return context.cfg.get(PATCHES_DIRECTORY, default=Defaults.patches_directory)


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


def verbosity(context):
    """Return the console verbosity level"""
    return context.cfg.get(VERBOSITY, default=Defaults.verbosity)


def verbose_simple_commands(context):
    """Is the verbosity level set to log commands?"""
    return verbosity(context) >= Verbosity.SIMPLE_COMMANDS


class PreferencesModel(QtCore.QObject):
    """Interact with repo-local and user-global git config preferences"""

    config_updated = Signal(str, str, object)

    def __init__(self, context):
        super().__init__()
        self.context = context
        self.config = context.cfg

    def set_config(self, source, config, value):
        """Set a configuration value"""
        if source == 'local':
            self.config.set_repo(config, value)
        else:
            self.config.set_user(config, value)
        self.config_updated.emit(source, config, value)

    def get_config(self, source, config):
        """Get a configured value"""
        if source == 'local':
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


class RemoveDictionary(Command):
    """Remove spelling dictionary entries"""

    UNDOABLE = True

    def __init__(self, context, values):
        self.context = context
        self.values = values

    def do(self):
        """Remove spelling dictionary entries"""
        for value in self.values:
            self.context.git.config(
                'unset',
                '--global',
                '--all',
                '--fixed-value',
                '--value',
                value,
                DICTIONARY,
            )
        self.context.cfg.reset()

    def undo(self):
        """Undo removal of spelling dictionary entries"""
        add_command = AddDictionary(self.context, self.values)
        add_command.do()


class AddDictionary(Command):
    """Add spelling dictionary entries"""

    UNDOABLE = True

    def __init__(self, context, values):
        self.context = context
        self.values = values

    def do(self):
        """Add spelling dictionary entries"""
        for value in self.values:
            self.context.git.config('--global', '--add', DICTIONARY, value)
        self.context.cfg.reset()

    def undo(self):
        """Remove spelling dictionary entries"""
        remove_command = RemoveDictionary(self.context, self.values)
        remove_command.do()
