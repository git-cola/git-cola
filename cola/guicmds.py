import os

from qtpy import QtGui

from . import cmds
from . import core
from . import difftool
from . import display
from . import gitcmds
from . import icons
from . import qtutils
from . import resources
from .i18n import N_
from .interaction import Interaction
from .widgets import completion
from .widgets import editremotes
from .widgets import switcher
from .widgets.browse import BrowseBranch
from .widgets.selectcommits import select_commits
from .widgets.selectcommits import select_commits_and_output


def copy_commit_id_to_clipboard(context):
    """Copy the current commit ID to the clipboard"""
    status, commit_id, _ = context.git.rev_parse('HEAD')
    if status == 0 and commit_id:
        qtutils.set_clipboard(commit_id)


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


def checkout_branch(context, default=None):
    """Launch the 'Checkout Branch' dialog."""
    branch = choose_potential_branch(
        context, N_('Checkout Branch'), N_('Checkout'), default=default
    )
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
    """Create a new repository and open it"""
    dirname = new_repo(context)
    if not dirname:
        return
    cmds.do(cmds.OpenRepo, context, dirname)


def new_bare_repo(context):
    """Create a bare repository and configure a remote pointing to it"""
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
    """Prompt for a directory and name for a new bare repository"""
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
        output=to_export_and_output['output'],
    )


def diff_against_commit(context):
    """Diff against any commit and checkout changes using the Diff Editor"""
    icon = icons.compare()
    ref = choose_ref(context, N_('Diff Against Commit'), N_('Diff'), icon=icon)
    if not ref:
        return
    cmds.do(cmds.DiffAgainstCommitMode, context, ref)


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
    """Open a repository in the current window"""
    model = context.model
    dirname = qtutils.opendir_dialog(N_('Open Git Repository'), model.getcwd())
    if not dirname:
        return
    cmds.do(cmds.OpenRepo, context, dirname)


def open_repo_in_new_window(context):
    """Spawn a new cola session."""
    model = context.model
    dirname = qtutils.opendir_dialog(N_('Open Git Repository'), model.getcwd())
    if not dirname:
        return
    cmds.do(cmds.OpenNewRepo, context, dirname)


def open_quick_repo_search(context, open_repo=True, parent=None):
    """Open a Quick Repository Search dialog"""
    if parent is None:
        parent = qtutils.active_window()
    settings = context.settings
    items = settings.bookmarks + settings.recent

    if items:
        cfg = context.cfg
        default_repo = cfg.get('cola.defaultrepo')

        entries = QtGui.QStandardItemModel()
        added = set()
        normalize = display.normalize_path
        star_icon = icons.star()
        folder_icon = icons.folder()

        for item in items:
            key = normalize(item['path'])
            if key in added:
                continue

            name = item['name']
            if default_repo == item['path']:
                icon = star_icon
            else:
                icon = folder_icon

            entry = switcher.switcher_item(key, icon, name)
            entries.appendRow(entry)
            added.add(key)

        title = N_('Quick Open Repository')
        place_holder = N_('Search repositories by name...')
        if open_repo:
            open_cmd = cmds.OpenRepo
        else:
            open_cmd = cmds.NoOp

        return switcher.switcher_inner_view(
            context,
            entries,
            title,
            place_holder=place_holder,
            enter_action=lambda entry: cmds.do(open_cmd, context, entry.key),
            parent=parent,
        )
    return None


def load_commitmsg(context):
    """Load a commit message from a file."""
    model = context.model
    filename = qtutils.open_file(N_('Load Commit Message'), directory=model.getcwd())
    if filename:
        cmds.do(cmds.LoadCommitMessageFromFile, context, filename)


def choose_from_dialog(get, context, title, button_text, default, icon=None):
    """Choose a value from a dialog using the `get` method"""
    parent = qtutils.active_window()
    return get(context, title, button_text, parent, default=default, icon=icon)


def choose_ref(context, title, button_text, default=None, icon=None):
    """Choose a Git ref and return it"""
    return choose_from_dialog(
        completion.GitRefDialog.get, context, title, button_text, default, icon=icon
    )


def choose_branch(context, title, button_text, default=None, icon=None):
    """Choose a branch and return either the chosen branch or an empty value"""
    return choose_from_dialog(
        completion.GitBranchDialog.get, context, title, button_text, default, icon=icon
    )


def choose_potential_branch(context, title, button_text, default=None, icon=None):
    """Choose a "potential" branch for checking out.

    This dialog includes remote branches from which new local branches can be created.
    """
    return choose_from_dialog(
        completion.GitCheckoutBranchDialog.get,
        context,
        title,
        button_text,
        default,
        icon=icon,
    )


def choose_remote_branch(context, title, button_text, default=None, icon=None):
    """Choose a remote branch"""
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
    """Run "git reset --soft" to reset the branch HEAD"""
    title = N_('Reset Branch (Soft)')
    ok_text = N_('Reset Branch')
    default = context.settings.get_value('reset::soft', 'ref', default='HEAD^')
    ref = choose_ref(context, title, ok_text, default=default)
    if ref:
        cmds.do(cmds.ResetSoft, context, ref)
        context.settings.set_value('reset::soft', 'ref', ref)


def reset_mixed(context):
    """Run "git reset --mixed" to reset the branch HEAD and staging area"""
    title = N_('Reset Branch and Stage (Mixed)')
    ok_text = N_('Reset')
    default = context.settings.get_value('reset::mixed', 'ref', default='HEAD^')
    ref = choose_ref(context, title, ok_text, default=default)
    if ref:
        cmds.do(cmds.ResetMixed, context, ref)
        context.settings.set_value('reset::mixed', 'ref', ref)


def reset_keep(context):
    """Run "git reset --keep" safe reset to avoid clobbering local changes"""
    title = N_('Reset All (Keep Unstaged Changes)')
    default = context.settings.get_value('reset::keep', 'ref', default='HEAD^')
    ref = choose_ref(context, title, N_('Reset and Restore'), default=default)
    if ref:
        cmds.do(cmds.ResetKeep, context, ref)
        context.settings.set_value('reset::keep', 'ref', ref)


def reset_merge(context):
    """Run "git reset --merge" to reset the working tree and staging area

    The staging area is allowed to carry forward unmerged index entries,
    but if any unstaged changes would be clobbered by the reset then the
    reset is aborted.
    """
    title = N_('Restore Worktree and Reset All (Merge)')
    ok_text = N_('Reset and Restore')
    default = context.settings.get_value('reset::merge', 'ref', default='HEAD^')
    ref = choose_ref(context, title, ok_text, default=default)
    if ref:
        cmds.do(cmds.ResetMerge, context, ref)
        context.settings.set_value('reset::merge', 'ref', ref)


def reset_hard(context):
    """Run "git reset --hard" to fully reset the working tree and staging area"""
    title = N_('Restore Worktree and Reset All (Hard)')
    ok_text = N_('Reset and Restore')
    default = context.settings.get_value('reset::hard', 'ref', default='HEAD^')
    ref = choose_ref(context, title, ok_text, default=default)
    if ref:
        cmds.do(cmds.ResetHard, context, ref)
        context.settings.set_value('reset::hard', 'ref', ref)


def restore_worktree(context):
    """Restore the worktree to the content from the specified commit"""
    title = N_('Restore Worktree')
    ok_text = N_('Restore Worktree')
    default = context.settings.get_value('restore::worktree', 'ref', default='HEAD^')
    ref = choose_ref(context, title, ok_text, default=default)
    if ref:
        cmds.do(cmds.RestoreWorktree, context, ref)
        context.settings.set_value('restore::worktree', 'ref', ref)


def build_layout_menu(widget, menu):
    """Add layouts from ~/.config/git-cola/layouts to the specified menu"""
    directory = resources.xdg_config_home('git-cola', 'layouts')
    if os.path.isdir(directory):
        layouts = sorted(os.listdir(directory))
    else:
        layouts = []
    suffix = '.layout'
    if layouts:
        menu.addSeparator()
    for layout in layouts:
        if layout.endswith(suffix):
            layout_name = layout[: -len(suffix)]
        else:
            layout_name = layout
        layout_filename = os.path.join(directory, layout)
        load_layout_action = qtutils.add_action(
            widget,
            layout_name,
            lambda filename=layout_filename: load_layout_file(widget, filename),
        )
        menu.addAction(load_layout_action)


def save_layout(widget):
    """Save the current widget layout to a file"""
    default_filename = resources.xdg_config_home(
        'git-cola', 'layouts', 'default.layout'
    )
    parent_dir = os.path.dirname(default_filename)
    if not os.path.isdir(parent_dir):
        os.makedirs(parent_dir)
    filename = qtutils.save_as(default_filename)
    if not filename:
        return
    state = widget.layout_state()
    with open(filename, 'wb') as output:
        output.write(state)


def load_layout(widget):
    """Choose a Qt layout file and apply it to the current widget"""
    directory = resources.xdg_config_home('git-cola', 'layouts')
    if not os.path.isdir(directory):
        os.makedirs(directory)
    filename = qtutils.existing_file(directory, title=N_('Load Layout'))
    load_layout_file(widget, filename)


def load_layout_file(widget, filename):
    """Load a Qt layout file into the specified widget"""
    if not filename or not os.path.isfile(filename):
        return
    with open(filename, 'rb') as handle:
        state = handle.read()
    if state:
        widget.apply_layout(state)


def install():
    """Install the GUI-model interaction hooks"""
    Interaction.choose_ref = staticmethod(choose_ref)
