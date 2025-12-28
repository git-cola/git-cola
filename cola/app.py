"""Provides the main() routine and ColaApplication"""
from functools import partial
import argparse
import os
import random
import signal
import sys
import time

try:
    from qtpy import QtCore
except ImportError as error:
    sys.stderr.write(
        """
Your Python environment does not have qtpy and PyQt (or PySide).
The following error was encountered when importing "qtpy":

    ImportError: {err}

Install qtpy and PyQt (or PySide) into your Python environment.
On a Debian/Ubuntu system you can install these modules using apt:

    sudo apt install python3-pyqt5 python3-pyqt5.qtwebengine python3-qtpy

""".format(
            err=error
        )
    )
    sys.exit(1)

from qtpy import QtWidgets
from qtpy.QtCore import Qt, Signal

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
from . import cmd
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
    random.seed(hash(time.time()))
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

    # Setup the openssh askpass credentials helper.
    askpass = _get_askpass()
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


def _get_askpass():
    """Get a default askpass program appropriate for the current environment"""
    git_askpass = core.getenv('GIT_ASKPASS')
    ssh_askpass = core.getenv('SSH_ASKPASS')
    if git_askpass:
        return git_askpass
    if ssh_askpass:
        return ssh_askpass
    if sys.platform == 'darwin':
        return resources.package_command('ssh-askpass-darwin')

    kde_askpass = core.find_executable('ksshaskpass')
    gnome_askpass = core.find_executable('gnome-ssh-askpass')
    if gnome_askpass is None:
        gnome_askpass = '/usr/lib/openssh/gnome-ssh-askpass'

    desktop_session = os.environ.get('DESKTOP_SESSION', 'unknown')
    if desktop_session == 'gnome':
        order = (gnome_askpass, kde_askpass)
    else:
        order = (kde_askpass, gnome_askpass)

    for askpass in order:
        if askpass and os.path.exists(askpass):
            return askpass

    return resources.package_command('ssh-askpass')


def get_icon_themes(context):
    """Return the default icon theme names"""
    result = []

    icon_themes_env = core.getenv('GIT_COLA_ICON_THEME')
    if icon_themes_env:
        result.extend([x for x in icon_themes_env.split(':') if x])

    icon_themes_cfg = list(reversed(context.cfg.get_all('cola.icontheme')))
    if icon_themes_cfg:
        result.extend(icon_themes_cfg)

    if not result:
        result.append('light')

    return result


# style note: we use camelCase here since we're masquerading a Qt class
class ColaApplication:
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
        self.theme = None
        self._install_hidpi_config()
        self._app = ColaQApplication(context, list(argv))
        self._app.setWindowIcon(icons.cola())
        self._app.setDesktopFileName('git-cola')
        self._install_style(gui_theme)

    def _install_style(self, theme_str):
        """Generate and apply a stylesheet to the app"""
        if theme_str is None:
            theme_str = self.context.cfg.get('cola.theme', default='default')
        theme = themes.find_theme(theme_str)
        self.theme = theme

        bold_fonts = self.context.cfg.get('cola.boldfonts', default=False)
        theme_stylesheet = theme.build_style_sheet(self._app.palette(), bold_fonts)
        self._app.setStyleSheet(theme_stylesheet)

        is_macos_theme = theme_str.startswith('macos-')
        if is_macos_theme:
            themes.apply_platform_theme(theme_str)
        elif theme_str != 'default':
            self._app.setPalette(theme.build_palette(self._app.palette()))

    def _install_hidpi_config(self):
        """Sets QT HiDPI scaling (requires Qt 5.6)"""
        value = self.context.cfg.get('cola.hidpi', default=hidpi.Option.AUTO)
        hidpi.apply_choice(value)

    def activeWindow(self):
        """QApplication::activeWindow() pass-through"""
        return self._app.activeWindow()

    def palette(self):
        """QApplication::palette() pass-through"""
        return self._app.palette()

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
        super().__init__(argv)
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
        return super().event(e)

    def commitData(self, session_mgr):
        """Save session data"""
        if not self.context or not self.context.view:
            return
        view = self.context.view
        if not hasattr(view, 'save_state'):
            return
        sid = session_mgr.sessionId()
        skey = session_mgr.sessionKey()
        session_id = f'{sid}_{skey}'
        session = Session(session_id, repo=core.getcwd())
        session.update()
        view.save_state(settings=session)


def process_args(args, setup_repo=False):
    """Process and verify command-line arguments"""
    if args.version:
        # Accept 'git cola --version' or 'git cola version'
        version.print_version()
        sys.exit(core.EXIT_SUCCESS)

    # Handle session management
    restore_session(args)

    # Initialize args.repo. If a repository was specified as a
    # positional argument then we will use that value.
    # If unspecified, the current directory is used.
    if setup_repo and not args.repo:
        if args.args and git.is_git_repository(args.args[0]):
            args.repo = args.args.pop(0)
    if not args.repo:
        args.repo = core.getcwd()

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


def application_init(
    args,
    update=False,
    app_name='Git Cola',
    setup_worktree=True,
    setup_repo=False,
):
    """Parses the command-line arguments and starts git-cola"""
    # Ensure that we're working in a valid git repository.
    # If not, try to find one.  When found, chdir there.
    setup_environment()
    process_args(args, setup_repo=setup_repo)

    context = new_context(args, app_name=app_name)
    enforce_single_instance(context)

    timer = context.timer
    timer.start('init')

    if setup_worktree:
        new_worktree(context, args.repo, args.prompt)
        if update:
            context.model.update_status()

    timer.stop('init')
    if args.perf:
        timer.display('init')
    return context


def new_context(args, app_name='Git Cola'):
    """Create top-level ApplicationContext objects"""
    context = ApplicationContext(args)
    context.timestamp = time.time()
    context.settings = args.settings or Settings.read()
    context.git = git.create()
    context.cfg = gitcfg.create(context)
    context.fsmonitor = fsmonitor.create(context)
    context.selection = selection.create()
    context.model = main.create(context)
    context.app_name = app_name
    context.app = new_application(context, args)
    context.timer = Timer()

    return context


def create_context():
    """Create a one-off context from the current directory"""
    args = null_args()
    return new_context(args)


def enforce_single_instance(context):
    """Ensure that only a single instance of the application is running"""
    if not context.args.single_instance:
        return
    window_id = context.app_name.replace(' ', '-')
    semaphore = QtCore.QSystemSemaphore(window_id, 1)
    semaphore.acquire()  # Prevent other instances from interacting with shared memory.

    # We want to prevent the same instance from launching from the same directory.
    # This is not foolproof, as users can still change repositories while the app
    # is running, but this at least provides a workflow where users can launch
    # the app from within their repository and we will prevent multiple instances
    # from being launched from within that same repository.
    shared_mem_id = window_id + '-'
    current_dir_hash = utils.sha256hex(os.getcwd())
    # Shared memory IDs can be max 30 characters on macOS.
    remaining_bytes = 30 - len(shared_mem_id)
    shared_mem_id += current_dir_hash[:-remaining_bytes]

    # Shared memory may is not freed when the application terminates abnormally on
    # Linux/UNIX so we workaround that by detaching here.
    if not utils.is_win32():
        fix_shared_mem = QtCore.QSharedMemory(shared_mem_id)
        if fix_shared_mem.attach():
            fix_shared_mem.detach()

    # If the shared memory segment can be attached then we are already running.
    context.shared_memory = QtCore.QSharedMemory(shared_mem_id)
    if context.shared_memory.attach():
        is_running = True
    else:
        # Create a one-byte shared memory segment.
        context.shared_memory.create(1)
        is_running = False

    semaphore.release()

    if is_running:
        format_vars = {
            'app_name': context.app_name,
            'dirname': os.getcwd(),
        }
        QtWidgets.QMessageBox.warning(
            None,
            N_('%(app_name)s is already running') % format_vars,
            N_('%(app_name)s is already running in %(dirname)s (--single-instance).')
            % format_vars,
        )
        sys.exit(1)


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
        '--theme', metavar='<name>', default=None, help='specify a GUI theme name'
    )

    # Allow only a single instance
    parser.add_argument(
        '-S',
        '--single-instance',
        action='store_true',
        help='only allow a single instance to be running',
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
            err = model.error
            standard.critical(
                N_('Error Opening Repository'),
                message=N_('Could not open %s.' % gitdir),
                details=err,
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
    update_index = context.cfg.get('cola.updateindex', True)
    update_status = partial(context.model.update_status, update_index=update_index)
    task = qtutils.SimpleTask(update_status)
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
    # We support ~/.config/git-cola/git-bindir on Windows for configuring
    # a custom location for finding the "git" executable.
    git_path = find_git()
    if git_path:
        prepend_path(git_path)

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


class Timer:
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
        sys.stdout.write(f'{key}: {elapsed:.5f}s\n')


class NullArgs:
    """Stub arguments for interactive API use"""

    def __init__(self):
        self.icon_themes = []
        self.perf = False
        self.prompt = False
        self.repo = core.getcwd()
        self.session = None
        self.settings = None
        self.theme = None
        self.version = False


def null_args():
    """Create a new instance of application arguments"""
    return NullArgs()


class ApplicationContext:
    """Context for performing operations on Git and related data models"""

    def __init__(self, args):
        self.args = args
        self.app = None  # ColaApplication
        self.shared_memory = None  # QSharedMemory
        self.command_bus = None  # cmd.CommandBus
        self.git = None  # git.Git
        self.cfg = None  # gitcfg.GitConfig
        self.model = None  # main.MainModel
        self.notifier = Notifier(self)
        self.timer = None  # Timer
        self.runtask = None  # qtutils.RunTask
        self.settings = None  # settings.Settings
        self.selection = None  # selection.SelectionModel
        self.fsmonitor = None  # fsmonitor
        self.view = None  # QWidget
        self.browser_windows = []  # list of browse.Browser

    def set_view(self, view):
        """Initialize view-specific members"""
        self.view = view
        self.notifier.setParent(view)
        self.command_bus = cmd.CommandBus(parent=view)
        self.runtask = qtutils.RunTask(parent=view)
        self.notifier.command.connect(self._command, Qt.QueuedConnection)
        self.notifier.critical.connect(self._critical, Qt.QueuedConnection)
        self.notifier.information.connect(self._information, Qt.QueuedConnection)
        self.notifier.log.connect(self._log, Qt.QueuedConnection)
        self.notifier.ready.emit()

    def _command(self, title, cmd, status, out, err):
        Interaction.command(title, cmd, status, out, err)

    def _critical(self, title, kwargs):
        Interaction.critical(title, **kwargs)

    def _information(self, title, kwargs):
        Interaction.information(title, **kwargs)

    def _log(self, message):
        Interaction.log(message)


class Notifier(QtCore.QObject):
    """Message bus for generic one-off notifications"""

    command = Signal(str, str, int, str, str)
    critical = Signal(object, object)
    information = Signal(object, object)
    log = Signal(object)
    message = Signal(object)
    ready = Signal()

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context

    def notify(self, message):
        """Send messages to listeners"""
        self.message.emit(message)

    def listen(self, message, callback):
        """Subscribe a callback specific messages"""

        def listener(current_message, message=message, callback=callback):
            """Fire a callback when specific messages are seen"""
            if current_message is message:
                callback()

        self.message.connect(listener, type=Qt.QueuedConnection)

    def emit_log(self, message):
        """Emit a log message"""
        self.log.emit(message)

    def git_cmd(self, message):
        """Emit a log message"""
        self.emit_log(f'[git] {message}')


def find_git():
    """Return the path of git.exe, or None if we can't find it."""
    if not utils.is_win32():
        return None  # UNIX systems have git in their $PATH

    # If the user wants to use a Git/bin/ directory from a non-standard
    # directory then they can write its location into
    # ~/.config/git-cola/git-bindir
    git_bindir = resources.config_home('git-bindir')
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
