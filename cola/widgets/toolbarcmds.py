from __future__ import absolute_import, division, unicode_literals

from .. import cmds
from .. import guicmds
# from ..widgets import archive
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
        'action': guicmds.open_new_repo,
        'icon': 'new'
    },
    'File::OpenRepo': {
        'title': 'Open...',
        'action': guicmds.open_repo,
        'icon': 'folder'
    },
    'File::OpenRepoNewWindow': {
        'title': 'Open in New Window...',
        'action': guicmds.open_repo_in_new_window,
        'icon': 'folder'
    },
    # 'File::CloneRepo': {
    #     'title': 'Clone...',
    #     'action': guicmds.spawn_clone,
    #     'icon': 'repo'
    # },
    'File::Refresh': {
        'title': 'Refresh...',
        'action': cmds.run(cmds.Refresh),
        'icon': 'sync'
    },
    'File::FindFiles': {
        'title': 'Find Files',
        'action': finder.finder,
        'icon': 'zoom_in'
    },
    'File::EditRemotes': {
        'title': 'Edit Remotes...',
        'action': editremotes.editor,
        'icon': None
    },
    'File::RecentModified': {
        'title': 'Recently Modified Files...',
        'action': recent.browse_recent_files,
        'icon': None
    },
    'File::ApplyPatches': {
        'title': 'Apply Patches...',
        'action': patch.apply_patches,
        'icon': None
    },
    'File::ExportPatches': {
        'title': 'Export Patches...',
        'action': guicmds.export_patches,
        'icon': None
    },
    # 'File::SaveAsTarZip': {
    #     'title': 'Save As Tarball/Zip...',
    #     'action': archive.save_archive,
    #     'icon': 'file_zip'
    # },
    # 'File::Preferences': {
    #     'title': 'Preferences',
    #     'action': prefs.preferences,
    #     'icon': 'configure'
    # },
    'Actions::Fetch': {
        'title': 'Fetch...',
        'action': remote.fetch,
        'icon': None
    },
    'Actions::Pull': {
        'title': 'Pull...',
        'action': remote.pull,
        'icon': 'pull'
    },
    'Actions::Push': {
        'title': 'Push...',
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
        'action': createtag.create_tag,
        'icon': 'tag'
    },
    'Actions::CherryPick': {
        'title': 'Cherry-Pick...',
        'action': guicmds.cherry_pick,
        'icon': None
    },
    'Actions::Merge': {
        'title': 'Merge...',
        'action': merge.local_merge,
        'icon': 'merge'
    },
    'Actions::AbortMerge': {
        'title': 'Abort Merge...',
        'action': cmds.run(cmds.AbortMerge),
        'icon': None
    },
    'Actions::UpdateSubmodules': {
        'title': 'Update All Submodules...',
        'action': cmds.run(cmds.SubmodulesUpdate),
        'icon': None
    },
    'Actions::ResetBranchHead': {
        'title': 'Reset Branch Head',
        'action': guicmds.reset_branch_head,
        'icon': None
    },
    'Actions::ResetWorktree': {
        'title': 'Reset Worktree',
        'action': guicmds.reset_worktree,
        'icon': None
    },
    'Actions::Grep': {
        'title': 'Grep',
        'action': grep.grep,
        'icon': None
    },
    'Actions::Search': {
        'title': 'Search...',
        'action': search.search,
        'icon': 'search'
    },
    'Commit::Stage': {
        'title': 'Stage',
        'action': cmds.run(cmds.StageOrUnstage),
        'icon': 'add'
    },
    'Commit::AmendLast': {
        'title': 'Amend Last Commit',
        'action': cmds.run(cmds.AmendMode),
        'icon': None
    },
    'Commit::StageAll': {
        'title': 'Stage All Untracked',
        'action': cmds.run(cmds.StageUntracked),
        'icon': None
    },
    'Commit::UnstageAll': {
        'title': 'Unstage All',
        'action': cmds.run(cmds.UnstageAll),
        'icon': None
    },
    'Commit::Unstage': {
        'title': 'Unstage',
        'action': cmds.run(cmds.UnstageSelected),
        'icon': 'remove'
    },
    'Commit::LoadCommitMessage': {
        'title': 'Load Commit Message...',
        'action': guicmds.load_commitmsg,
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
        'action': guicmds.diff_expression,
        'icon': None
    },
    'Diff::Branches': {
        'title': 'Branches...',
        'action': compare.compare_branches,
        'icon': None
    },
    'Diff::Diffstat': {
        'title': 'Diffstat',
        'action': cmds.run(cmds.Diffstat),
        'icon': None
    },
    'Branch::Review': {
        'title': 'Review...',
        'action': guicmds.review_branch,
        'icon': None
    },
    'Branch::Create': {
        'title': 'Create...',
        'action': createbranch.create_new_branch,
        'icon': None
    },
    'Branch::Checkout': {
        'title': 'Checkout...',
        'action': guicmds.checkout_branch,
        'icon': None
    },
    'Branch::Delete': {
        'title': 'Delete...',
        'action': guicmds.delete_branch,
        'icon': None
    },
    'Branch::DeleteRemote': {
        'title': 'Delete Remote Branch...',
        'action': guicmds.delete_remote_branch,
        'icon': None
    },
    'Branch::Rename': {
        'title': 'Rename Branch...',
        'action': guicmds.rename_branch,
        'icon': None
    },
    'Branch::BrowseCurrent': {
        'title': 'Browse Current Branch...',
        'action': guicmds.browse_current,
        'icon': None
    },
    'Branch::BrowseOther': {
        'title': 'Browse Other Branch...',
        'action': guicmds.browse_other,
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
        'action': browse.worktree_browser,
        'icon': 'cola'
    },
    'View::DAG': {
        'title': 'DAG...',
        'action': dag.git_dag,
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
