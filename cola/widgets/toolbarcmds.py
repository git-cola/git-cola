# encoding: utf-8
from __future__ import absolute_import, division, unicode_literals

from .. import cmds
from .. import guicmds
from ..widgets import action
from ..widgets import browse
from ..widgets import compare
from ..widgets import createbranch
from ..widgets import createtag
from ..widgets import editremotes
from ..widgets import finder
from ..widgets import grep
from ..widgets import merge
from ..widgets import patch
from ..widgets import recent
from ..widgets import remote
from ..widgets import search
from ..widgets import stash

COMMANDS = {
    'Others::LaunchEditor': {
        'title': 'Launch Editor',
        'action': cmds.run(cmds.LaunchEditor),
        'icon': 'edit'
    },
    'Others::RevertUnstagedEdits': {
        'title': 'Revert Unstaged Edits...',
        'action': cmds.run(cmds.RevertUnstagedEdits),
        'icon': 'undo'
    },
    'File::NewRepo': {
        'title': 'New Repository...',
        'action': lambda: guicmds.open_new_repo(),
        'icon': 'new'
    },
    'File::OpenRepo': {
        'title': 'Open...',
        'action': lambda: guicmds.open_repo(),
        'icon': 'folder'
    },
    'File::OpenRepoNewWindow': {
        'title': 'Open in New Window...',
        'action': lambda: guicmds.open_repo_in_new_window(),
        'icon': 'folder'
    },
    # 'File::CloneRepo': {
    #     'title': 'Clone...',
    #     'action': lambda: app().activeWindow().clone_repo(),
    #     'icon': 'repo'
    # },
    'File::Refresh': {
        'title': 'Refresh...',
        'action': cmds.run(cmds.Refresh),
        'icon': 'sync'
    },
    'File::FindFiles': {
        'title': 'Find Files',
        'action': lambda: finder.finder(),
        'icon': 'zoom_in'
    },
    'File::EditRemotes': {
        'title': 'Edit Remotes...',
        'action': lambda: editremotes.remote_editor().exec_(),
        'icon': None
    },
    'File::RecentModified': {
        'title': 'Recently Modified Files...',
        'action': lambda: recent.browse_recent_files(),
        'icon': None
    },
    'File::ApplyPatches': {
        'title': 'Apply Patches...',
        'action': lambda: patch.apply_patches(),
        'icon': None
    },
    'File::ExportPatches': {
        'title': 'Export Patches...',
        'action': lambda: guicmds.export_patches(),
        'icon': None
    },
    # 'File::SaveAsTarZip': {
    #     'title': 'Save As Tarball/Zip...',
    #     'action': lambda: app().activeWindow().save_archive(),
    #     'icon': 'file_zip'
    # },
    # 'File::Preferences': {
    #     'title': 'Preferences',
    #     'action': lambda: app().activeWindow().preferences(),
    #     'icon': 'configure'
    # },
    'Actions::Fetch': {
        'title': 'Fetch...',
        'action': lambda: remote.fetch(),
        'icon': None
    },
    'Actions::Pull': {
        'title': 'Pull...',
        'action': lambda: remote.pull(),
        'icon': 'pull'
    },
    'Actions::Push': {
        'title': 'Push...',
        'action': lambda: remote.push(),
        'icon': 'push'
    },
    'Actions::Stash': {
        'title': 'Stash...',
        'action': lambda: stash.stash(),
        'icon': None
    },
    'Actions::CreateTag': {
        'title': 'Create Tag...',
        'action': lambda: createtag.create_tag(),
        'icon': 'tag'
    },
    'Actions::CherryPick': {
        'title': 'Cherry-Pick...',
        'action': lambda: guicmds.cherry_pick(),
        'icon': None
    },
    'Actions::Merge': {
        'title': 'Merge...',
        'action': lambda: merge.local_merge(),
        'icon': 'merge'
    },
    'Actions::AbortMerge': {
        'title': 'Abort Merge...',
        'action': lambda: merge.abort_merge(),
        'icon': None
    },
    'Actions::ResetBrachHead': {
        'title': 'Reset Branch Head',
        'action': lambda: guicmds.reset_branch_head(),
        'icon': None
    },
    'Actions::ResetWorktree': {
        'title': 'Reset Worktree',
        'action': lambda: guicmds.reset_worktree(),
        'icon': None
    },
    'Actions::Grep': {
        'title': 'Grep',
        'action': lambda: grep.grep(),
        'icon': None
    },
    'Actions::Search': {
        'title': 'Search...',
        'action': lambda: search.search(),
        'icon': 'search'
    },
    'Commit::Stage': {
        'title': 'Stage',
        'action': cmds.run(cmds.AmendMode, True),
        'icon': 'add'
    },
    'Commit::AmendLast': {
        'title': 'Amend Last Commit',
        'action': lambda: action.ActionButtons.stage(
            action.ActionButtons()),
        'icon': None
    },
    'Commit::StageAll': {
        'title': 'Stage All Untracked',
        'action': cmds.run(cmds.StageUntracked),
        'icon': None
    },
    'Commit::UnsageAll': {
        'title': 'Unstage All',
        'action': cmds.run(cmds.UnstageAll),
        'icon': None
    },
    'Commit::Unstage': {
        'title': 'Unstage',
        'action': lambda: action.ActionButtons.unstage(
            action.ActionButtons()),
        'icon': 'remove'
    },
    'Commit::LoadCommitMessage': {
        'title': 'Load Commit Message...',
        'action': lambda: guicmds.load_commitmsg(),
        'icon': None
    },
    'Commit::GetCommitMessageTemplate': {
        'title': 'Get Commit Message Template',
        'action': cmds.run(cmds.LoadCommitMessageFromTemplate),
        'icon': None
    },
    'Diff::Difftool': {
        'title': 'Launch Diff tool',
        'action': cmds.run(cmds.LaunchDifftool),
        'icon': 'diff'
    },
    'Diff::Expression': {
        'title': 'Expression...',
        'action': lambda: guicmds.diff_expression(),
        'icon': None
    },
    'Diff::Branches': {
        'title': 'Branches...',
        'action': lambda: compare.compare_branches(),
        'icon': None
    },
    'Diff::Diffstat': {
        'title': 'Diffstat',
        'action': cmds.run(cmds.Diffstat),
        'icon': None
    },
    'Branch::Review': {
        'title': 'Review...',
        'action': lambda: guicmds.review_branch(),
        'icon': None
    },
    'Branch::Create': {
        'title': 'Create...',
        'action': lambda: createbranch.create_new_branch(),
        'icon': None
    },
    'Branch::Checkout': {
        'title': 'Checkout...',
        'action': lambda: guicmds.checkout_branch(),
        'icon': None
    },
    'Branch::Delete': {
        'title': 'Delete...',
        'action': lambda: guicmds.delete_branch(),
        'icon': None
    },
    'Branch::DeleteRemote': {
        'title': 'Delete Remote Branch...',
        'action': lambda: guicmds.delete_remote_branch(),
        'icon': None
    },
    'Branch::Rename': {
        'title': 'Rename Branch...',
        'action': lambda: guicmds.rename_branch(),
        'icon': None
    },
    'Branch::BrowseCurrent': {
        'title': 'Browse Current Branch...',
        'action': lambda: guicmds.browse_current(),
        'icon': None
    },
    'Branch::BrowseOther': {
        'title': 'Browse Other Branch...',
        'action': lambda: guicmds.browse_other(),
        'icon': None
    },
    'Branch::VisualizeCurrent': {
        'title': 'Visualize Current Branch...',
        'action': cmds.run(cmds.VisualizeCurrent),
        'icon': None
    },
    'Branch::VisualizeAll': {
        'title': 'Visualize All Branches...',
        'action': cmds.run(cmds.VisualizeAll),
        'icon': None
    },
    'View::FileBrowser': {
        'title': 'File Browser...',
        'action': lambda: browse.worktree_browser(show=True),
        'icon': 'cola'
    },
    # 'View::DAG': {
    #     'title': 'DAG...',
    #     'action': lambda: app().activeWindow().git_dag(),
    #     'icon': 'cola'
    # }
}
#     'Rebase::StartInteractive': {
#         'title': 'Start Interactive Rebase...',
#         'action': lambda: app().activeWindow().rebase_start(),
#         'icon': None
#     },
#     'Rebase::Edit': {
#         'title': 'Edit...',
#         'action': lambda: cmds.rebase_edit_todo(),
#         'icon': None
#     },
#     'Rebase::Continue': {
#         'title': 'Continue',
#         'action': lambda: cmds.rebase_continue(),
#         'icon': None
#     },
#     'Rebase::SkipCurrentPatch': {
#         'title': 'Skip Current Patch',
#         'action': lambda: cmds.rebase_skip(),
#         'icon': None
#     },
#     'Rebase::Abort': {
#         'title': 'Abort',
#         'action': lambda: cmds.rebase_abort(),
#         'icon': None
#     }
