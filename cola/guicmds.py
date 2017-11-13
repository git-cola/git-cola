from __future__ import division, absolute_import, unicode_literals
import os
import re

from .i18n import N_
from .interaction import Interaction
from .models import main
from .widgets import completion
from .widgets.browse import BrowseBranch
from .widgets.selectcommits import select_commits
from .widgets.selectcommits import select_commits_and_output
from . import cmds
from . import core
from . import difftool
from . import gitcmds
from . import icons
from . import qtutils
from . import utils
from . import git


def delete_branch():
    """Launch the 'Delete Branch' dialog."""
    icon = icons.discard()
    branch = choose_branch(N_('Delete Branch'), N_('Delete'), icon=icon)
    if not branch:
        return
    cmds.do(cmds.DeleteBranch, branch)


def delete_remote_branch():
    """Launch the 'Delete Remote Branch' dialog."""
    branch = choose_remote_branch(N_('Delete Remote Branch'), N_('Delete'),
                                  icon=icons.discard())
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
    BrowseBranch.browse(branch)


def browse_other():
    """Prompt for a branch and inspect content at that point in time."""
    # Prompt for a branch to browse
    branch = choose_ref(N_('Browse Commits...'), N_('Browse'))
    if not branch:
        return
    BrowseBranch.browse(branch)


def checkout_branch():
    """Launch the 'Checkout Branch' dialog."""
    branch = choose_potential_branch(N_('Checkout Branch'), N_('Checkout'))
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
    path = qtutils.opendir_dialog(N_('New Repository...'), core.getcwd())
    if not path:
        return None
    # Avoid needlessly calling `git init`.
    if git.is_git_worktree(path) or git.is_git_dir(path):
        # We could prompt here and confirm that they really didn't
        # mean to open an existing repository, but I think
        # treating it like an "Open" is a sensible DWIM answer.
        return path

    status, out, err = core.run_command(['git', 'init', path])
    if status == 0:
        return path
    else:
        title = N_('Error Creating Repository')
        Interaction.command_error(title, 'git init', status, out, err)
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
    to_export_and_output = select_commits_and_output(N_('Export Patches'), revs,
                                                     summaries)
    if not to_export_and_output['to_export']:
        return

    cmds.do(cmds.FormatPatch, reversed(to_export_and_output['to_export']),
            reversed(revs), to_export_and_output['output'])


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


def choose_from_dialog(get, title, button_text, default, icon=None):
    parent = qtutils.active_window()
    return get(title, button_text, parent, default=default, icon=icon)


def choose_ref(title, button_text, default=None, icon=None):
    return choose_from_dialog(completion.GitRefDialog.get,
                              title, button_text, default, icon=icon)


def choose_branch(title, button_text, default=None, icon=None):
    return choose_from_dialog(completion.GitBranchDialog.get,
                              title, button_text, default, icon=icon)


def choose_potential_branch(title, button_text, default=None, icon=None):
    return choose_from_dialog(completion.GitPotentialBranchDialog.get,
                              title, button_text, default, icon=icon)


def choose_remote_branch(title, button_text, default=None, icon=None):
    return choose_from_dialog(completion.GitRemoteBranchDialog.get,
                              title, button_text, default, icon=icon)


def review_branch():
    """Diff against an arbitrary revision, branch, tag, etc."""
    branch = choose_ref(N_('Select Branch to Review'), N_('Review'))
    if not branch:
        return
    merge_base = gitcmds.merge_base_parent(branch)
    difftool.diff_commits(qtutils.active_window(), merge_base, branch)


class CloneTask(qtutils.Task):
    """Clones a Git repository"""

    def __init__(self, url, destdir, spawn, parent):
        qtutils.Task.__init__(self, parent)
        self.url = url
        self.destdir = destdir
        self.spawn = spawn
        self.cmd = None

    def task(self):
        """Runs the model action and captures the result"""
        self.cmd = cmds.do(cmds.Clone, self.url, self.destdir, spawn=self.spawn)
        return self.cmd


def clone_repo(parent, runtask, progress, finish, spawn):
    """Clone a repository asynchronously with progress animation"""
    result = prompt_for_clone()
    if result is None:
        return
    # Use a thread to update in the background
    url, destdir = result
    progress.set_details(N_('Clone Repository'),
                         N_('Cloning repository at %s') % url)
    task = CloneTask(url, destdir, spawn, parent)
    runtask.start(task, finish=finish, progress=progress)


def report_clone_repo_errors(task):
    """Report errors from the clone task if they exist"""
    cmd = task.cmd
    if cmd is None:
        return
    status = cmd.status
    out = cmd.out
    err = cmd.err
    title = N_('Error: could not clone "%s"') % task.cmd.url
    Interaction.command(title, 'git clone', status, out, err)


def rename_branch():
    """Launch the 'Rename Branch' dialogs."""
    branch = choose_branch(N_('Rename Existing Branch'), N_('Select'))
    if not branch:
        return
    new_branch = choose_branch(N_('Enter New Branch Name'), N_('Rename'))
    if not new_branch:
        return
    cmds.do(cmds.RenameBranch, branch, new_branch)


def reset_branch_head():
    ref = choose_ref(N_('Reset Branch Head'), N_('Reset'), default='HEAD^')
    if ref:
        cmds.do(cmds.ResetBranchHead, ref)


def reset_worktree():
    ref = choose_ref(N_('Reset Worktree'), N_('Reset'))
    if ref:
        cmds.do(cmds.ResetWorktree, ref)
