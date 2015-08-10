from __future__ import division, absolute_import, unicode_literals

import os
import re

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import difftool
from cola import gitcmds
from cola import qtutils
from cola import utils
from cola.git import git
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import main
from cola.widgets import completion
from cola.widgets.browse import BrowseDialog
from cola.widgets.selectcommits import select_commits
from cola.compat import ustr


def delete_branch():
    """Launch the 'Delete Branch' dialog."""
    branch = choose_branch(N_('Delete Branch'), N_('Delete'))
    if not branch:
        return
    cmds.do(cmds.DeleteBranch, branch)


def delete_remote_branch():
    """Launch the 'Delete Remote Branch' dialog."""
    branch = choose_remote_branch(N_('Delete Remote Branch'), N_('Delete'))
    if not branch:
        return
    rgx = re.compile(r'^(?P<remote>[^/]+)/(?P<branch>.+)$')
    match = rgx.match(branch)
    if match:
        remote = match.group('remote')
        branch = match.group('branch')
        cmds.do(cmds.DeleteRemoteBranch, remote, branch)

def browse_current():
    """Launch the 'Browse Current Branch' dialog."""
    branch = gitcmds.current_branch()
    BrowseDialog.browse(branch)


def browse_other():
    """Prompt for a branch and inspect content at that point in time."""
    # Prompt for a branch to browse
    branch = choose_ref(N_('Browse Commits...'), N_('Browse'))
    if not branch:
        return
    BrowseDialog.browse(branch)


def checkout_branch():
    """Launch the 'Checkout Branch' dialog."""
    branch = choose_branch(N_('Checkout Branch'), N_('Checkout'))
    if not branch:
        return
    cmds.do(cmds.CheckoutBranch, branch)


def cherry_pick():
    """Launch the 'Cherry-Pick' dialog."""
    revs, summaries = gitcmds.log_helper(all=True)
    commits = select_commits(N_('Cherry-Pick Commit'),
                             revs, summaries, multiselect=False)
    if not commits:
        return
    cmds.do(cmds.CherryPick, commits)


def new_repo():
    """Prompt for a new directory and create a new Git repository

    :returns str: repository path or None if no repository was created.

    """
    dlg = QtGui.QFileDialog()
    dlg.setFileMode(QtGui.QFileDialog.Directory)
    dlg.setOption(QtGui.QFileDialog.ShowDirsOnly)
    dlg.show()
    dlg.raise_()
    if dlg.exec_() != QtGui.QFileDialog.Accepted:
        return None
    paths = dlg.selectedFiles()
    if not paths:
        return None
    path = ustr(paths[0])
    if not path:
        return None
    # Avoid needlessly calling `git init`.
    if git.is_git_dir(path):
        # We could prompt here and confirm that they really didn't
        # mean to open an existing repository, but I think
        # treating it like an "Open" is a sensible DWIM answer.
        return path

    status, out, err = core.run_command(['git', 'init', path])
    if status == 0:
        return path
    else:
        title = N_('Error Creating Repository')
        msg = (N_('"%(command)s" returned exit status %(status)d') %
               dict(command='git init %s' % path, status=status))
        details = N_('Output:\n%s') % out
        if err:
            details += '\n\n'
            details += N_('Errors: %s') % err
        qtutils.critical(title, msg, details)
        return None


def open_new_repo():
    dirname = new_repo()
    if not dirname:
        return
    cmds.do(cmds.OpenRepo, dirname)


def prompt_for_clone():
    """
    Present a GUI for cloning a repository.

    Returns the target directory and URL

    """
    url, ok = qtutils.prompt(N_('Path or URL to clone (Env. $VARS okay)'))
    url = utils.expandpath(url)
    if not ok or not url:
        return None
    try:
        # Pick a suitable basename by parsing the URL
        newurl = url.replace('\\', '/').rstrip('/')
        default = newurl.rsplit('/', 1)[-1]
        if default == '.git':
            # The end of the URL is /.git, so assume it's a file path
            default = os.path.basename(os.path.dirname(newurl))
        if default.endswith('.git'):
            # The URL points to a bare repo
            default = default[:-4]
        if url == '.':
            # The URL is the current repo
            default = os.path.basename(core.getcwd())
        if not default:
            raise
    except:
        Interaction.information(
                N_('Error Cloning'),
                N_('Could not parse Git URL: "%s"') % url)
        Interaction.log(N_('Could not parse Git URL: "%s"') % url)
        return None

    # Prompt the user for a directory to use as the parent directory
    msg = N_('Select a parent directory for the new clone')
    dirname = qtutils.opendir_dialog(msg, main.model().getcwd())
    if not dirname:
        return None
    count = 1
    destdir = os.path.join(dirname, default)
    olddestdir = destdir
    if core.exists(destdir):
        # An existing path can be specified
        msg = (N_('"%s" already exists, cola will create a new directory') %
               destdir)
        Interaction.information(N_('Directory Exists'), msg)

    # Make sure the new destdir doesn't exist
    while core.exists(destdir):
        destdir = olddestdir + str(count)
        count += 1

    return url, destdir


def export_patches():
    """Run 'git format-patch' on a list of commits."""
    revs, summaries = gitcmds.log_helper()
    to_export = select_commits(N_('Export Patches'), revs, summaries)
    if not to_export:
        return
    cmds.do(cmds.FormatPatch, reversed(to_export), reversed(revs))


def diff_expression():
    """Diff using an arbitrary expression."""
    tracked = gitcmds.tracked_branch()
    current = gitcmds.current_branch()
    if tracked and current:
        ref = tracked + '..' + current
    else:
        ref = 'origin/master..'
    difftool.diff_expression(qtutils.active_window(), ref)


def open_repo():
    dirname = qtutils.opendir_dialog(N_('Open Git Repository...'),
                                     main.model().getcwd())
    if not dirname:
        return
    cmds.do(cmds.OpenRepo, dirname)


def open_repo_in_new_window():
    """Spawn a new cola session."""
    dirname = qtutils.opendir_dialog(N_('Open Git Repository...'),
                                     main.model().getcwd())
    if not dirname:
        return
    cmds.do(cmds.OpenNewRepo, dirname)


def load_commitmsg():
    """Load a commit message from a file."""
    filename = qtutils.open_file(N_('Load Commit Message'),
                                 directory=main.model().getcwd())
    if filename:
        cmds.do(cmds.LoadCommitMessageFromFile, filename)


def choose_from_dialog(get, title, button_text, default):
    parent = qtutils.active_window()
    return get(title, button_text, parent, default=default)


def choose_ref(title, button_text, default=None):
    return choose_from_dialog(completion.GitRefDialog.get,
                              title, button_text, default)


def choose_branch(title, button_text, default=None):
    return choose_from_dialog(completion.GitBranchDialog.get,
                              title, button_text, default)


def choose_remote_branch(title, button_text, default=None):
    return choose_from_dialog(completion.GitRemoteBranchDialog.get,
                              title, button_text, default)


def review_branch():
    """Diff against an arbitrary revision, branch, tag, etc."""
    branch = choose_ref(N_('Select Branch to Review'), N_('Review'))
    if not branch:
        return
    merge_base = gitcmds.merge_base_parent(branch)
    difftool.diff_commits(qtutils.active_window(), merge_base, branch)


class TaskRunner(QtCore.QObject):
    """Runs QRunnable instances and transfers control when they finish"""

    def __init__(self, parent):
        QtCore.QObject.__init__(self, parent)
        self.tasks = []
        self.task_details = {}
        self.connect(self, Task.FINISHED, self.finish)

    def start(self, task, progress=None, finish=None):
        """Start the task and register a callback"""
        if progress is not None:
            progress.show()
        # prevents garbage collection bugs in certain PyQt4 versions
        self.tasks.append(task)
        task_id = id(task)
        self.task_details[task_id] = (progress, finish)
        QtCore.QThreadPool.globalInstance().start(task)

    def finish(self, task, *args, **kwargs):
        task_id = id(task)
        try:
            self.tasks.remove(task)
        except:
            pass
        try:
            progress, finish = self.task_details[task_id]
            del self.task_details[task_id]
        except KeyError:
            finish = progress = None

        if progress is not None:
            progress.hide()

        if finish is not None:
            finish(task, *args, **kwargs)


class Task(QtCore.QRunnable):
    """Base class for concrete tasks"""

    FINISHED = SIGNAL('finished')

    def __init__(self, sender):
        QtCore.QRunnable.__init__(self)
        self.sender = sender

    def finish(self, *args, **kwargs):
        self.sender.emit(self.FINISHED, self, *args, **kwargs)


class CloneTask(Task):
    """Clones a Git repository"""

    def __init__(self, sender, url, destdir, spawn):
        Task.__init__(self, sender)
        self.url = url
        self.destdir = destdir
        self.spawn = spawn
        self.cmd = None

    def run(self):
        """Runs the model action and captures the result"""
        self.cmd = cmds.do(cmds.Clone, self.url, self.destdir,
                           spawn=self.spawn)
        self.finish()


def clone_repo(task_runner, progress, finish, spawn):
    """Clone a repostiory asynchronously with progress animation"""
    result = prompt_for_clone()
    if result is None:
        return
    # Use a thread to update in the background
    url, destdir = result
    progress.set_details(N_('Clone Repository'),
                         N_('Cloning repository at %s') % url)
    task = CloneTask(task_runner, url, destdir, spawn)
    task_runner.start(task,
                      finish=finish,
                      progress=progress)


def report_clone_repo_errors(task):
    """Report errors from the clone task if they exist"""
    if task.cmd is None or task.cmd.ok:
        return
    Interaction.critical(task.cmd.error_message,
                         message=task.cmd.error_message,
                         details=task.cmd.error_details)

def rename_branch():
    """Launch the 'Rename Branch' dialogs."""
    branch = choose_branch(N_('Rename Existing Branch'), N_('Select'))
    if not branch:
        return
    new_branch = choose_branch(N_('Enter Branch New Name'), N_('Rename'))
    if not new_branch:
        return
    cmds.do(cmds.RenameBranch, branch, new_branch)
