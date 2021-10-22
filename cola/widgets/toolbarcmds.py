from __future__ import absolute_import, division, print_function, unicode_literals

from .. import cmds
from .. import guicmds
from ..widgets import archive
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
        'icon': 'edit',
    },
    'Others::RevertUnstagedEdits': {
        'title': 'Revert Unstaged Edits...',
        'action': cmds.run(cmds.RevertUnstagedEdits),
        'icon': 'undo',
    },
    'File::NewRepo': {
        'title': 'New Repository...',
        'action': guicmds.open_new_repo,
        'icon': 'new',
    },
    'File::OpenRepo': {
        'title': 'Open...',
        'action': guicmds.open_repo,
        'icon': 'folder',
    },
    'File::OpenRepoNewWindow': {
        'title': 'Open in New Window...',
        'action': guicmds.open_repo_in_new_window,
        'icon': 'folder',
    },
    # 'File::CloneRepo': {
    #     'title': 'Clone...',
    #     'action': guicmds.spawn_clone,
    #     'icon': 'repo'
    # },
    'File::Refresh': {
        'title': 'Refresh...',
        'action': cmds.run(cmds.Refresh),
        'icon': 'sync',
    },
    'File::FindFiles': {
        'title': 'Find Files',
        'action': finder.finder,
        'icon': 'zoom_in',
    },
    'File::EditRemotes': {
        'title': 'Edit Remotes...',
        'action': editremotes.editor,
        'icon': 'edit',
    },
    'File::RecentModified': {
        'title': 'Recently Modified Files...',
        'action': recent.browse_recent_files,
        'icon': 'edit',
    },
    'File::ApplyPatches': {
        'title': 'Apply Patches...',
        'action': patch.apply_patches,
        'icon': 'diff',
    },
    'File::ExportPatches': {
        'title': 'Export Patches...',
        'action': guicmds.export_patches,
        'icon': 'save',
    },
    'File::SaveAsTarZip': {
        'title': 'Save As Tarball/Zip...',
        'action': archive.save_archive,
        'icon': 'file_zip',
    },
    # 'File::Preferences': {
    #     'title': 'Preferences',
    #     'action': prefs.preferences,
    #     'icon': 'configure'
    # },
    'Actions::Fetch': {'title': 'Fetch...', 'action': remote.fetch, 'icon': 'download'},
    'Actions::Pull': {'title': 'Pull...', 'action': remote.pull, 'icon': 'pull'},
    'Actions::Push': {'title': 'Push...', 'action': remote.push, 'icon': 'push'},
    'Actions::Stash': {'title': 'Stash...', 'action': stash.view, 'icon': 'commit'},
    'Actions::CreateTag': {
        'title': 'Create Tag...',
        'action': createtag.create_tag,
        'icon': 'tag',
    },
    'Actions::CherryPick': {
        'title': 'Cherry-Pick...',
        'action': guicmds.cherry_pick,
        'icon': 'cherry_pick',
    },
    'Actions::Merge': {
        'title': 'Merge...',
        'action': merge.local_merge,
        'icon': 'merge',
    },
    'Actions::AbortMerge': {
        'title': 'Abort Merge...',
        'action': cmds.run(cmds.AbortMerge),
        'icon': 'undo',
    },
    'Actions::UpdateSubmodules': {
        'title': 'Update All Submodules...',
        'action': cmds.run(cmds.SubmodulesUpdate),
        'icon': 'sync',
    },
    'Actions::ResetSoft': {
        'title': 'Reset Branch (Soft)',
        'action': guicmds.reset_soft,
        'icon': 'style_dialog_reset',
        'tooltip': cmds.ResetSoft.tooltip('<commit>'),
    },
    'Actions::ResetMixed': {
        'title': 'Reset Branch and Stage (Mixed)',
        'action': guicmds.reset_mixed,
        'icon': 'style_dialog_reset',
        'tooltip': cmds.ResetMixed.tooltip('<commit>'),
    },
    'Actions::RestoreWorktree': {
        'title': 'Restore Worktree',
        'action': guicmds.restore_worktree,
        'icon': 'edit',
        'tooltip': cmds.RestoreWorktree.tooltip('<commit>'),
    },
    'Actions::ResetKeep': {
        'title': 'Restore Worktree and Reset All (Keep Unstaged Changes)',
        'action': guicmds.reset_keep,
        'icon': 'style_dialog_reset',
        'tooltip': cmds.ResetKeep.tooltip('<commit>'),
    },
    'Actions::ResetHard': {
        'title': 'Restore Worktre and Reset All (Hard)',
        'action': guicmds.reset_hard,
        'icon': 'style_dialog_reset',
        'tooltip': cmds.ResetHard.tooltip('<commit>'),
    },
    'Actions::Grep': {
        'title': 'Grep',
        'action': grep.grep,
        'icon': 'search',
    },
    'Actions::Search': {
        'title': 'Search...',
        'action': search.search,
        'icon': 'search',
    },
    'Commit::Stage': {
        'title': 'Stage',
        'action': cmds.run(cmds.StageOrUnstage),
        'icon': 'add',
    },
    'Commit::AmendLast': {
        'title': 'Amend Last Commit',
        'action': cmds.run(cmds.AmendMode),
        'icon': 'edit',
    },
    'Commit::UndoLastCommit': {
        'title': 'Undo Last Commit',
        'action': cmds.run(cmds.UndoLastCommit),
        'icon': 'style_dialog_discard',
    },
    'Commit::StageAll': {
        'title': 'Stage All Untracked',
        'action': cmds.run(cmds.StageUntracked),
        'icon': 'add',
    },
    'Commit::UnstageAll': {
        'title': 'Unstage All',
        'action': cmds.run(cmds.UnstageAll),
        'icon': 'remove',
    },
    'Commit::Unstage': {
        'title': 'Unstage',
        'action': cmds.run(cmds.UnstageSelected),
        'icon': 'remove',
    },
    'Commit::LoadCommitMessage': {
        'title': 'Load Commit Message...',
        'action': guicmds.load_commitmsg,
        'icon': 'file_text',
    },
    'Commit::GetCommitMessageTemplate': {
        'title': 'Get Commit Message Template',
        'action': cmds.run(cmds.LoadCommitMessageFromTemplate),
        'icon': 'style_dialog_apply',
    },
    'Diff::Difftool': {
        'title': 'Launch Diff tool',
        'action': cmds.run(cmds.LaunchDifftool),
        'icon': 'diff',
    },
    'Diff::Expression': {
        'title': 'Expression...',
        'action': guicmds.diff_expression,
        'icon': 'compare',
    },
    'Diff::Branches': {
        'title': 'Branches...',
        'action': compare.compare_branches,
        'icon': 'compare',
    },
    'Diff::Diffstat': {
        'title': 'Diffstat',
        'action': cmds.run(cmds.Diffstat),
        'icon': 'diff',
    },
    'Branch::Review': {
        'title': 'Review...',
        'action': guicmds.review_branch,
        'icon': 'compare',
    },
    'Branch::Create': {
        'title': 'Create...',
        'action': createbranch.create_new_branch,
        'icon': 'branch',
    },
    'Branch::Checkout': {
        'title': 'Checkout...',
        'action': guicmds.checkout_branch,
        'icon': 'branch',
    },
    'Branch::Delete': {
        'title': 'Delete...',
        'action': guicmds.delete_branch,
        'icon': 'discard',
    },
    'Branch::DeleteRemote': {
        'title': 'Delete Remote Branch...',
        'action': guicmds.delete_remote_branch,
        'icon': 'discard',
    },
    'Branch::Rename': {
        'title': 'Rename Branch...',
        'action': guicmds.rename_branch,
        'icon': 'edit',
    },
    'Branch::BrowseCurrent': {
        'title': 'Browse Current Branch...',
        'action': guicmds.browse_current,
        'icon': 'directory',
    },
    'Branch::BrowseOther': {
        'title': 'Browse Other Branch...',
        'action': guicmds.browse_other,
        'icon': 'directory',
    },
    'Branch::VisualizeCurrent': {
        'title': 'Visualize Current Branch...',
        'action': cmds.run(cmds.VisualizeCurrent),
        'icon': 'visualize',
    },
    'Branch::VisualizeAll': {
        'title': 'Visualize All Branches...',
        'action': cmds.run(cmds.VisualizeAll),
        'icon': 'visualize',
    },
    'View::FileBrowser': {
        'title': 'File Browser...',
        'action': browse.worktree_browser,
        'icon': 'cola',
    },
    'View::DAG': {'title': 'DAG...', 'action': dag.git_dag, 'icon': 'cola'},
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
