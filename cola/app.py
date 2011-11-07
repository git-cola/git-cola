# Copyright (C) 2009, David Aguilar <davvid@gmail.com>
"""Provides the main() routine and ColaApplicaiton"""

import glob
import optparse
import os
import signal
import sys

try:
    from PyQt4 import QtGui
    from PyQt4 import QtCore
    from PyQt4.QtCore import SIGNAL
except ImportError:
    print >> sys.stderr, 'Sorry, you do not seem to have PyQt4 installed.'
    print >> sys.stderr, 'Please install it before using git-cola.'
    print >> sys.stderr, 'e.g.:    sudo apt-get install python-qt4'
    sys.exit(-1)


# Import cola modules
import cola
from cola import cmds
from cola import git
from cola import guicmds
from cola import inotify
from cola import i18n
from cola import qtcompat
from cola import qtutils
from cola import resources
from cola import signals
from cola import utils
from cola import version
from cola.classic import cola_classic
from cola.dag import git_dag
from cola.decorators import memoize
from cola.main.view import MainView
from cola.main.controller import MainController
from cola.widgets import cfgactions
from cola.widgets import startup


def setup_environment():
    # Spoof an X11 display for SSH
    os.environ.setdefault('DISPLAY', ':0')

    # Provide an SSH_ASKPASS fallback
    if sys.platform == 'darwin':
        os.environ.setdefault('SSH_ASKPASS',
                              resources.share('bin', 'ssh-askpass-darwin'))
    else:
        os.environ.setdefault('SSH_ASKPASS',
                              resources.share('bin', 'ssh-askpass'))

    # Setup the path so that git finds us when we run 'git cola'
    path_entries = os.environ.get('PATH').split(os.pathsep)
    bindir = os.path.dirname(os.path.abspath(__file__))
    path_entries.insert(0, bindir)
    path = os.pathsep.join(path_entries)
    os.environ['PATH'] = path
    os.putenv('PATH', path)


@memoize
def instance(argv):
    return QtGui.QApplication(list(argv))


# style note: we use camelCase here since we're masquerading a Qt class
class ColaApplication(object):
    """The main cola application

    ColaApplication handles i18n of user-visible data
    """

    def __init__(self, argv, locale=None, gui=True):
        """Initialize our QApplication for translation
        """
        i18n.install(locale)
        qtcompat.install()

        # Add the default style dir so that we find our icons
        icon_dir = resources.icon_dir()
        qtcompat.add_search_path(os.path.basename(icon_dir), icon_dir)

        # monkey-patch Qt's translate() to use our translate()
        if gui:
            self._app = instance(tuple(argv))
            self._app.setWindowIcon(QtGui.QIcon(resources.icon('git.svg')))
            self._translate_base = QtGui.QApplication.translate
            QtGui.QApplication.translate = self.translate
        else:
            self._app = QtCore.QCoreApplication(argv)
            self._translate_base = QtCore.QCoreApplication.translate
            QtCore.QCoreApplication.translate = self.translate

        # Register model commands
        cmds.register()

        # Make file descriptors binary for win32
        utils.set_binary(sys.stdin)
        utils.set_binary(sys.stdout)
        utils.set_binary(sys.stderr)

    def translate(self, domain, txt):
        """
        Translate strings with gettext

        Supports @@noun/@@verb specifiers.

        """
        trtxt = i18n.gettext(txt)
        if trtxt[-6:-4] == '@@': # handle @@verb / @@noun
            trtxt = trtxt[:-6]
        return trtxt

    def activeWindow(self):
        """Wrap activeWindow()"""
        return self._app.activeWindow()

    def exec_(self):
        """Wrap exec_()"""
        return self._app.exec_()


def parse_args(context):
    parser = optparse.OptionParser(usage='%prog [options]')

    # We also accept 'git cola version'
    parser.add_option('-v', '--version',
                      help='Show cola version',
                      dest='version',
                      default=False,
                      action='store_true')

    # Accept git cola --classic
    parser.add_option('--classic',
                      help='Launch cola classic',
                      dest='classic',
                      default=False,
                      action='store_true')

    # Specifies a git repository to open
    parser.add_option('-r', '--repo',
                      help='Specifies the path to a git repository.',
                      dest='repo',
                      metavar='PATH',
                      default=os.getcwd())

    # Specifies that we should prompt for a repository at startup
    parser.add_option('--prompt',
                      help='Prompt for a repository before starting the main GUI.',
                      dest='prompt',
                      action='store_true',
                      default=False)

    # Used on Windows for adding 'git' to the path
    parser.add_option('-g', '--git-path',
                      help='Specifies the path to the git binary',
                      dest='git',
                      metavar='PATH',
                      default='')

    if context == 'git-dag':
        parser.add_option('-c', '--count',
                          help='Number of commits to display.',
                          dest='count',
                          type='int',
                          default=1000)

    return parser.parse_args()


def process_args(opts, args):
    if opts.version or (args and args[0] == 'version'):
        # Accept 'git cola --version' or 'git cola version'
        print 'cola version', version.version()
        sys.exit(0)

    if opts.git:
        # Adds git to the PATH.  This is needed on Windows.
        path_entries = os.environ.get('PATH', '').split(os.pathsep)
        path_entries.insert(0, os.path.dirname(opts.git))
        os.environ['PATH'] = os.pathsep.join(path_entries)

    # Bail out if --repo is not a directory
    repo = os.path.realpath(opts.repo)
    if not os.path.isdir(repo):
        print >> sys.stderr, "fatal: '%s' is not a directory.  Consider supplying -r <path>.\n" % repo
        sys.exit(-1)

    # We do everything relative to the repo root
    os.chdir(opts.repo)

    return repo


def main(context):
    """Parses the command-line arguments and starts git-cola
    """
    setup_environment()
    opts, args = parse_args(context)
    repo = process_args(opts, args)

    # Allow Ctrl-C to exit
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Initialize the app
    app = ColaApplication(sys.argv)

    # Ensure that we're working in a valid git repository.
    # If not, try to find one.  When found, chdir there.
    model = cola.model()
    valid = model.use_worktree(repo) and not opts.prompt
    while not valid:
        startup_dlg = startup.StartupDialog(app.activeWindow())
        gitdir = startup_dlg.find_git_repo()
        if not gitdir:
            sys.exit(-1)
        valid = model.use_worktree(gitdir)

    # Finally, go to the root of the git repo
    os.chdir(model.git.worktree())

    # Show the GUI
    if opts.classic:
        view = cola_classic(update=False)
    elif context == 'git-cola':
        view = MainView(model)
        ctl = MainController(model, view)
    elif context == 'git-dag':
        ctl = git_dag(model, app.activeWindow(), opts=opts, args=args)
        view = ctl.view

    # Install UI wrappers for command objects
    cfgactions.install_command_wrapper()
    guicmds.install_command_wrapper()

    # Show the view and start the main event loop
    view.show()

    # Make sure that we start out on top
    view.raise_()

    # Scan for the first time
    task = _start_update_thread(model)

    # Start the inotify thread
    inotify.start()

    msg_timer = QtCore.QTimer()
    msg_timer.setSingleShot(True)
    msg_timer.connect(msg_timer, SIGNAL('timeout()'), _send_msg)
    msg_timer.start(0)

    # Start the event loop
    result = app.exec_()

    # All done, cleanup
    inotify.stop()
    QtCore.QThreadPool.globalInstance().waitForDone()

    pattern = cola.model().tmp_file_pattern()
    for filename in glob.glob(pattern):
        os.unlink(filename)
    sys.exit(result)

    return ctl, task


def _start_update_thread(model):
    """Update the model in the background

    git-cola should startup as quickly as possible.

    """
    from PyQt4 import QtCore

    class UpdateTask(QtCore.QRunnable):
        def run(self):
            model.update_status(update_index=True)

    # Hold onto a reference to prevent PyQt from dereferencing
    task = UpdateTask()
    QtCore.QThreadPool.globalInstance().start(task)

    return task


def _send_msg():
    import cola
    git.GIT_COLA_TRACE = os.getenv('GIT_COLA_TRACE', False)
    if git.GIT_COLA_TRACE:
        msg = ('info: Trace enabled.  '
               'Many of commands reported with "trace" use git\'s stable '
               '"plumbing" API and are not intended for typical '
               'day-to-day use.  Here be dragons')
        cola.notifier().broadcast(signals.log_cmd, 0, msg)
