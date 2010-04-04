# Copyright (C) 2009, David Aguilar <davvid@gmail.com>
"""Provides the main() routine used by the git-cola script"""

import optparse
import signal
import glob
import sys
import os

from cola import resources
from cola import utils
from cola import core
from cola import git
from cola import inotify
from cola import version

# Spoof an X11 display for SSH
os.environ.setdefault('DISPLAY', ':0')

# Provide an SSH_ASKPASS fallback
if sys.platform == 'darwin':
    os.environ.setdefault('SSH_ASKPASS',
                          resources.share('bin', 'ssh-askpass-darwin'))
else:
    os.environ.setdefault('SSH_ASKPASS',
                          resources.share('bin', 'ssh-askpass'))


def main():
    """Parses the command-line arguments and starts git-cola
    """
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

    # Accept --style=/path/to/style.qss or --style=dark for built-in styles
    parser.add_option('-s', '--style',
                      help='Applies an alternate stylesheet.  '
                           'The allowed values are: "dark" or a file path.',
                      dest='style',
                      metavar='PATH or STYLE',
                      default='')

    # Specifies a git repository to open
    parser.add_option('-r', '--repo',
                      help='Specifies the path to a git repository.',
                      dest='repo',
                      metavar='PATH',
                      default=os.getcwd())

    # Used on Windows for adding 'git' to the path
    parser.add_option('-g', '--git-path',
                      help='Specifies the path to the git binary',
                      dest='git',
                      metavar='PATH',
                      default='')
    opts, args = parser.parse_args()

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

    try:
        # Defer these imports to allow git cola --version without pyqt installed
        from PyQt4 import QtCore
        from PyQt4 import QtGui
    except ImportError:
        print >> sys.stderr, 'Sorry, you do not seem to have PyQt4 installed.'
        print >> sys.stderr, 'Please install it before using cola.'
        print >> sys.stderr, 'e.g.:    sudo apt-get install python-qt4'
        sys.exit(-1)

    # Import cola modules
    import cola
    from cola.models.gitrepo import GitRepoModel
    from cola.views import startup
    from cola.views.main import MainView
    from cola.views.repo import RepoDialog
    from cola.controllers.main import MainController
    from cola.controllers.classic import ClassicController
    from cola.app import ColaApplication
    from cola import qtutils
    from cola import commands


    # Allow Ctrl-C to exit
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Initialize the app
    app = ColaApplication(sys.argv)

    style = None
    if opts.style:
        # This loads the built-in and user-specified stylesheets.
        # We allows absolute and relative paths to a stylesheet
        # by assuming that non-file arguments refer to a built-in style.
        if os.path.isabs(opts.style) or os.path.isfile(opts.style):
            filename = opts.style
        else:
            filename = resources.stylesheet(opts.style)

        if filename and os.path.exists(filename):
            # Automatically register each subdirectory in the style dir
            # as a Qt resource directory.
            _setup_resource_dir(os.path.dirname(filename))
            stylesheet = open(filename, 'r')
            style = core.read_nointr(stylesheet)
            stylesheet.close()
            app.setStyleSheet(style)
        else:
            _setup_resource_dir(resources.style_dir())
            print >> sys.stderr, ("warn: '%s' is not a valid style."
                                  % opts.style)
    else:
        # Add the default style dir so that we find our icons
        _setup_resource_dir(resources.style_dir())

    # Register model commands
    commands.register()

    # Ensure that we're working in a valid git repository.
    # If not, try to find one.  When found, chdir there.
    model = cola.model()
    valid = model.use_worktree(repo)
    while not valid:
        startup_dlg = startup.StartupDialog(app.activeWindow())
        gitdir = startup_dlg.find_git_repo()
        if not gitdir:
            sys.exit(-1)
        valid = model.use_worktree(gitdir)

    # Finally, go to the root of the git repo
    os.chdir(model.git.worktree())

    # Show the GUI and start the event loop
    if opts.classic:
        view = RepoDialog()
        view.tree.setModel(GitRepoModel(view.tree))
        controller = ClassicController(view.tree)
    else:
        view = MainView()
        controller = MainController(model, view)

    # Scan for the first time
    model.update_status()

    # Start the inotify thread
    inotify.start()

    # Make sure that we start out on top
    view.raise_()

    # Show the view and start the main event loop
    view.show()
    result = app.exec_()

    # All done, cleanup
    inotify.stop()

    # TODO: Provide fallback implementation
    if hasattr(QtCore, 'QThreadPool'):
        QtCore.QThreadPool.globalInstance().waitForDone()

    pattern = cola.model().tmp_file_pattern()
    for filename in glob.glob(pattern):
        os.unlink(filename)
    sys.exit(result)


def _setup_resource_dir(dirname):
    """Adds resource directories to Qt's search path"""
    from PyQt4 import QtCore
    resource_paths = resources.resource_dirs(dirname)
    for r in resource_paths:
        basename = os.path.basename(r)
        QtCore.QDir.setSearchPaths(basename, [r])
