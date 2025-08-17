"""Main UI for authoring commits and other Git Cola interactions"""
import os
from functools import partial

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..compat import WIN32
from ..i18n import N_
from ..interaction import Interaction
from ..models import prefs
from ..qtutils import get
from .. import cmds
from .. import core
from .. import guicmds
from .. import git
from .. import gitcmds
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import resources
from .. import utils
from .. import version
from . import about
from . import action
from . import archive
from . import bookmarks
from . import branch
from . import submodules
from . import browse
from . import cfgactions
from . import clone
from . import commitmsg
from . import common
from . import compare
from . import createbranch
from . import createtag
from . import dag
from . import diff
from . import finder
from . import editremotes
from . import grep
from . import log
from . import merge
from . import prefs as prefs_widget
from . import recent
from . import remote
from . import search
from . import standard
from . import status
from . import stash
from . import toolbar


class MainView(standard.MainWindow):
    config_actions_changed = Signal(object)

    def __init__(self, context, parent=None):
        standard.MainWindow.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.context = context
        self.git = context.git
        self.dag = None
        self.model = context.model
        self.prefs_model = prefs_model = prefs.PreferencesModel(context)
        self.toolbar_state = toolbar.ToolBarState(context, self)

        # The widget version is used by import/export_state().
        # Change this whenever dockwidgets are removed.
        self.widget_version = 2

        create_dock = qtutils.create_dock
        cfg = context.cfg
        self.browser_dockable = cfg.get('cola.browserdockable')
        if self.browser_dockable:
            browser = browse.worktree_browser(
                context, parent=self, show=False, update=False
            )
            self.browserdock = create_dock(
                'Browser', N_('Browser'), self, widget=browser
            )

        # "Actions" widget
        self.actionswidget = action.ActionButtons(context, self)
        self.actionsdock = create_dock(
            'Actions', N_('Actions'), self, widget=self.actionswidget
        )
        qtutils.hide_dock(self.actionsdock)

        # "Repository Status" widget
        self.statusdock = create_dock(
            'Status',
            N_('Status'),
            self,
            func=lambda dock: status.StatusWidget(context, dock.titleBarWidget(), dock),
        )
        self.statuswidget = self.statusdock.widget()

        # "Switch Repository" widgets
        self.bookmarksdock = create_dock(
            'Favorites',
            N_('Favorites'),
            self,
            func=lambda dock: bookmarks.bookmark(context, dock),
        )
        self.bookmarkswidget = self.bookmarksdock.widget()
        qtutils.hide_dock(self.bookmarksdock)

        self.recentdock = create_dock(
            'Recent',
            N_('Recent'),
            self,
            func=lambda dock: bookmarks.recent(context, dock),
        )
        self.recentwidget = self.recentdock.widget()
        qtutils.hide_dock(self.recentdock)
        self.bookmarkswidget.connect_to(self.recentwidget)

        # "Branch" widgets
        self.branchdock = create_dock(
            'Branches',
            N_('Branches'),
            self,
            func=partial(branch.BranchesWidget, context),
        )
        self.branchwidget = self.branchdock.widget()
        titlebar = self.branchdock.titleBarWidget()
        titlebar.add_corner_widget(self.branchwidget.filter_button)
        titlebar.add_corner_widget(self.branchwidget.sort_order_button)

        # "Submodule" widgets
        self.submodulesdock = create_dock(
            'Submodules',
            N_('Submodules'),
            self,
            func=partial(submodules.SubmodulesWidget, context),
        )
        self.submoduleswidget = self.submodulesdock.widget()

        # "Commit Message Editor" widget
        editor = commitmsg.CommitMessageEditor(context, self)
        self.commiteditor = editor
        self.commitdock = create_dock(
            'Commit', N_('Commit'), self, widget=editor, hide_title=True, stretch=False
        )
        titlebar = self.commitdock.titleBarWidget()
        titlebar.add_title_widget(self.commiteditor.topwidget)
        self.commitdock.setTabOrder(
            self.commiteditor.summary, self.commiteditor.description
        )

        # "Console" widget
        self.logwidget = log.LogWidget(context)
        self.logdock = create_dock(
            'Console', N_('Console'), self, widget=self.logwidget, hide_title=True
        )
        qtutils.hide_dock(self.logdock)

        # "Diff Viewer" widget
        self.diffdock = create_dock(
            'Diff',
            N_('Diff'),
            self,
            func=lambda dock: diff.Viewer(context, parent=dock),
            hide_title=True,
        )
        self.diffviewer = self.diffdock.widget()
        self.diffviewer.set_diff_type(self.model.diff_type)
        self.diffviewer.enable_filename_tracking()
        self.diffeditor = self.diffviewer.text
        titlebar = self.diffdock.titleBarWidget()
        titlebar.add_title_widget(self.diffviewer.options)
        titlebar.add_corner_widget(self.diffviewer.diffstat)

        # All Actions
        # Make Cmd-M minimize the window on macOS.
        if utils.is_darwin():
            self.minimize_action = qtutils.add_action(
                self, N_('Minimize Window'), self.showMinimized, hotkeys.MACOS_MINIMIZE
            )
        self.unstage_all_action = qtutils.add_action(
            self, N_('Unstage All'), cmds.run(cmds.UnstageAll, context)
        )
        self.unstage_all_action.setIcon(icons.remove())

        self.undo_commit_action = qtutils.add_action(
            self, N_('Undo Last Commit'), cmds.run(cmds.UndoLastCommit, context)
        )
        self.undo_commit_action.setIcon(icons.style_dialog_discard())

        self.unstage_selected_action = qtutils.add_action(
            self, N_('Unstage'), cmds.run(cmds.UnstageSelected, context)
        )
        self.unstage_selected_action.setIcon(icons.remove())

        self.show_diffstat_action = qtutils.add_action(
            self, N_('Diffstat'), self.statuswidget.select_header, hotkeys.DIFFSTAT
        )
        self.show_diffstat_action.setIcon(icons.diff())

        self.stage_modified_action = qtutils.add_action(
            self,
            cmds.StageModified.name(),
            cmds.run(cmds.StageModified, context),
            hotkeys.STAGE_MODIFIED,
        )
        self.stage_modified_action.setIcon(icons.add())

        self.stage_untracked_action = qtutils.add_action(
            self,
            cmds.StageUntracked.name(),
            cmds.run(cmds.StageUntracked, context),
            hotkeys.STAGE_UNTRACKED,
        )
        self.stage_untracked_action.setIcon(icons.add())

        self.apply_patches_action = qtutils.add_action(
            self, N_('Apply Patches...'), partial(diff.apply_patches, context)
        )
        self.apply_patches_action.setIcon(icons.diff())

        self.apply_patches_abort_action = qtutils.add_action_with_tooltip(
            self,
            N_('Abort Applying Patches...'),
            N_('Abort the current "git am" patch session'),
            cmds.run(cmds.AbortApplyPatch, context),
        )
        self.apply_patches_abort_action.setIcon(icons.style_dialog_discard())

        self.apply_patches_continue_action = qtutils.add_action_with_tooltip(
            self,
            N_('Continue Applying Patches'),
            N_('Commit the current state and continue applying patches'),
            cmds.run(cmds.ApplyPatchesContinue, context),
        )
        self.apply_patches_continue_action.setIcon(icons.commit())

        self.apply_patches_skip_action = qtutils.add_action_with_tooltip(
            self,
            N_('Skip Current Patch'),
            N_('Skip applying the current patch and continue applying patches'),
            cmds.run(cmds.ApplyPatchesContinue, context),
        )
        self.apply_patches_skip_action.setIcon(icons.discard())

        self.export_patches_action = qtutils.add_action(
            self,
            N_('Export Patches...'),
            partial(guicmds.export_patches, context),
            hotkeys.EXPORT,
        )
        self.export_patches_action.setIcon(icons.save())

        self.new_repository_action = qtutils.add_action(
            self, N_('New Repository...'), partial(guicmds.open_new_repo, context)
        )
        self.new_repository_action.setIcon(icons.new())

        self.new_bare_repository_action = qtutils.add_action(
            self, N_('New Bare Repository...'), partial(guicmds.new_bare_repo, context)
        )
        self.new_bare_repository_action.setIcon(icons.new())

        prefs_func = partial(
            prefs_widget.preferences, context, parent=self, model=prefs_model
        )
        self.preferences_action = qtutils.add_action(
            self, N_('Preferences'), prefs_func, QtGui.QKeySequence.Preferences
        )
        self.preferences_action.setIcon(icons.configure())

        self.edit_remotes_action = qtutils.add_action(
            self, N_('Edit Remotes...'), partial(editremotes.editor, context)
        )
        self.edit_remotes_action.setIcon(icons.edit())

        self.rescan_action = qtutils.add_action(
            self,
            cmds.Refresh.name(),
            cmds.run(cmds.Refresh, context),
            *hotkeys.REFRESH_HOTKEYS,
        )
        self.rescan_action.setIcon(icons.sync())

        self.find_files_action = qtutils.add_action(
            self,
            N_('Find Files'),
            partial(finder.finder, context),
            hotkeys.FINDER,
        )
        self.find_files_action.setIcon(icons.search())

        self.browse_recently_modified_action = qtutils.add_action(
            self,
            N_('Recently Modified Files...'),
            partial(recent.browse_recent_files, context),
            hotkeys.EDIT_SECONDARY,
        )
        self.browse_recently_modified_action.setIcon(icons.directory())

        self.cherry_pick_action = qtutils.add_action(
            self,
            N_('Cherry-Pick...'),
            partial(guicmds.cherry_pick, context),
            hotkeys.CHERRY_PICK,
        )
        self.cherry_pick_action.setIcon(icons.cherry_pick())
        self.cherry_pick_abort_action = qtutils.add_action(
            self, N_('Abort Cherry-Pick...'), cmds.run(cmds.AbortCherryPick, context)
        )
        self.cherry_pick_abort_action.setIcon(icons.style_dialog_discard())

        self.load_commitmsg_action = qtutils.add_action(
            self, N_('Load Commit Message...'), partial(guicmds.load_commitmsg, context)
        )
        self.load_commitmsg_action.setIcon(icons.file_text())

        self.prepare_commitmsg_hook_action = qtutils.add_action(
            self,
            N_('Prepare Commit Message'),
            cmds.run(cmds.PrepareCommitMessageHook, context),
            hotkeys.PREPARE_COMMIT_MESSAGE,
        )

        self.save_tarball_action = qtutils.add_action(
            self, N_('Save As Tarball/Zip...'), partial(archive.save_archive, context)
        )
        self.save_tarball_action.setIcon(icons.file_zip())

        self.quit_action = qtutils.add_action(
            self, N_('Quit'), self.close, hotkeys.QUIT
        )

        self.grep_action = qtutils.add_action(
            self, N_('Grep'), partial(grep.grep, context), hotkeys.GREP
        )
        self.grep_action.setIcon(icons.search())

        self.merge_local_action = qtutils.add_action(
            self, N_('Merge...'), partial(merge.local_merge, context), hotkeys.MERGE
        )
        self.merge_local_action.setIcon(icons.merge())

        self.merge_abort_action = qtutils.add_action(
            self, N_('Abort Merge...'), cmds.run(cmds.AbortMerge, context)
        )
        self.merge_abort_action.setIcon(icons.style_dialog_discard())

        self.update_submodules_action = qtutils.add_action(
            self,
            N_('Update All Submodules...'),
            cmds.run(cmds.SubmodulesUpdate, context),
        )
        self.update_submodules_action.setIcon(icons.sync())

        self.add_submodule_action = qtutils.add_action(
            self,
            N_('Add Submodule...'),
            partial(submodules.add_submodule, context, parent=self),
        )
        self.add_submodule_action.setIcon(icons.add())

        self.fetch_action = qtutils.add_action_with_tooltip(
            self,
            N_('Fetch...'),
            N_('Fetch from one or more remotes using "git fetch"'),
            partial(remote.fetch, context),
            hotkeys.FETCH,
        )
        self.fetch_action.setIcon(icons.download())

        self.push_action = qtutils.add_action_with_tooltip(
            self,
            N_('Push...'),
            N_('Push to one or more remotes using "git push"'),
            partial(remote.push, context),
            hotkeys.PUSH,
        )
        self.push_action.setIcon(icons.push())

        self.pull_action = qtutils.add_action_with_tooltip(
            self,
            N_('Pull...'),
            N_('Integrate changes using "git pull"'),
            partial(remote.pull, context),
            hotkeys.PULL,
        )
        self.pull_action.setIcon(icons.pull())

        self.open_repo_action = qtutils.add_action(
            self, N_('Open...'), partial(guicmds.open_repo, context), hotkeys.OPEN
        )
        self.open_repo_action.setIcon(icons.folder())

        self.open_repo_new_action = qtutils.add_action(
            self,
            N_('Open in New Window...'),
            partial(guicmds.open_repo_in_new_window, context),
        )
        self.open_repo_new_action.setIcon(icons.folder())

        self.stash_action = qtutils.add_action_with_tooltip(
            self,
            N_('Stash...'),
            N_('Temporarily stash away uncommitted changes using "git stash"'),
            partial(stash.view, context),
            hotkeys.STASH,
        )
        self.stash_action.setIcon(icons.commit())

        self.reset_soft_action = qtutils.add_action_with_tooltip(
            self,
            N_('Reset Branch (Soft)'),
            cmds.ResetSoft.tooltip('<commit>'),
            partial(guicmds.reset_soft, context),
        )
        self.reset_soft_action.setIcon(icons.style_dialog_reset())

        self.reset_mixed_action = qtutils.add_action_with_tooltip(
            self,
            N_('Reset Branch and Stage (Mixed)'),
            cmds.ResetMixed.tooltip('<commit>'),
            partial(guicmds.reset_mixed, context),
        )
        self.reset_mixed_action.setIcon(icons.style_dialog_reset())

        self.reset_keep_action = qtutils.add_action_with_tooltip(
            self,
            N_('Restore Worktree and Reset All (Keep Unstaged Changes)'),
            cmds.ResetKeep.tooltip('<commit>'),
            partial(guicmds.reset_keep, context),
        )
        self.reset_keep_action.setIcon(icons.style_dialog_reset())

        self.reset_merge_action = qtutils.add_action_with_tooltip(
            self,
            N_('Restore Worktree and Reset All (Merge)'),
            cmds.ResetMerge.tooltip('<commit>'),
            partial(guicmds.reset_merge, context),
        )
        self.reset_merge_action.setIcon(icons.style_dialog_reset())

        self.reset_hard_action = qtutils.add_action_with_tooltip(
            self,
            N_('Restore Worktree and Reset All (Hard)'),
            cmds.ResetHard.tooltip('<commit>'),
            partial(guicmds.reset_hard, context),
        )
        self.reset_hard_action.setIcon(icons.style_dialog_reset())

        self.restore_worktree_action = qtutils.add_action_with_tooltip(
            self,
            N_('Restore Worktree'),
            cmds.RestoreWorktree.tooltip('<commit>'),
            partial(guicmds.restore_worktree, context),
        )
        self.restore_worktree_action.setIcon(icons.edit())

        self.clone_repo_action = qtutils.add_action(
            self, N_('Clone...'), partial(clone.clone, context)
        )
        self.clone_repo_action.setIcon(icons.repo())

        self.help_docs_action = qtutils.add_action(
            self,
            N_('Documentation'),
            resources.show_html_docs,
            QtGui.QKeySequence.HelpContents,
        )

        self.help_shortcuts_action = qtutils.add_action(
            self, N_('Keyboard Shortcuts'), about.show_shortcuts, hotkeys.QUESTION
        )

        self.visualize_current_action = qtutils.add_action(
            self,
            N_('Visualize Current Branch...'),
            cmds.run(cmds.VisualizeCurrent, context),
        )
        self.visualize_current_action.setIcon(icons.visualize())

        self.visualize_all_action = qtutils.add_action(
            self, N_('Visualize All Branches...'), cmds.run(cmds.VisualizeAll, context)
        )
        self.visualize_all_action.setIcon(icons.visualize())

        self.search_commits_action = qtutils.add_action(
            self, N_('Search...'), partial(search.search, context)
        )
        self.search_commits_action.setIcon(icons.search())

        self.browse_branch_action = qtutils.add_action(
            self,
            N_('Browse Current Branch...'),
            partial(guicmds.browse_current, context),
        )
        self.browse_branch_action.setIcon(icons.directory())

        self.browse_other_branch_action = qtutils.add_action(
            self, N_('Browse Other Branch...'), partial(guicmds.browse_other, context)
        )
        self.browse_other_branch_action.setIcon(icons.directory())

        self.load_commitmsg_template_action = qtutils.add_action(
            self,
            N_('Get Commit Message Template'),
            cmds.run(cmds.LoadCommitMessageFromTemplate, context),
        )
        self.load_commitmsg_template_action.setIcon(icons.style_dialog_apply())

        self.help_about_action = qtutils.add_action(
            self, N_('About'), partial(about.about_dialog, context)
        )

        self.diff_against_commit_action = qtutils.add_action(
            self,
            N_('Against Commit... (Diff Mode)'),
            partial(guicmds.diff_against_commit, context),
        )
        self.diff_against_commit_action.setIcon(icons.compare())

        self.exit_diff_mode_action = qtutils.add_action(
            self, N_('Exit Diff Mode'), cmds.run(cmds.ResetMode, context)
        )
        self.exit_diff_mode_action.setIcon(icons.compare())

        self.diff_expression_action = qtutils.add_action(
            self, N_('Expression...'), partial(guicmds.diff_expression, context)
        )
        self.diff_expression_action.setIcon(icons.compare())

        self.branch_compare_action = qtutils.add_action(
            self, N_('Branches...'), partial(compare.compare_branches, context)
        )
        self.branch_compare_action.setIcon(icons.compare())

        self.create_tag_action = qtutils.add_action(
            self,
            N_('Create Tag...'),
            partial(createtag.create_tag, context),
        )
        self.create_tag_action.setIcon(icons.tag())

        self.create_branch_action = qtutils.add_action(
            self,
            N_('Create...'),
            partial(createbranch.create_new_branch, context),
            hotkeys.BRANCH,
        )
        self.create_branch_action.setIcon(icons.branch())

        self.delete_branch_action = qtutils.add_action(
            self, N_('Delete...'), partial(guicmds.delete_branch, context)
        )
        self.delete_branch_action.setIcon(icons.discard())

        self.delete_remote_branch_action = qtutils.add_action(
            self,
            N_('Delete Remote Branch...'),
            partial(guicmds.delete_remote_branch, context),
        )
        self.delete_remote_branch_action.setIcon(icons.discard())

        self.rename_branch_action = qtutils.add_action(
            self, N_('Rename Branch...'), partial(guicmds.rename_branch, context)
        )
        self.rename_branch_action.setIcon(icons.edit())

        self.checkout_branch_action = qtutils.add_action(
            self,
            N_('Checkout...'),
            partial(guicmds.checkout_branch, context),
            hotkeys.CHECKOUT,
        )
        self.checkout_branch_action.setIcon(icons.branch())

        self.branch_review_action = qtutils.add_action(
            self, N_('Review...'), partial(guicmds.review_branch, context)
        )
        self.branch_review_action.setIcon(icons.compare())

        self.browse_action = qtutils.add_action(
            self, N_('File Browser...'), partial(browse.worktree_browser, context)
        )
        self.browse_action.setIcon(icons.cola())

        self.dag_action = qtutils.add_action(self, N_('DAG...'), self.git_dag)
        self.dag_action.setIcon(icons.cola())

        self.rebase_start_action = qtutils.add_action(
            self,
            N_('Start Interactive Rebase...'),
            cmds.run(cmds.Rebase, context),
            hotkeys.REBASE_START_AND_CONTINUE,
        )
        self.rebase_start_action.setIcon(icons.play())

        self.rebase_edit_todo_action = qtutils.add_action(
            self, N_('Edit...'), cmds.run(cmds.RebaseEditTodo, context)
        )
        self.rebase_edit_todo_action.setIcon(icons.edit())

        self.rebase_continue_action = qtutils.add_action(
            self,
            N_('Continue'),
            cmds.run(cmds.RebaseContinue, context),
            hotkeys.REBASE_START_AND_CONTINUE,
        )
        self.rebase_continue_action.setIcon(icons.play())

        self.rebase_skip_action = qtutils.add_action(
            self, N_('Skip Current Patch'), cmds.run(cmds.RebaseSkip, context)
        )
        self.rebase_skip_action.setIcon(icons.delete())

        self.rebase_abort_action = qtutils.add_action(
            self, N_('Abort'), cmds.run(cmds.RebaseAbort, context)
        )
        self.rebase_abort_action.setIcon(icons.close())

        # For "Start Rebase" only, reverse the first argument to setEnabled()
        # so that we can operate on it as a group.
        # We can do this because can_rebase == not is_rebasing
        self.rebase_start_action_proxy = utils.Proxy(
            self.rebase_start_action,
            setEnabled=lambda x: self.rebase_start_action.setEnabled(not x),
        )

        self.rebase_group = utils.Group(
            self.rebase_start_action_proxy,
            self.rebase_edit_todo_action,
            self.rebase_continue_action,
            self.rebase_skip_action,
            self.rebase_abort_action,
        )

        self.annex_init_action = qtutils.add_action(
            self, N_('Initialize Git Annex'), cmds.run(cmds.AnnexInit, context)
        )

        self.lfs_init_action = qtutils.add_action(
            self, N_('Initialize Git LFS'), cmds.run(cmds.LFSInstall, context)
        )

        self.lock_layout_action = qtutils.add_action_bool(
            self, N_('Lock Layout'), self.set_lock_layout, False
        )

        self.reset_layout_action = qtutils.add_action(
            self, N_('Reset Layout'), self.reset_layout
        )

        self.save_layout_action = qtutils.add_action(
            self, N_('Save Layout'), lambda: guicmds.save_layout(self)
        )
        self.load_layout_action = qtutils.add_action(
            self, N_('Load Layout'), lambda: guicmds.load_layout(self)
        )

        self.quick_repository_search = qtutils.add_action(
            self,
            N_('Quick Open...'),
            lambda: guicmds.open_quick_repo_search(self.context, parent=self),
            hotkeys.OPEN_REPO_SEARCH,
        )
        self.quick_repository_search.setIcon(icons.search())

        self.terminal_action = common.terminal_action(
            context, self, hotkey=hotkeys.TERMINAL
        )

        # Create the application menu
        self.menubar = QtWidgets.QMenuBar(self)
        self.setMenuBar(self.menubar)

        # File Menu
        add_menu = qtutils.add_menu
        self.file_menu = add_menu(N_('&File'), self.menubar)
        self.file_menu.addAction(self.quick_repository_search)
        # File->Open Recent menu
        self.open_recent_menu = self.file_menu.addMenu(N_('Open Recent'))
        self.open_recent_menu.setIcon(icons.folder())
        self.file_menu.addAction(self.open_repo_action)
        self.file_menu.addAction(self.open_repo_new_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.new_repository_action)
        self.file_menu.addAction(self.new_bare_repository_action)
        self.file_menu.addAction(self.clone_repo_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.rescan_action)
        self.file_menu.addAction(self.find_files_action)
        self.file_menu.addAction(self.edit_remotes_action)
        self.file_menu.addAction(self.browse_recently_modified_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.save_tarball_action)

        self.patches_menu = self.file_menu.addMenu(N_('Patches'))
        self.patches_menu.setIcon(icons.diff())
        self.patches_menu.addAction(self.export_patches_action)
        self.patches_menu.addAction(self.apply_patches_action)
        self.patches_menu.addAction(self.apply_patches_continue_action)
        self.patches_menu.addAction(self.apply_patches_skip_action)
        self.patches_menu.addAction(self.apply_patches_abort_action)

        # Git Annex / Git LFS
        annex = core.find_executable('git-annex')
        lfs = core.find_executable('git-lfs')
        if annex or lfs:
            self.file_menu.addSeparator()
        if annex:
            self.file_menu.addAction(self.annex_init_action)
        if lfs:
            self.file_menu.addAction(self.lfs_init_action)

        self.file_menu.addSeparator()
        self.file_menu.addAction(self.preferences_action)
        self.file_menu.addAction(self.quit_action)

        # Edit Menu
        self.edit_proxy = edit_proxy = FocusProxy(
            editor, editor.summary, editor.description
        )

        copy_widgets = (
            self,
            editor.summary,
            editor.description,
            self.diffeditor,
            self.bookmarkswidget.tree,
            self.recentwidget.tree,
        )
        select_widgets = copy_widgets + (self.statuswidget.tree,)
        edit_proxy.override('copy', copy_widgets)
        edit_proxy.override('selectAll', select_widgets)

        edit_menu = self.edit_menu = add_menu(N_('&Edit'), self.menubar)
        undo = qtutils.add_action(edit_menu, N_('Undo'), edit_proxy.undo, hotkeys.UNDO)
        undo.setIcon(icons.undo())
        redo = qtutils.add_action(edit_menu, N_('Redo'), edit_proxy.redo, hotkeys.REDO)
        redo.setIcon(icons.redo())
        edit_menu.addSeparator()
        cut = qtutils.add_action(edit_menu, N_('Cut'), edit_proxy.cut, hotkeys.CUT)
        cut.setIcon(icons.cut())
        copy = qtutils.add_action(edit_menu, N_('Copy'), edit_proxy.copy, hotkeys.COPY)
        copy.setIcon(icons.copy())
        copy_commit_id = qtutils.add_action(
            edit_menu,
            N_('Copy Commit'),
            lambda: guicmds.copy_commit_id_to_clipboard(context),
            hotkeys.COPY_COMMIT_ID,
        )
        copy_commit_id.setIcon(icons.copy())
        self.addAction(copy_commit_id)
        paste = qtutils.add_action(
            edit_menu, N_('Paste'), edit_proxy.paste, hotkeys.PASTE
        )
        paste.setIcon(icons.paste())
        delete = qtutils.add_action(
            edit_menu, N_('Delete'), edit_proxy.delete, hotkeys.DELETE
        )
        delete.setIcon(icons.delete())
        edit_menu.addSeparator()
        select_all = qtutils.add_action(
            edit_menu, N_('Select All'), edit_proxy.selectAll, hotkeys.SELECT_ALL
        )
        select_all.setIcon(icons.select_all())
        edit_menu.addSeparator()
        qtutils.add_menu_actions(edit_menu, self.commiteditor.menu_actions)

        # Actions menu
        self.actions_menu = add_menu(N_('Actions'), self.menubar)
        if self.terminal_action is not None:
            self.actions_menu.addAction(self.terminal_action)
        self.actions_menu.addAction(self.fetch_action)
        self.actions_menu.addAction(self.push_action)
        self.actions_menu.addAction(self.pull_action)
        self.actions_menu.addAction(self.stash_action)
        self.actions_menu.addSeparator()
        self.actions_menu.addAction(self.create_tag_action)
        self.actions_menu.addAction(self.cherry_pick_action)
        self.actions_menu.addAction(self.cherry_pick_abort_action)
        self.actions_menu.addAction(self.merge_local_action)
        self.actions_menu.addAction(self.merge_abort_action)
        self.actions_menu.addSeparator()
        self.actions_menu.addAction(self.update_submodules_action)
        self.actions_menu.addAction(self.add_submodule_action)
        self.actions_menu.addSeparator()
        self.actions_menu.addAction(self.grep_action)
        self.actions_menu.addAction(self.search_commits_action)

        # Commit Menu
        self.commit_menu = add_menu(N_('Commit@@verb'), self.menubar)
        self.commit_menu.setTitle(N_('Commit@@verb'))
        self.commit_menu.addAction(self.commiteditor.commit_action)
        self.commit_menu.addAction(self.commiteditor.amend_action)
        self.commit_menu.addAction(self.undo_commit_action)
        self.commit_menu.addSeparator()
        self.commit_menu.addAction(self.statuswidget.tree.process_selection_action)
        self.commit_menu.addAction(self.statuswidget.tree.stage_or_unstage_all_action)
        self.commit_menu.addAction(self.stage_modified_action)
        self.commit_menu.addAction(self.stage_untracked_action)
        self.commit_menu.addSeparator()
        self.commit_menu.addAction(self.unstage_all_action)
        self.commit_menu.addAction(self.unstage_selected_action)
        self.commit_menu.addSeparator()
        self.commit_menu.addAction(self.load_commitmsg_action)
        self.commit_menu.addAction(self.load_commitmsg_template_action)
        self.commit_menu.addAction(self.prepare_commitmsg_hook_action)

        # Diff Menu
        self.diff_menu = add_menu(N_('Diff'), self.menubar)
        self.diff_menu.addAction(self.diff_expression_action)
        self.diff_menu.addAction(self.branch_compare_action)
        self.diff_menu.addAction(self.show_diffstat_action)
        self.diff_menu.addSeparator()
        self.diff_menu.addAction(self.diff_against_commit_action)
        self.diff_menu.addAction(self.exit_diff_mode_action)

        # Branch Menu
        self.branch_menu = add_menu(N_('Branch'), self.menubar)
        self.branch_menu.addAction(self.branch_review_action)
        self.branch_menu.addSeparator()
        self.branch_menu.addAction(self.create_branch_action)
        self.branch_menu.addAction(self.checkout_branch_action)
        self.branch_menu.addAction(self.delete_branch_action)
        self.branch_menu.addAction(self.delete_remote_branch_action)
        self.branch_menu.addAction(self.rename_branch_action)
        self.branch_menu.addSeparator()
        self.branch_menu.addAction(self.browse_branch_action)
        self.branch_menu.addAction(self.browse_other_branch_action)
        self.branch_menu.addSeparator()
        self.branch_menu.addAction(self.visualize_current_action)
        self.branch_menu.addAction(self.visualize_all_action)

        # Rebase menu
        self.rebase_menu = add_menu(N_('Rebase'), self.menubar)
        self.rebase_menu.addAction(self.rebase_start_action)
        self.rebase_menu.addAction(self.rebase_edit_todo_action)
        self.rebase_menu.addSeparator()
        self.rebase_menu.addAction(self.rebase_continue_action)
        self.rebase_menu.addAction(self.rebase_skip_action)
        self.rebase_menu.addSeparator()
        self.rebase_menu.addAction(self.rebase_abort_action)

        # Reset menu
        self.reset_menu = add_menu(N_('Reset'), self.menubar)
        self.reset_menu.addAction(self.unstage_all_action)
        self.reset_menu.addAction(self.undo_commit_action)
        self.reset_menu.addSeparator()
        self.reset_menu.addAction(self.reset_soft_action)
        self.reset_menu.addAction(self.reset_mixed_action)
        self.reset_menu.addAction(self.restore_worktree_action)
        self.reset_menu.addSeparator()
        self.reset_menu.addAction(self.reset_keep_action)
        self.reset_menu.addAction(self.reset_merge_action)
        self.reset_menu.addAction(self.reset_hard_action)

        # View Menu
        self.view_menu = add_menu(N_('View'), self.menubar)
        self.view_menu.aboutToShow.connect(lambda: self.build_view_menu(self.view_menu))
        self.setup_dockwidget_view_menu()
        if utils.is_darwin():
            # The native macOS menu doesn't show empty entries.
            self.build_view_menu(self.view_menu)

        # Help Menu
        self.help_menu = add_menu(N_('Help'), self.menubar)
        self.help_menu.addAction(self.help_docs_action)
        self.help_menu.addAction(self.help_shortcuts_action)
        self.help_menu.addAction(self.help_about_action)

        # Arrange dock widgets
        bottom = Qt.BottomDockWidgetArea
        top = Qt.TopDockWidgetArea

        self.addDockWidget(top, self.statusdock)
        self.addDockWidget(top, self.commitdock)
        if self.browser_dockable:
            self.addDockWidget(top, self.browserdock)
            self.tabifyDockWidget(self.browserdock, self.commitdock)

        self.addDockWidget(top, self.branchdock)
        self.addDockWidget(top, self.submodulesdock)
        self.addDockWidget(top, self.bookmarksdock)
        self.addDockWidget(top, self.recentdock)

        self.tabifyDockWidget(self.branchdock, self.submodulesdock)
        self.tabifyDockWidget(self.submodulesdock, self.bookmarksdock)
        self.tabifyDockWidget(self.bookmarksdock, self.recentdock)
        self.branchdock.raise_()

        self.addDockWidget(bottom, self.diffdock)
        self.addDockWidget(bottom, self.actionsdock)
        self.addDockWidget(bottom, self.logdock)
        self.tabifyDockWidget(self.actionsdock, self.logdock)

        # Listen for model notifications
        self.model.updated.connect(self.refresh, type=Qt.QueuedConnection)
        self.model.mode_changed.connect(
            lambda mode: self.refresh(), type=Qt.QueuedConnection
        )

        prefs_model.config_updated.connect(self._config_updated)
        self.commit_menu.aboutToShow.connect(self.update_menu_actions)
        self.open_recent_menu.aboutToShow.connect(self.build_recent_menu)

        self.diffeditor.options_changed.connect(self.statuswidget.refresh)
        self.diffeditor.up.connect(self.statuswidget.move_up)
        self.diffeditor.down.connect(self.statuswidget.move_down)

        self.commiteditor.up.connect(self.statuswidget.move_up)
        self.commiteditor.down.connect(self.statuswidget.move_down)

        self.config_actions_changed.connect(
            lambda names_and_shortcuts: _install_config_actions(
                context,
                self.actions_menu,
                names_and_shortcuts,
            ),
            type=Qt.QueuedConnection,
        )
        self.init_state(context.settings, self.set_initial_size)

        # Set the UI font size.
        font = self.font()
        font_size = self.context.cfg.get(prefs.FONTSIZE, font.pointSize())
        if font.pointSize() != font_size:
            font.setPointSize(font_size)
            self.setFont(font)

        # Route command output here
        Interaction.log_status = self.logwidget.log_status
        Interaction.log = self.logwidget.log
        # Focus the status widget; this must be deferred
        QtCore.QTimer.singleShot(0, self.initialize)

    def initialize(self):
        context = self.context
        git_version = version.git_version_str(context)
        if git_version:
            ok = True
            Interaction.log(
                git_version + '\n' + N_('git cola version %s') % version.version()
            )
        else:
            ok = False
            error_msg = N_('error: unable to execute git')
            Interaction.log(error_msg)

        if ok:
            self.statuswidget.setFocus()
        else:
            title = N_('error: unable to execute git')
            msg = title
            details = ''
            if WIN32:
                details = git.win32_git_error_hint()
            Interaction.critical(title, message=msg, details=details)
            self.context.app.exit(2)

    def set_initial_size(self):
        # Default size; this is thrown out when save/restore is used
        width, height = qtutils.desktop_size()
        self.resize((width * 3) // 4, height)
        self.statuswidget.set_initial_size()
        self.commiteditor.set_initial_size()

    def set_filter(self, txt):
        self.statuswidget.set_filter(txt)

    # Qt overrides
    def closeEvent(self, event):
        """Save state in the settings"""
        commit_msg = self.commiteditor.commit_message(raw=True)
        self.model.save_commitmsg(msg=commit_msg)
        for browser in list(self.context.browser_windows):
            browser.close()
        standard.MainWindow.closeEvent(self, event)

    def create_view_menu(self):
        menu = qtutils.create_menu(N_('View'), self)
        self.build_view_menu(menu)
        return menu

    def build_view_menu(self, menu):
        menu.clear()
        if utils.is_darwin():
            menu.addAction(self.minimize_action)
        menu.addAction(self.browse_action)
        menu.addAction(self.dag_action)
        menu.addSeparator()

        popup_menu = self.createPopupMenu()
        for menu_action in popup_menu.actions():
            menu_action.setParent(menu)
            menu.addAction(menu_action)

        context = self.context
        menu_action = menu.addAction(
            N_('New Toolbar'), partial(toolbar.add_toolbar, context, self)
        )
        menu_action.setIcon(icons.add())
        menu.addSeparator()

        dockwidgets = [
            self.logdock,
            self.commitdock,
            self.statusdock,
            self.diffdock,
            self.actionsdock,
            self.bookmarksdock,
            self.recentdock,
            self.branchdock,
            self.submodulesdock,
        ]
        if self.browser_dockable:
            dockwidgets.append(self.browserdock)

        for dockwidget in dockwidgets:
            # Associate the action with the shortcut
            toggleview = dockwidget.toggleViewAction()
            menu.addAction(toggleview)

        menu.addSeparator()
        menu.addAction(self.lock_layout_action)

        layout_menu = menu.addMenu(N_('Layouts'))
        layout_menu.addAction(self.save_layout_action)
        layout_menu.addAction(self.load_layout_action)
        layout_menu.addAction(self.reset_layout_action)
        guicmds.build_layout_menu(self, layout_menu)

        return menu

    def contextMenuEvent(self, event):
        menu = self.create_view_menu()
        menu.exec_(event.globalPos())

    def build_recent_menu(self):
        cmd = cmds.OpenRepo
        context = self.context
        settings = context.settings
        settings.load()
        menu = self.open_recent_menu
        menu.clear()
        worktree = context.git.worktree()

        for entry in settings.recent:
            directory = entry['path']
            if directory == worktree:
                # Omit the current worktree from the "Open Recent" menu.
                continue
            name = entry['name']
            text = f'{name} {chr(0x2192)} {directory}'
            menu.addAction(text, cmds.run(cmd, context, directory))

    # Accessors
    mode = property(lambda self: self.model.mode)

    def _config_updated(self, _source, config, value):
        if config == prefs.FONTDIFF:
            # The diff font
            font = QtGui.QFont()
            if not font.fromString(value):
                return
            self.logwidget.setFont(font)
            self.diffeditor.setFont(font)
            self.commiteditor.setFont(font)

        elif config == prefs.FONTSIZE:
            font = self.font()
            font.setPointSize(value)
            self.setFont(font)

        elif config == prefs.TABWIDTH:
            # This can be set locally or globally, so we have to use the
            # effective value otherwise we'll update when we shouldn't.
            # For example, if this value is overridden locally, and the
            # global value is tweaked, we should not update.
            value = prefs.tabwidth(self.context)
            self.diffeditor.set_tabwidth(value)
            self.commiteditor.set_tabwidth(value)

        elif config == prefs.EXPANDTAB:
            self.commiteditor.set_expandtab(value)

        elif config == prefs.LINEBREAK:
            # enables automatic line breaks
            self.commiteditor.set_linebreak(value)

        elif config == prefs.SORT_BOOKMARKS:
            self.bookmarksdock.widget().reload_bookmarks()

        elif config == prefs.TEXTWIDTH:
            # Use the effective value for the same reason as tabwidth.
            value = prefs.textwidth(self.context)
            self.commiteditor.set_textwidth(value)

        elif config == prefs.SHOW_PATH:
            # the path in the window title was toggled
            self.refresh_window_title()

    def start(self, context):
        """Do the expensive "get_config_actions()" call in the background"""
        # Install .git-config-defined actions
        task = qtutils.SimpleTask(self.get_config_actions)
        context.runtask.start(task)

    def get_config_actions(self):
        actions = cfgactions.get_config_actions(self.context)
        self.config_actions_changed.emit(actions)

    def refresh(self):
        """Update the title with the current branch and directory name."""
        curbranch = self.model.currentbranch
        is_merging = self.model.is_merging
        is_rebasing = self.model.is_rebasing
        is_applying_patch = self.model.is_applying_patch
        is_cherry_picking = self.model.is_rebasing

        try:
            curdir = core.getcwd()
        except FileNotFoundError:
            return
        msg = N_('Repository: %s') % curdir
        msg += '\n'
        msg += N_('Branch: %s') % curbranch

        if is_rebasing:
            msg += '\n\n'
            msg += N_(
                'This repository is currently being rebased.\n'
                'Resolve conflicts, commit changes, and run:\n'
                '    Rebase > Continue'
            )
        elif is_applying_patch:
            msg += '\n\n'
            msg += N_(
                'This repository has unresolved conflicts after applying a patch.\n'
                'Resolve conflicts and commit changes.'
            )
        elif is_cherry_picking:
            msg += '\n\n'
            msg += N_(
                'This repository is in the middle of a cherry-pick.\n'
                'Resolve conflicts and commit changes.'
            )
        elif is_merging:
            msg += '\n\n'
            msg += N_(
                'This repository is in the middle of a merge.\n'
                'Resolve conflicts and commit changes.'
            )

        self.refresh_window_title()
        self.commitdock.setToolTip(msg)

        self.actionswidget.set_mode(self.mode)
        self.commiteditor.set_mode(self.mode)
        self.statuswidget.set_mode(self.mode)

        self.update_actions()

    def refresh_window_title(self):
        """Refresh the window title when state changes"""
        alerts = []

        project = self.model.project
        curbranch = self.model.currentbranch
        is_cherry_picking = self.model.is_cherry_picking
        is_merging = self.model.is_merging
        is_rebasing = self.model.is_rebasing
        is_applying_patch = self.model.is_applying_patch
        is_diff_mode = self.model.is_diff_mode()
        is_amend_mode = self.mode == self.model.mode_amend

        prefix = chr(0xAB)
        suffix = chr(0xBB)

        if is_amend_mode:
            alerts.append(N_('Amending'))
        elif is_diff_mode:
            alerts.append(N_('Diff Mode'))
        elif is_cherry_picking:
            alerts.append(N_('Cherry-picking'))
        elif is_merging:
            alerts.append(N_('Merging'))
        elif is_rebasing:
            alerts.append(N_('Rebasing'))
        elif is_applying_patch:
            alerts.append(N_('Applying Patch'))

        if alerts:
            alert_text = (prefix + ' %s ' + suffix + ' ') % ', '.join(alerts)
        else:
            alert_text = ''

        if self.model.cfg.get(prefs.SHOW_PATH, True):
            path_text = self.git.worktree()
        else:
            path_text = ''

        title = f'{project}: {curbranch} {alert_text}{path_text}'
        self.setWindowTitle(title)

    def update_actions(self):
        is_rebasing = self.model.is_rebasing
        self.rebase_group.setEnabled(is_rebasing)

        enabled = not self.model.is_empty_repository()
        self.rename_branch_action.setEnabled(enabled)
        self.delete_branch_action.setEnabled(enabled)

        self.annex_init_action.setEnabled(not self.model.annex)
        self.lfs_init_action.setEnabled(not self.model.lfs)
        self.merge_abort_action.setEnabled(self.model.is_merging)
        self.cherry_pick_abort_action.setEnabled(self.model.is_cherry_picking)
        self.apply_patches_continue_action.setEnabled(self.model.is_applying_patch)
        self.apply_patches_skip_action.setEnabled(self.model.is_applying_patch)
        self.apply_patches_abort_action.setEnabled(self.model.is_applying_patch)

        diff_mode = self.model.mode == self.model.mode_diff
        self.exit_diff_mode_action.setEnabled(diff_mode)

    def update_menu_actions(self):
        # Enable the Prepare Commit Message action if the hook exists
        hook = gitcmds.prepare_commit_message_hook(self.context)
        enabled = os.path.exists(hook)
        self.prepare_commitmsg_hook_action.setEnabled(enabled)

    def export_state(self):
        """Save persistent UI state on shutdown"""
        state = standard.MainWindow.export_state(self)
        show_status_filter = self.statuswidget.filter_widget.isVisible()
        state['show_status_filter'] = show_status_filter
        state['toolbars'] = self.toolbar_state.export_state()
        state['ref_sort'] = self.model.ref_sort
        self.diffviewer.export_state(state)
        self.commiteditor.export_state(state)

        return state

    def apply_state(self, state):
        """Apply persistent UI state on startup"""
        base_ok = standard.MainWindow.apply_state(self, state)
        lock_layout = state.get('lock_layout', False)
        self.lock_layout_action.setChecked(lock_layout)

        show_status_filter = state.get('show_status_filter', False)
        self.statuswidget.filter_widget.setVisible(show_status_filter)

        toolbars = state.get('toolbars', [])
        self.toolbar_state.apply_state(toolbars)

        sort_key = state.get('ref_sort', 0)
        self.model.set_ref_sort(sort_key)

        diff_ok = self.diffviewer.apply_state(state)
        commitmsg_ok = self.commiteditor.apply_state(state)
        return base_ok and diff_ok and commitmsg_ok

    def setup_dockwidget_view_menu(self):
        # Hotkeys for toggling the dock widgets
        if utils.is_darwin():
            optkey = 'Meta'
        else:
            optkey = 'Ctrl'
        dockwidgets = (
            (optkey + '+0', self.logdock),
            (optkey + '+1', self.commitdock),
            (optkey + '+2', self.statusdock),
            (optkey + '+3', self.diffdock),
            (optkey + '+4', self.actionsdock),
            (optkey + '+5', self.bookmarksdock),
            (optkey + '+6', self.recentdock),
            (optkey + '+7', self.branchdock),
            (optkey + '+8', self.submodulesdock),
        )
        for shortcut, dockwidget in dockwidgets:
            # Associate the action with the shortcut
            toggleview = dockwidget.toggleViewAction()
            toggleview.setShortcut('Shift+' + shortcut)

            def showdock(show, dockwidget=dockwidget):
                if show:
                    dockwidget.raise_()
                    dockwidget.widget().setFocus()
                else:
                    self.setFocus()

            self.addAction(toggleview)
            qtutils.connect_action_bool(toggleview, showdock)

            # Create a new shortcut Shift+<shortcut> that gives focus
            toggleview = QtWidgets.QAction(self)
            toggleview.setShortcut(shortcut)

            def focusdock(dockwidget=dockwidget):
                focus_dock(dockwidget)

            self.addAction(toggleview)
            qtutils.connect_action(toggleview, focusdock)

        # These widgets warrant home-row hotkey status
        qtutils.add_action(
            self,
            'Focus Commit Message',
            lambda: focus_dock(self.commitdock),
            hotkeys.FOCUS,
        )

        qtutils.add_action(
            self,
            'Focus Status Window',
            lambda: focus_dock(self.statusdock),
            hotkeys.FOCUS_STATUS,
        )

        qtutils.add_action(
            self,
            'Focus Diff Editor',
            lambda: focus_dock(self.diffdock),
            hotkeys.FOCUS_DIFF,
        )

    def git_dag(self):
        self.dag = dag.git_dag(self.context, existing_view=self.dag)

    # Qt overrides
    def setFont(self, font):
        """Forward setFont() to child widgets"""
        super().setFont(font)
        self.statuswidget.setFont(font)
        self.branchwidget.setFont(font)
        self.submoduleswidget.setFont(font)
        self.recentwidget.setFont(font)
        self.bookmarkswidget.setFont(font)


class FocusProxy:
    """Proxy over child widgets and operate on the focused widget"""

    def __init__(self, *widgets):
        self.widgets = widgets
        self.overrides = {}

    def override(self, name, widgets):
        self.overrides[name] = widgets

    def focus(self, name):
        """Return the currently focused widget"""
        widgets = self.overrides.get(name, self.widgets)
        # The parent must be the parent of all the proxied widgets
        parent = widgets[0]
        # The first widget is used as a fallback
        fallback = widgets[1]
        # We ignore the parent when delegating to child widgets
        widgets = widgets[1:]

        focus = parent.focusWidget()
        if focus not in widgets:
            focus = fallback
        return focus

    def __getattr__(self, name):
        """Return a callback that calls a common child method"""

        def callback():
            focus = self.focus(name)
            func = getattr(focus, name, None)
            if func:
                func()

        return callback

    def delete(self):
        """Specialized delete() to deal with QLineEdit vs. QTextEdit"""
        focus = self.focus('delete')
        if hasattr(focus, 'del_'):
            focus.del_()
        elif hasattr(focus, 'textCursor'):
            focus.textCursor().deleteChar()


def show_dock(dockwidget):
    dockwidget.raise_()
    dockwidget.widget().setFocus()


def focus_dock(dockwidget):
    if get(dockwidget.toggleViewAction()):
        show_dock(dockwidget)
    else:
        dockwidget.toggleViewAction().trigger()


def _install_config_actions(context, menu, names_and_shortcuts):
    """Install .gitconfig-defined actions"""
    if not names_and_shortcuts:
        return
    menu.addSeparator()
    cache = {}
    for name, shortcut in names_and_shortcuts:
        sub_menu, action_name = build_menus(name, menu, cache)
        callback = cmds.run(cmds.RunConfigAction, context, name)
        menu_action = sub_menu.addAction(action_name, callback)
        if shortcut:
            menu_action.setShortcut(shortcut)


def build_menus(name, menu, cache):
    """Create a chain of QMenu entries parented under a root QMenu

    A name of "a/b/c" create a menu chain of menu -> QMenu("a") -> QMenu("b")
    and returns a tuple of (QMenu("b"), "c").

    :param name: The full entry path, ex: "a/b/c" where "a/b" is the menu chain.
    :param menu: The root menu under which to create the menu chain.
    :param cache: A dict cache of previously created menus to avoid duplicates.

    """
    # NOTE: utils.split() and friends are used instead of os.path.split() because
    # slash '/' is the only supported "<menu>/name" separator.  Use of os.path.split()
    # would introduce differences in behavior across platforms.

    # If the menu_path is empty then no parent menus need to be created.
    # The action will be added to the root menu.
    menu_path, text = utils.split(utils.normalize_slash(name))

    if not menu_path:
        return (menu, text)
    # When menu_path contains ex: "a/b" we will create two menus: "a" and "b".
    # The root menu is the parent of "a" and "a" is the parent of "b".
    # The menu returned to the caller is "b".
    #
    # Loop over the individual menu basenames alongside the full subpath returned by
    # pathset(). The subpath is a cache key for finding previously created menus.
    menu_names = utils.splitpath(menu_path)  # ['a', 'b']
    menu_pathset = utils.pathset(menu_path)  # ['a', 'a/b']
    for menu_name, menu_id in zip(menu_names, menu_pathset):
        try:
            menu = cache[menu_id]
        except KeyError:
            menu = cache[menu_id] = menu.addMenu(menu_name)

    return (menu, text)
