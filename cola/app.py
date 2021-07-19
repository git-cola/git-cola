"""Provides the main() routine and ColaApplication"""
# pylint: disable=unused-import
from __future__ import absolute_import, division, print_function, unicode_literals
from functools import partial
import argparse
import os
import signal
import sys
import time

__copyright__ = """
Copyright (C) 2007-2017 David Aguilar and contributors
"""

try:
    from qtpy import QtCore
except ImportError:
    sys.stderr.write(
        """
You do not seem to have PyQt5, PySide, or PyQt4 installed.
Please install it before using git-cola, e.g. on a Debian/Ubutnu system:

    sudo apt-get install python-pyqt5 python-pyqt5.qtwebkit

"""
    )
    sys.exit(1)

from qtpy import QtWidgets
from qtpy.QtCore import Qt

try:
    # Qt 5.12 / PyQt 5.13 is unable to use QtWebEngineWidgets unless it is
    # imported before QApplication is constructed.
    from qtpy import QtWebEngineWidgets  # noqa
except ImportError:
    # QtWebEngineWidgets / QtWebKit is not available -- no big deal.
    pass

# Import cola modules
from .i18n import N_
from .interaction import Interaction
from .models import main
from .models import selection
from .widgets import cfgactions
from .widgets import standard
from .widgets import startup
from .settings import Session
from .settings import Settings
from . import cmds
from . import core
from . import compat
from . import fsmonitor
from . import git
from . import gitcfg
from . import guicmds
from . import hidpi
from . import icons
from . import i18n
from . import qtcompat
from . import qtutils
from . import resources
from . import themes
from . import utils
from . import version


def setup_environment():
    """Set environment variables to control git's behavior"""
    # Allow Ctrl-C to exit
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Session management wants an absolute path when restarting
    sys.argv[0] = sys_argv0 = os.path.abspath(sys.argv[0])

    # Spoof an X11 display for SSH
    os.environ.setdefault('DISPLAY', ':0')

    if not core.getenv('SHELL', ''):
        for shell in ('/bin/zsh', '/bin/bash', '/bin/sh'):
            if os.path.exists(shell):
                compat.setenv('SHELL', shell)
                break

    # Setup the path so that git finds us when we run 'git cola'
    path_entries = core.getenv('PATH', '').split(os.pathsep)
    bindir = core.decode(os.path.dirname(sys_argv0))
    path_entries.append(bindir)
    path = os.pathsep.join(path_entries)
    compat.setenv('PATH', path)

    # We don't ever want a pager
    compat.setenv('GIT_PAGER', '')

    # Setup *SSH_ASKPASS
    git_askpass = core.getenv('GIT_ASKPASS')
    ssh_askpass = core.getenv('SSH_ASKPASS')
    if git_askpass:
        askpass = git_askpass
    elif ssh_askpass:
        askpass = ssh_askpass
    elif sys.platform == 'darwin':
        askpass = resources.share('bin', 'ssh-askpass-darwin')
    else:
        askpass = resources.share('bin', 'ssh-askpass')

    compat.setenv('GIT_ASKPASS', askpass)
    compat.setenv('SSH_ASKPASS', askpass)

    # --- >8 --- >8 ---
    # Git v1.7.10 Release Notes
    # =========================
    #
    # Compatibility Notes
    # -------------------
    #
    #  * From this release on, the "git merge" command in an interactive
    #   session will start an editor when it automatically resolves the
    #   merge for the user to explain the resulting commit, just like the
    #   "git commit" command does when it wasn't given a commit message.
    #
    #   If you have a script that runs "git merge" and keeps its standard
    #   input and output attached to the user's terminal, and if you do not
    #   want the user to explain the resulting merge commits, you can
    #   export GIT_MERGE_AUTOEDIT environment variable set to "no", like
    #   this:
    #
    #        #!/bin/sh
    #        GIT_MERGE_AUTOEDIT=no
    #        export GIT_MERGE_AUTOEDIT
    #
    #   to disable this behavior (if you want your users to explain their
    #   merge commits, you do not have to do anything).  Alternatively, you
    #   can give the "--no-edit" option to individual invocations of the
    #   "git merge" command if you know everybody who uses your script has
    #   Git v1.7.8 or newer.
    # --- >8 --- >8 ---
    # Longer-term: Use `git merge --no-commit` so that we always
    # have a chance to explain our merges.
    compat.setenv('GIT_MERGE_AUTOEDIT', 'no')

    # Gnome3 on Debian has XDG_SESSION_TYPE=wayland and
    # XDG_CURRENT_DESKTOP=GNOME, which Qt warns about at startup:
    #
    #   Warning: Ignoring XDG_SESSION_TYPE=wayland on Gnome.
    #   Use QT_QPA_PLATFORM=wayland to run on Wayland anyway.
    #
    # This annoying, so we silence the warning.
    # We'll need to keep this hack here until a future version of Qt provides
    # Qt Wayland widgets that are usable in gnome-shell.
    # Cf. https://bugreports.qt.io/browse/QTBUG-68619
    if (
        core.getenv('XDG_CURRENT_DESKTOP', '') == 'GNOME'
        and core.getenv('XDG_SESSION_TYPE', '') == 'wayland'
    ):
        compat.unsetenv('XDG_SESSION_TYPE')


def get_icon_themes(context):
    """Return the default icon theme names"""
    result = []

    icon_themes_env = core.getenv('GIT_COLA_ICON_THEME')
    if icon_themes_env:
        result.extend([x for x in icon_themes_env.split(':') if x])

    icon_themes_cfg = context.cfg.get_all('cola.icontheme')
    if icon_themes_cfg:
        result.extend(icon_themes_cfg)

    if not result:
        result.append('light')

    return result


# style note: we use camelCase here since we're masquerading a Qt class
class ColaApplication(object):
    """The main cola application

    ColaApplication handles i18n of user-visible data
    """

    def __init__(self, context, argv, locale=None, icon_themes=None, gui_theme=None):
        cfgactions.install()
        i18n.install(locale)
        qtcompat.install()
        guicmds.install()
        standard.install()
        icons.install(icon_themes or get_icon_themes(context))

        self.context = context
        self._install_hidpi_config()
        self._app = ColaQApplication(context, list(argv))
        self._app.setWindowIcon(icons.cola())
        self._install_style(gui_theme)

    def _install_style(self, theme_str):
        """Generate and apply a stylesheet to the app"""
        if theme_str is None:
            theme_str = self.context.cfg.get('cola.theme', default='default')
        theme = themes.find_theme(theme_str)
        self._app.setStyleSheet(theme.build_style_sheet(self._app.palette()))
        if theme_str != 'default':
            self._app.setPalette(theme.build_palette(self._app.palette()))

    def _install_hidpi_config(self):
        """Sets QT HIDPI scalling (requires Qt 5.6)"""
        value = self.context.cfg.get('cola.hidpi', default=hidpi.Option.AUTO)
        hidpi.apply_choice(value)

    def activeWindow(self):
        """QApplication::activeWindow() pass-through"""
        return self._app.activeWindow()

    def desktop(self):
        """QApplication::desktop() pass-through"""
        return self._app.desktop()

    def start(self):
        """Wrap exec_() and start the application"""
        # Defer connection so that local cola.inotify is honored
        context = self.context
        monitor = context.fsmonitor
        monitor.files_changed.connect(
            cmds.run(cmds.Refresh, context), type=Qt.QueuedConnection
        )
        monitor.config_changed.connect(
            cmds.run(cmds.RefreshConfig, context), type=Qt.QueuedConnection
        )
        # Start the filesystem monitor thread
        monitor.start()
        return self._app.exec_()

    def stop(self):
        """Finalize the application"""
        self.context.fsmonitor.stop()
        # Workaround QTBUG-52988 by deleting the app manually to prevent a
        # crash during app shutdown.
        # https://bugreports.qt.io/browse/QTBUG-52988
        try:
            del self._app
        except (AttributeError, RuntimeError):
            pass
        self._app = None

    def exit(self, status):
        """QApplication::exit(status) pass-through"""
        return self._app.exit(status)


class ColaQApplication(QtWidgets.QApplication):
    """QApplication implementation for handling custom events"""

    def __init__(self, context, argv):
        super(ColaQApplication, self).__init__(argv)
        self.context = context
        # Make icons sharp in HiDPI screen
        if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
            self.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    def event(self, e):
        """Respond to focus events for the cola.refreshonfocus feature"""
        if e.type() == QtCore.QEvent.ApplicationActivate:
            context = self.context
            if context:
                cfg = context.cfg
                if context.git.is_valid() and cfg.get(
                    'cola.refreshonfocus', default=False
                ):
                    cmds.do(cmds.Refresh, context)
        return super(ColaQApplication, self).event(e)

    def commitData(self, session_mgr):
        """Save session data"""
        if not self.context or not self.context.view:
            return
        view = self.context.view
        if not hasattr(view, 'save_state'):
            return
        sid = session_mgr.sessionId()
        skey = session_mgr.sessionKey()
        session_id = '%s_%s' % (sid, skey)
        session = Session(session_id, repo=core.getcwd())
        session.update()
        view.save_state(settings=session)


def process_args(args):
    """Process and verify command-line arguments"""
    if args.version:
        # Accept 'git cola --version' or 'git cola version'
        version.print_version()
        sys.exit(core.EXIT_SUCCESS)

    # Handle session management
    restore_session(args)

    # Bail out if --repo is not a directory
    repo = core.decode(args.repo)
    if repo.startswith('file:'):
        repo = repo[len('file:') :]
    repo = core.realpath(repo)
    if not core.isdir(repo):
        errmsg = (
            N_(
                'fatal: "%s" is not a directory.  '
                'Please specify a correct --repo <path>.'
            )
            % repo
        )
        core.print_stderr(errmsg)
        sys.exit(core.EXIT_USAGE)


def restore_session(args):
    """Load a session based on the window-manager provided arguments"""
    # args.settings is provided when restoring from a session.
    args.settings = None
    if args.session is None:
        return
    session = Session(args.session)
    if session.load():
        args.settings = session
        args.repo = session.repo


def application_init(args, update=False):
    """Parses the command-line arguments and starts git-cola"""
    # Ensure that we're working in a valid git repository.
    # If not, try to find one.  When found, chdir there.
    setup_environment()
    process_args(args)

    context = new_context(args)
    timer = context.timer
    timer.start('init')

    new_worktree(context, args.repo, args.prompt)

    if update:
        context.model.update_status()

    timer.stop('init')
    if args.perf:
        timer.display('init')
    return context


def new_context(args):
    """Create top-level ApplicationContext objects"""
    context = ApplicationContext(args)
    context.settings = args.settings or Settings.read()
    context.git = git.create()
    context.cfg = gitcfg.create(context)
    context.fsmonitor = fsmonitor.create(context)
    context.selection = selection.create()
    context.model = main.create(context)
    context.app = new_application(context, args)
    context.timer = Timer()

    return context


def application_run(context, view, start=None, stop=None):
    """Run the application main loop"""
    initialize_view(context, view)
    # Startup callbacks
    if start:
        start(context, view)
    # Start the event loop
    result = context.app.start()
    # Finish
    if stop:
        stop(context, view)
    context.app.stop()

    return result


def initialize_view(context, view):
    """Register the main widget and display it"""
    context.set_view(view)
    view.show()
    if sys.platform == 'darwin':
        view.raise_()


def application_start(context, view):
    """Show the GUI and start the main event loop"""
    # Store the view for session management
    return application_run(context, view, start=default_start, stop=default_stop)


def default_start(context, _view):
    """Scan for the first time"""
    QtCore.QTimer.singleShot(0, startup_message)
    QtCore.QTimer.singleShot(0, lambda: async_update(context))


def default_stop(_context, _view):
    """All done, cleanup"""
    QtCore.QThreadPool.globalInstance().waitForDone()


def add_common_arguments(parser):
    """Add command arguments to the ArgumentParser"""
    # We also accept 'git cola version'
    parser.add_argument(
        '--version', default=False, action='store_true', help='print version number'
    )

    # Specifies a git repository to open
    parser.add_argument(
        '-r',
        '--repo',
        metavar='<repo>',
        default=core.getcwd(),
        help='open the specified git repository',
    )

    # Specifies that we should prompt for a repository at startup
    parser.add_argument(
        '--prompt', action='store_true', default=False, help='prompt for a repository'
    )

    # Specify the icon theme
    parser.add_argument(
        '--icon-theme',
        metavar='<theme>',
        dest='icon_themes',
        action='append',
        default=[],
        help='specify an icon theme (name or directory)',
    )

    # Resume an X Session Management session
    parser.add_argument(
        '-session', metavar='<session>', default=None, help=argparse.SUPPRESS
    )

    # Enable timing information
    parser.add_argument(
        '--perf', action='store_true', default=False, help=argparse.SUPPRESS
    )

    # Specify the GUI theme
    parser.add_argument(
        '--theme', metavar='<name>', default=None, help='specify an GUI theme name'
    )


def new_application(context, args):
    """Create a new ColaApplication"""
    return ColaApplication(
        context, sys.argv, icon_themes=args.icon_themes, gui_theme=args.theme
    )


def new_worktree(context, repo, prompt):
    """Find a Git repository, or prompt for one when not found"""
    model = context.model
    cfg = context.cfg
    parent = qtutils.active_window()
    valid = False

    if not prompt:
        valid = model.set_worktree(repo)
        if not valid:
            # We are not currently in a git repository so we need to find one.
            # Before prompting the user for a repository, check if they've
            # configured a default repository and attempt to use it.
            default_repo = cfg.get('cola.defaultrepo')
            if default_repo:
                valid = model.set_worktree(default_repo)

    while not valid:
        # If we've gotten into this loop then that means that neither the
        # current directory nor the default repository were available.
        # Prompt the user for a repository.
        startup_dlg = startup.StartupDialog(context, parent)
        gitdir = startup_dlg.find_git_repo()
        if not gitdir:
            sys.exit(core.EXIT_NOINPUT)

        if not core.exists(os.path.join(gitdir, '.git')):
            offer_to_create_repo(context, gitdir)
            valid = model.set_worktree(gitdir)
            continue

        valid = model.set_worktree(gitdir)
        if not valid:
            standard.critical(
                N_('Error Opening Repository'), N_('Could not open %s.' % gitdir)
            )


def offer_to_create_repo(context, gitdir):
    """Offer to create a new repo"""
    title = N_('Repository Not Found')
    text = N_('%s is not a Git repository.') % gitdir
    informative_text = N_('Create a new repository at that location?')
    if standard.confirm(title, text, informative_text, N_('Create')):
        status, out, err = context.git.init(gitdir)
        title = N_('Error Creating Repository')
        if status != 0:
            Interaction.command_error(title, 'git init', status, out, err)


def async_update(context):
    """Update the model in the background

    git-cola should startup as quickly as possible.

    """
    update_status = partial(context.model.update_status, update_index=True)
    task = qtutils.SimpleTask(context.view, update_status)
    context.runtask.start(task)


def startup_message():
    """Print debug startup messages"""
    trace = git.GIT_COLA_TRACE
    if trace in ('2', 'trace'):
        msg1 = 'info: debug level 2: trace mode enabled'
        msg2 = 'info: set GIT_COLA_TRACE=1 for less-verbose output'
        Interaction.log(msg1)
        Interaction.log(msg2)
    elif trace:
        msg1 = 'info: debug level 1'
        msg2 = 'info: set GIT_COLA_TRACE=2 for trace mode'
        Interaction.log(msg1)
        Interaction.log(msg2)


def initialize():
    """System-level initialization"""
    # The current directory may have been deleted while we are still
    # in that directory.  We rectify this situation by walking up the
    # directory tree and retrying.
    #
    # This is needed because  because Python throws exceptions in lots of
    # stdlib functions when in this situation, e.g. os.path.abspath() and
    # os.path.realpath(), so it's simpler to mitigate the damage by changing
    # the current directory to one that actually exists.
    while True:
        try:
            return core.getcwd()
        except OSError:
            os.chdir('..')


class Timer(object):
    """Simple performance timer"""

    def __init__(self):
        self._data = {}

    def start(self, key):
        """Start a timer"""
        now = time.time()
        self._data[key] = [now, now]

    def stop(self, key):
        """Stop a timer and return its elapsed time"""
        entry = self._data[key]
        entry[1] = time.time()
        return self.elapsed(key)

    def elapsed(self, key):
        """Return the elapsed time for a timer"""
        entry = self._data[key]
        return entry[1] - entry[0]

    def display(self, key):
        """Display a timer"""
        elapsed = self.elapsed(key)
        sys.stdout.write('%s: %.5fs\n' % (key, elapsed))


class ApplicationContext(object):
    """Context for performing operations on Git and related data models"""

    def __init__(self, args):
        self.args = args
        self.app = None  # ColaApplication
        self.git = None  # git.Git
        self.cfg = None  # gitcfg.GitConfig
        self.model = None  # main.MainModel
        self.timer = None  # Timer
        self.runtask = None  # qtutils.RunTask
        self.settings = None  # settings.Settings
        self.selection = None  # selection.SelectionModel
        self.fsmonitor = None  # fsmonitor
        self.view = None  # QWidget

    def set_view(self, view):
        """Initialize view-specific members"""
        self.view = view
        self.runtask = qtutils.RunTask(parent=view)


def winmain(main_fn, *argv):
    """Find Git and launch main(argv)"""
    git_path = find_git()
    if git_path:
        prepend_path(git_path)
    return main_fn(*argv)


def find_git():
    """Return the path of git.exe, or None if we can't find it."""
    if not utils.is_win32():
        return None  # UNIX systems have git in their $PATH

    # If the user wants to use a Git/bin/ directory from a non-standard
    # directory then they can write its location into
    # ~/.config/git-cola/git-bindir
    git_bindir = os.path.expanduser(
        os.path.join('~', '.config', 'git-cola', 'git-bindir')
    )
    if core.exists(git_bindir):
        custom_path = core.read(git_bindir).strip()
        if custom_path and core.exists(custom_path):
            return custom_path

    # Try to find Git's bin/ directory in one of the typical locations
    pf = os.environ.get('ProgramFiles', 'C:\\Program Files')
    pf32 = os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')
    pf64 = os.environ.get('ProgramW6432', 'C:\\Program Files')
    for p in [pf64, pf32, pf, 'C:\\']:
        candidate = os.path.join(p, 'Git\\bin')
        if os.path.isdir(candidate):
            return candidate

    return None


def prepend_path(path):
    """Adds git to the PATH.  This is needed on Windows."""
    path = core.decode(path)
    path_entries = core.getenv('PATH', '').split(os.pathsep)
    if path not in path_entries:
        path_entries.insert(0, path)
        compat.setenv('PATH', os.pathsep.join(path_entries))
