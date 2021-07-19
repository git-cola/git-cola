from __future__ import absolute_import, division, print_function, unicode_literals
import os

from . import cmds
from . import core
from . import difftool
from . import gitcmds
from . import icons
from . import qtutils
from .i18n import N_
from .interaction import Interaction
from .widgets import completion
from .widgets import editremotes
from .widgets.browse import BrowseBranch
from .widgets.selectcommits import select_commits
from .widgets.selectcommits import select_commits_and_output


def delete_branch(context):
    """Launch the 'Delete Branch' dialog."""
    icon = icons.discard()
    branch = choose_branch(context, N_('Delete Branch'), N_('Delete'), icon=icon)
    if not branch:
        return
    cmds.do(cmds.DeleteBranch, context, branch)


def delete_remote_branch(context):
    """Launch the 'Delete Remote Branch' dialog."""
    remote_branch = choose_remote_branch(
        context, N_('Delete Remote Branch'), N_('Delete'), icon=icons.discard()
    )
    if not remote_branch:
        return
    remote, branch = gitcmds.parse_remote_branch(remote_branch)
    if remote and branch:
        cmds.do(cmds.DeleteRemoteBranch, context, remote, branch)


def browse_current(context):
    """Launch the 'Browse Current Branch' dialog."""
    branch = gitcmds.current_branch(context)
    BrowseBranch.browse(context, branch)


def browse_other(context):
    """Prompt for a branch and inspect content at that point in time."""
    # Prompt for a branch to browse
    branch = choose_ref(context, N_('Browse Commits...'), N_('Browse'))
    if not branch:
        return
    BrowseBranch.browse(context, branch)


def checkout_branch(context):
    """Launch the 'Checkout Branch' dialog."""
    branch = choose_potential_branch(context, N_('Checkout Branch'), N_('Checkout'))
    if not branch:
        return
    cmds.do(cmds.CheckoutBranch, context, branch)


def cherry_pick(context):
    """Launch the 'Cherry-Pick' dialog."""
    revs, summaries = gitcmds.log_helper(context, all=True)
    commits = select_commits(
        context, N_('Cherry-Pick Commit'), revs, summaries, multiselect=False
    )
    if not commits:
        return
    cmds.do(cmds.CherryPick, context, commits)


def new_repo(context):
    """Prompt for a new directory and create a new Git repository

    :returns str: repository path or None if no repository was created.

    """
    git = context.git
    path = qtutils.opendir_dialog(N_('New Repository...'), core.getcwd())
    if not path:
        return None
    # Avoid needlessly calling `git init`.
    if git.is_git_repository(path):
        # We could prompt here and confirm that they really didn't
        # mean to open an existing repository, but I think
        # treating it like an "Open" is a sensible DWIM answer.
        return path

    status, out, err = git.init(path)
    if status == 0:
        return path

    title = N_('Error Creating Repository')
    Interaction.command_error(title, 'git init', status, out, err)
    return None


def open_new_repo(context):
    dirname = new_repo(context)
    if not dirname:
        return
    cmds.do(cmds.OpenRepo, context, dirname)


def new_bare_repo(context):
    result = None
    repo = prompt_for_new_bare_repo()
    if not repo:
        return result
    # Create bare repo
    ok = cmds.do(cmds.NewBareRepo, context, repo)
    if not ok:
        return result
    # Add a new remote pointing to the bare repo
    parent = qtutils.active_window()
    add_remote = editremotes.add_remote(
        context, parent, name=os.path.basename(repo), url=repo, readonly_url=True
    )
    if add_remote:
        result = repo

    return result


def prompt_for_new_bare_repo():
    path = qtutils.opendir_dialog(N_('Select Directory...'), core.getcwd())
    if not path:
        return None

    bare_repo = None
    default = os.path.basename(core.getcwd())
    if not default.endswith('.git'):
        default += '.git'
    while not bare_repo:
        name, ok = qtutils.prompt(
            N_('Enter a name for the new bare repo'),
            title=N_('New Bare Repository...'),
            text=default,
        )
        if not name or not ok:
            return None
        if not name.endswith('.git'):
            name += '.git'
        repo = os.path.join(path, name)
        if core.isdir(repo):
            Interaction.critical(N_('Error'), N_('"%s" already exists') % repo)
        else:
            bare_repo = repo

    return bare_repo


def export_patches(context):
    """Run 'git format-patch' on a list of commits."""
    revs, summaries = gitcmds.log_helper(context)
    to_export_and_output = select_commits_and_output(
        context, N_('Export Patches'), revs, summaries
    )
    if not to_export_and_output['to_export']:
        return

    cmds.do(
        cmds.FormatPatch,
        context,
        reversed(to_export_and_output['to_export']),
        reversed(revs),
        to_export_and_output['output'],
    )


def diff_expression(context):
    """Diff using an arbitrary expression."""
    tracked = gitcmds.tracked_branch(context)
    current = gitcmds.current_branch(context)
    if tracked and current:
        ref = tracked + '..' + current
    else:
        ref = '@{upstream}..'
    difftool.diff_expression(context, qtutils.active_window(), ref)


def open_repo(context):
    model = context.model
    dirname = qtutils.opendir_dialog(N_('Open Git Repository...'), model.getcwd())
    if not dirname:
        return
    cmds.do(cmds.OpenRepo, context, dirname)


def open_repo_in_new_window(context):
    """Spawn a new cola session."""
    model = context.model
    dirname = qtutils.opendir_dialog(N_('Open Git Repository...'), model.getcwd())
    if not dirname:
        return
    cmds.do(cmds.OpenNewRepo, context, dirname)


def load_commitmsg(context):
    """Load a commit message from a file."""
    model = context.model
    filename = qtutils.open_file(N_('Load Commit Message'), directory=model.getcwd())
    if filename:
        cmds.do(cmds.LoadCommitMessageFromFile, context, filename)


def choose_from_dialog(get, context, title, button_text, default, icon=None):
    parent = qtutils.active_window()
    return get(context, title, button_text, parent, default=default, icon=icon)


def choose_ref(context, title, button_text, default=None, icon=None):
    return choose_from_dialog(
        completion.GitRefDialog.get, context, title, button_text, default, icon=icon
    )


def choose_branch(context, title, button_text, default=None, icon=None):
    return choose_from_dialog(
        completion.GitBranchDialog.get, context, title, button_text, default, icon=icon
    )


def choose_potential_branch(context, title, button_text, default=None, icon=None):
    return choose_from_dialog(
        completion.GitCheckoutBranchDialog.get,
        context,
        title,
        button_text,
        default,
        icon=icon,
    )


def choose_remote_branch(context, title, button_text, default=None, icon=None):
    return choose_from_dialog(
        completion.GitRemoteBranchDialog.get,
        context,
        title,
        button_text,
        default,
        icon=icon,
    )


def review_branch(context):
    """Diff against an arbitrary revision, branch, tag, etc."""
    branch = choose_ref(context, N_('Select Branch to Review'), N_('Review'))
    if not branch:
        return
    merge_base = gitcmds.merge_base_parent(context, branch)
    difftool.diff_commits(context, qtutils.active_window(), merge_base, branch)


def rename_branch(context):
    """Launch the 'Rename Branch' dialogs."""
    branch = choose_branch(context, N_('Rename Existing Branch'), N_('Select'))
    if not branch:
        return
    new_branch = choose_branch(context, N_('Enter New Branch Name'), N_('Rename'))
    if not new_branch:
        return
    cmds.do(cmds.RenameBranch, context, branch, new_branch)


def reset_soft(context):
    title = N_('Reset Branch (Soft)')
    ok_text = N_('Reset Branch')
    ref = choose_ref(context, title, ok_text, default='HEAD^')
    if ref:
        cmds.do(cmds.ResetSoft, context, ref)


def reset_mixed(context):
    title = N_('Reset Branch and Stage (Mixed)')
    ok_text = N_('Reset')
    ref = choose_ref(context, title, ok_text, default='HEAD^')
    if ref:
        cmds.do(cmds.ResetMixed, context, ref)


def reset_keep(context):
    title = N_('Reset All (Keep Unstaged Changes)')
    ref = choose_ref(context, title, N_('Reset and Restore'))
    if ref:
        cmds.do(cmds.ResetKeep, context, ref)


def reset_merge(context):
    title = N_('Restore Worktree and Reset All (Merge)')
    ok_text = N_('Reset and Restore')
    ref = choose_ref(context, title, ok_text, default='HEAD^')
    if ref:
        cmds.do(cmds.ResetMerge, context, ref)


def reset_hard(context):
    title = N_('Restore Worktree and Reset All (Hard)')
    ok_text = N_('Reset and Restore')
    ref = choose_ref(context, title, ok_text, default='HEAD^')
    if ref:
        cmds.do(cmds.ResetHard, context, ref)


def restore_worktree(context):
    title = N_('Restore Worktree')
    ok_text = N_('Restore Worktree')
    ref = choose_ref(context, title, ok_text, default='HEAD^')
    if ref:
        cmds.do(cmds.RestoreWorktree, context, ref)


def install():
    """Install the GUI-model interaction hooks"""
    Interaction.choose_ref = staticmethod(choose_ref)
