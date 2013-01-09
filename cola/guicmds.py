import os

import cola
from cola import cmds
from cola import core
from cola import difftool
from cola import gitcmds
from cola import qt
from cola import qtutils
from cola.git import git
from cola.interaction import Interaction
from cola.widgets.browse import BrowseDialog
from cola.widgets.combodlg import ComboDialog
from cola.widgets.grep import run_grep
from cola.widgets.selectcommits import select_commits


def choose_from_combo(title, items):
    """Quickly choose an item from a list using a combo box"""
    return ComboDialog(qtutils.active_window(), title=title, items=items).selected()


def branch_delete():
    """Launch the 'Delete Branch' dialog."""
    branch = choose_from_combo('Delete Branch',
                               cola.model().local_branches)
    if not branch:
        return
    cmds.do(cmds.DeleteBranch, branch)


def diff_revision():
    """Diff an arbitrary revision against the worktree"""
    ref = choose_ref('Select Revision to Diff', 'Diff',
                     default='HEAD^')
    if not ref:
        return
    difftool.diff_commits(qtutils.active_window(), ref, None)


def browse_current():
    """Launch the 'Browse Current Branch' dialog."""
    branch = gitcmds.current_branch()
    BrowseDialog.browse(branch)


def browse_other():
    """Prompt for a branch and inspect content at that point in time."""
    # Prompt for a branch to browse
    branch = choose_from_combo('Browse Revision...', gitcmds.all_refs())
    if not branch:
        return
    BrowseDialog.browse(branch)


def checkout_branch():
    """Launch the 'Checkout Branch' dialog."""
    branch = choose_from_combo('Checkout Branch',
                               cola.model().local_branches)
    if not branch:
        return
    cmds.do(cmds.CheckoutBranch, branch)


def cherry_pick():
    """Launch the 'Cherry-Pick' dialog."""
    revs, summaries = gitcmds.log_helper(all=True)
    commits = select_commits('Cherry-Pick Commit',
                             revs, summaries, multiselect=False)
    if not commits:
        return
    cmds.do(cmds.CherryPick, commits)


def clone_repo(spawn=True):
    """
    Present GUI controls for cloning a repository

    A new cola session is invoked when 'spawn' is True.

    """
    url, ok = qtutils.prompt('Path or URL to clone (Env. $VARS okay)')
    url = os.path.expandvars(core.encode(url))
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
            default = os.path.basename(os.getcwd())
        if not default:
            raise
    except:
        Interaction.information(
                'Error Cloning',
                'Could not parse: "%s"' % url)
        Interaction.log('Oops, could not parse git url: "%s"' % url)
        return None

    # Prompt the user for a directory to use as the parent directory
    msg = 'Select a parent directory for the new clone'
    dirname = qtutils.opendir_dialog(msg, cola.model().getcwd())
    if not dirname:
        return None
    count = 1
    dirname = core.decode(dirname)
    destdir = os.path.join(dirname, core.decode(default))
    olddestdir = destdir
    if os.path.exists(destdir):
        # An existing path can be specified
        msg = ('"%s" already exists, cola will create a new directory' %
               destdir)
        Interaction.information('Directory Exists', msg)

    # Make sure the new destdir doesn't exist
    while os.path.exists(destdir):
        destdir = olddestdir + str(count)
        count += 1
    if cmds.do(cmds.Clone, core.decode(url), destdir, spawn=spawn):
        return destdir
    return None


def export_patches():
    """Run 'git format-patch' on a list of commits."""
    revs, summaries = gitcmds.log_helper()
    to_export = select_commits('Export Patches', revs, summaries)
    if not to_export:
        return
    to_export.reverse()
    revs.reverse()
    cmds.do(cmds.FormatPatch, to_export, revs)


def diff_expression():
    """Diff using an arbitrary expression."""
    tracked = gitcmds.tracked_branch()
    current = gitcmds.current_branch()
    if tracked and current:
        default = tracked + '..' + current
    else:
        default = 'origin/master..'
    ref = choose_ref('Enter Diff Expression', 'Diff',
                     default=default)
    if not ref:
        return
    difftool.diff_expression(qtutils.active_window(), ref)


def grep():
    """Prompt and use 'git grep' to find the content."""
    widget = run_grep(parent=qtutils.active_window())
    widget.show()
    widget.raise_()
    return widget


def open_repo():
    """Spawn a new cola session."""
    dirname = qtutils.opendir_dialog('Open Git Repository...',
                                     cola.model().getcwd())
    if not dirname:
        return
    cmds.do(cmds.OpenRepo, dirname)


def load_commitmsg():
    """Load a commit message from a file."""
    filename = qtutils.open_dialog('Load Commit Message...',
                                   cola.model().getcwd())
    if filename:
        cmds.do(cmds.LoadCommitMessage, filename)


def rebase():
    """Rebase onto a branch."""
    branch = choose_from_combo('Rebase Branch',
                               cola.model().all_branches())
    if not branch:
        return
    #TODO cmd
    status, output = git.rebase(branch, with_stderr=True, with_status=True)
    Interaction.log_status(status, output, '')


def choose_ref(title, button_text, default=None):
    parent = qtutils.active_window()
    return qt.GitRefDialog.ref(title, button_text, parent, default=default)


def review_branch():
    """Diff against an arbitrary revision, branch, tag, etc."""
    branch = choose_ref('Select Branch to Review', 'Review')
    if not branch:
        return
    merge_base = gitcmds.merge_base_parent(branch)
    difftool.diff_commits(qtutils.active_window(), merge_base, branch)
