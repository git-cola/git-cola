# Copyright (C) 2009, 2010, 2011, 2012, 2013
# David Aguilar <davvid@gmail.com>
"""Provides the main() routine and ColaApplicaiton"""

import glob
import os
import signal
import sys

# Make homebrew work by default
if sys.platform == 'darwin':
    from distutils import sysconfig
    python_version = sysconfig.get_python_version()
    homebrew_mods = '/usr/local/lib/python%s/site-packages' % python_version
    if os.path.isdir(homebrew_mods):
        sys.path.append(homebrew_mods)

try:
    from PyQt4 import QtGui
    from PyQt4 import QtCore
    from PyQt4.QtCore import SIGNAL
except ImportError:
    sys.stderr.write('Sorry, you do not seem to have PyQt4 installed.\n')
    sys.stderr.write('Please install it before using git-cola.\n')
    sys.stderr.write('e.g.: sudo apt-get install python-qt4\n')
    sys.exit(-1)


# Import cola modules
from cola import core
from cola import compat
from cola import git
from cola import inotify
from cola import i18n
from cola import qtcompat
from cola import qtutils
from cola import resources
from cola import utils
from cola import version
from cola.decorators import memoize
from cola.interaction import Interaction
from cola.models import main
from cola.widgets import cfgactions
from cola.widgets import startup


def setup_environment():
    # Spoof an X11 display for SSH
    os.environ.setdefault('DISPLAY', ':0')

    if not core.getenv('SHELL', ''):
        for shell in ('/bin/zsh', '/bin/bash', '/bin/sh'):
            if os.path.exists(shell):
                compat.setenv('SHELL', shell)
                break

    # Setup the path so that git finds us when we run 'git cola'
    path_entries = core.getenv('PATH', '').split(os.pathsep)
    bindir = os.path.dirname(core.abspath(__file__))
    path_entries.insert(0, bindir)
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


@memoize
def instance(argv):
    return QtGui.QApplication(list(argv))


# style note: we use camelCase here since we're masquerading a Qt class
class ColaApplication(object):
    """The main cola application

    ColaApplication handles i18n of user-visible data
    """

    def __init__(self, argv, locale=None, gui=True):
        cfgactions.install()
        i18n.install(locale)
        qtcompat.install()
        qtutils.install()

        # Add the default style dir so that we find our icons
        icon_dir = resources.icon_dir()
        qtcompat.add_search_path(os.path.basename(icon_dir), icon_dir)

        if gui:
            self._app = instance(tuple(argv))
            self._app.setWindowIcon(qtutils.git_icon())
        else:
            self._app = QtCore.QCoreApplication(argv)

        self._app.setStyleSheet("""
            QMainWindow::separator {
                width: 3px;
                height: 3px;
            }
            QMainWindow::separator:hover {
                background: white;
            }
            """)

    def activeWindow(self):
        """Wrap activeWindow()"""
        return self._app.activeWindow()

    def desktop(self):
        return self._app.desktop()

    def exec_(self):
        """Wrap exec_()"""
        return self._app.exec_()


def process_args(args):
    if args.version:
        # Accept 'git cola --version' or 'git cola version'
        version.print_version()
        sys.exit(0)

    if args.git_path:
        # Adds git to the PATH.  This is needed on Windows.
        path_entries = core.getenv('PATH', '').split(os.pathsep)
        path_entries.insert(0, os.path.dirname(core.decode(args.git_path)))
        compat.setenv('PATH', os.pathsep.join(path_entries))

    # Bail out if --repo is not a directory
    repo = core.decode(args.repo)
    if repo.startswith('file:'):
        repo = repo[len('file:'):]
    repo = core.realpath(repo)
    if not core.isdir(repo):
        sys.stderr.write("fatal: '%s' is not a directory.  "
                         'Consider supplying -r <path>.\n' % repo)
        sys.exit(-1)

    # We do everything relative to the repo root
    os.chdir(args.repo)
    return repo


def application_init(args, update=False):
    """Parses the command-line arguments and starts git-cola
    """
    setup_environment()
    process_args(args)

    # Ensure that we're working in a valid git repository.
    # If not, try to find one.  When found, chdir there.
    app = new_application()
    model = new_model(app, args.repo, prompt=args.prompt)
    if update:
        model.update_status()

    return ApplicationContext(args, app, model)


def application_start(context, view):
    # Make sure that we start out on top
    view.show()
    view.raise_()

    # Scan for the first time
    task = _start_update_thread(context.model)

    # Start the inotify thread
    inotify.start()

    msg_timer = QtCore.QTimer()
    msg_timer.setSingleShot(True)
    msg_timer.connect(msg_timer, SIGNAL('timeout()'), _send_msg)
    msg_timer.start(0)

    # Start the event loop
    result = context.app.exec_()

    # All done, cleanup
    inotify.stop()
    QtCore.QThreadPool.globalInstance().waitForDone()
    del task

    pattern = utils.tmp_file_pattern()
    for filename in glob.glob(pattern):
        os.unlink(filename)

    return result


def add_common_arguments(parser):
    # We also accept 'git cola version'
    parser.add_argument('--version', default=False, action='store_true',
                        help='prints the version')

    # Specifies a git repository to open
    parser.add_argument('-r', '--repo', metavar='<repo>', default=os.getcwd(),
                        help='specifies the path to a git repository')

    # Specifies that we should prompt for a repository at startup
    parser.add_argument('--prompt', action='store_true', default=False,
                        help='prompts for a repository')

    # Used on Windows for adding 'git' to the path
    parser.add_argument('-g', '--git-path', metavar='<path>', default=None,
                        help='specifies the path to the git binary')


def new_application():
    # Allow Ctrl-C to exit
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Initialize the app
    return ColaApplication(sys.argv)


def new_model(app, repo, prompt=False):
    model = main.model()
    valid = model.set_worktree(repo) and not prompt
    while not valid:
        startup_dlg = startup.StartupDialog(app.activeWindow())
        gitdir = startup_dlg.find_git_repo()
        if not gitdir:
            sys.exit(-1)
        valid = model.set_worktree(gitdir)

    # Finally, go to the root of the git repo
    os.chdir(model.git.worktree())
    return model


def _start_update_thread(model):
    """Update the model in the background

    git-cola should startup as quickly as possible.

    """
    class UpdateTask(QtCore.QRunnable):
        def run(self):
            model.update_status(update_index=True)

    # Hold onto a reference to prevent PyQt from dereferencing
    task = UpdateTask()
    QtCore.QThreadPool.globalInstance().start(task)

    return task


def _send_msg():
    if git.GIT_COLA_TRACE == 'trace':
        msg = ('info: Trace enabled.  '
               'Many of commands reported with "trace" use git\'s stable '
               '"plumbing" API and are not intended for typical '
               'day-to-day use.  Here be dragons')
        Interaction.log(msg)


class ApplicationContext(object):

    def __init__(self, args, app, model):
        self.args = args
        self.app = app
        self.model = model
