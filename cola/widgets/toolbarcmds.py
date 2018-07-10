# encoding: utf-8
from __future__ import absolute_import, division, unicode_literals

from .. import cmds
from .. import guicmds
from ..widgets import browse
from ..widgets import compare
from ..widgets import createbranch
from ..widgets import createtag
from ..widgets import dag
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
        'context': False,
        'action': cmds.run(cmds.LaunchEditor),
        'icon': 'edit'
    },
    'Others::RevertUnstagedEdits': {
        'title': 'Revert Unstaged Edits...',
        'context': False,
        'action': cmds.run(cmds.RevertUnstagedEdits),
        'icon': 'undo'
    },
    'File::NewRepo': {
        'title': 'New Repository...',
        'context': False,
        'action': guicmds.open_new_repo,
        'icon': 'new'
    },
    'File::OpenRepo': {
        'title': 'Open...',
        'context': False,
        'action': guicmds.open_repo,
        'icon': 'folder'
    },
    'File::OpenRepoNewWindow': {
        'title': 'Open in New Window...',
        'context': False,
        'action': guicmds.open_repo_in_new_window,
        'icon': 'folder'
    },
    # 'File::CloneRepo': {
    #     'title': 'Clone...',
    #     'context': False,
    #     'action': lambda: app().activeWindow().clone_repo(),
    #     'icon': 'repo'
    # },
    'File::Refresh': {
        'title': 'Refresh...',
        'context': False,
        'action': cmds.run(cmds.Refresh),
        'icon': 'sync'
    },
    'File::FindFiles': {
        'title': 'Find Files',
        'context': False,
        'action': finder.finder,
        'icon': 'zoom_in'
    },
    'File::EditRemotes': {
        'title': 'Edit Remotes...',
        'context': False,
        'action': editremotes.editor,
        'icon': None
    },
    'File::RecentModified': {
        'title': 'Recently Modified Files...',
        'context': False,
        'action': recent.browse_recent_files,
        'icon': None
    },
    'File::ApplyPatches': {
        'title': 'Apply Patches...',
        'context': False,
        'action': patch.apply_patches,
        'icon': None
    },
    'File::ExportPatches': {
        'title': 'Export Patches...',
        'context': False,
        'action': guicmds.export_patches,
        'icon': None
    },
    # 'File::SaveAsTarZip': {
    #     'title': 'Save As Tarball/Zip...',
    #     'context': False,
    #     'action': lambda: app().activeWindow().save_archive(),
    #     'icon': 'file_zip'
    # },
    # 'File::Preferences': {
    #     'title': 'Preferences',
    #     'context': False,
    #     'action': lambda: app().activeWindow().preferences(),
    #     'icon': 'configure'
    # },
    'Actions::Fetch': {
        'title': 'Fetch...',
        'context': False,
        'action': remote.fetch,
        'icon': None
    },
    'Actions::Pull': {
        'title': 'Pull...',
        'context': False,
        'action': remote.pull,
        'icon': 'pull'
    },
    'Actions::Push': {
        'title': 'Push...',
        'context': False,
        'action': remote.push,
        'icon': 'push'
    },
    'Actions::Stash': {
        'title': 'Stash...',
        'action': stash.view,
        'icon': None
    },
    'Actions::CreateTag': {
        'title': 'Create Tag...',
        'context': False,
        'action': createtag.create_tag,
        'icon': 'tag'
    },
    'Actions::CherryPick': {
        'title': 'Cherry-Pick...',
        'context': False,
        'action': guicmds.cherry_pick,
        'icon': None
    },
    'Actions::Merge': {
        'title': 'Merge...',
        'context': False,
        'action': merge.local_merge,
        'icon': 'merge'
    },
    'Actions::AbortMerge': {
        'title': 'Abort Merge...',
        'context': False,
        'action': cmds.run(cmds.AbortMerge),
        'icon': None
    },
    'Actions::ResetBrachHead': {
        'title': 'Reset Branch Head',
        'context': False,
        'action': guicmds.reset_branch_head,
        'icon': None
    },
    'Actions::ResetWorktree': {
        'title': 'Reset Worktree',
        'context': False,
        'action': guicmds.reset_worktree,
        'icon': None
    },
    'Actions::Grep': {
        'title': 'Grep',
        'context': False,
        'action': grep.grep,
        'icon': None
    },
    'Actions::Search': {
        'title': 'Search...',
        'context': False,
        'action': search.search,
        'icon': 'search'
    },
    # TODO convert ActionButtons::stage() into a StageSelected command
    'Commit::Stage': {
        'title': 'Stage',
        'context': False,
        'action': cmds.run(cmds.StageOrUnstage),
        'icon': 'add'
    },
    'Commit::AmendLast': {
        'title': 'Amend Last Commit',
        'context': False,
        'action': cmds.run(cmds.AmendMode, True),
        'icon': None
    },
    'Commit::StageAll': {
        'title': 'Stage All Untracked',
        'context': False,
        'action': cmds.run(cmds.StageUntracked),
        'icon': None
    },
    'Commit::UnstageAll': {
        'title': 'Unstage All',
        'context': False,
        'action': cmds.run(cmds.UnstageAll),
        'icon': None
    },
    'Commit::Unstage': {
        'title': 'Unstage',
        'context': False,
        'action': cmds.run(cmds.UnstageSelected),
        'icon': 'remove'
    },
    'Commit::LoadCommitMessage': {
        'title': 'Load Commit Message...',
        'context': False,
        'action': guicmds.load_commitmsg,
        'icon': None
    },
    'Commit::GetCommitMessageTemplate': {
        'title': 'Get Commit Message Template',
        'context': False,
        'action': cmds.run(cmds.LoadCommitMessageFromTemplate),
        'icon': None
    },
    'Diff::Difftool': {
        'title': 'Launch Diff tool',
        'context': False,
        'action': cmds.run(cmds.LaunchDifftool),
        'icon': 'diff'
    },
    'Diff::Expression': {
        'title': 'Expression...',
        'action': lambda context: guicmds.diff_expression(context=context),
        'icon': None
    },
    'Diff::Branches': {
        'title': 'Branches...',
        'context': False,
        'action': compare.compare_branches,
        'icon': None
    },
    'Diff::Diffstat': {
        'title': 'Diffstat',
        'context': False,
        'action': cmds.run(cmds.Diffstat),
        'icon': None
    },
    'Branch::Review': {
        'title': 'Review...',
        'action': lambda context: guicmds.review_branch(context=context),
        'icon': None
    },
    'Branch::Create': {
        'title': 'Create...',
        'context': False,
        'action': createbranch.create_new_branch,
        'icon': None
    },
    'Branch::Checkout': {
        'title': 'Checkout...',
        'context': False,
        'action': guicmds.checkout_branch,
        'icon': None
    },
    'Branch::Delete': {
        'title': 'Delete...',
        'context': False,
        'action': guicmds.delete_branch,
        'icon': None
    },
    'Branch::DeleteRemote': {
        'title': 'Delete Remote Branch...',
        'context': False,
        'action': guicmds.delete_remote_branch,
        'icon': None
    },
    'Branch::Rename': {
        'title': 'Rename Branch...',
        'context': False,
        'action': guicmds.rename_branch,
        'icon': None
    },
    'Branch::BrowseCurrent': {
        'title': 'Browse Current Branch...',
        'context': False,
        'action': guicmds.browse_current,
        'icon': None
    },
    'Branch::BrowseOther': {
        'title': 'Browse Other Branch...',
        'context': False,
        'action': guicmds.browse_other,
        'icon': None
    },
    'Branch::VisualizeCurrent': {
        'title': 'Visualize Current Branch...',
        'context': False,
        'action': cmds.run(cmds.VisualizeCurrent),
        'icon': None
    },
    'Branch::VisualizeAll': {
        'title': 'Visualize All Branches...',
        'context': False,
        'action': cmds.run(cmds.VisualizeAll),
        'icon': None
    },
    'View::FileBrowser': {
        'title': 'File Browser...',
        'context': False,
        'action': lambda: browse.worktree_browser(show=True),
        'icon': 'cola'
    },
    'View::DAG': {
        'title': 'DAG...',
        'action': lambda context: dag.git_dag(context, show=True),
        'icon': 'cola'
    },
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
