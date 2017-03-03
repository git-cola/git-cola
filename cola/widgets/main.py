"""This view provides the main git-cola user interface.
"""
from __future__ import division, absolute_import, unicode_literals

import os

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..compat import unichr
from ..i18n import N_
from ..interaction import Interaction
from ..models import prefs
from ..settings import Settings
from .. import cmds
from .. import core
from .. import guicmds
from .. import git
from .. import gitcfg
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
from . import browse
from . import cfgactions
from . import commitmsg
from . import compare
from . import createbranch
from . import createtag
from . import dag
from . import defs
from . import diff
from . import finder
from . import editremotes
from . import grep
from . import log
from . import merge
from . import patch
from . import prefs as prefs_widget
from . import recent
from . import remote
from . import search
from . import standard
from . import status
from . import stash


class MainView(standard.MainWindow):
    config_actions_changed = Signal(object)
    updated = Signal()

    def __init__(self, model, parent=None, settings=None):
        standard.MainWindow.__init__(self, parent)

        # Default size; this is thrown out when save/restore is used
        self.dag = None
        self.model = model
        self.settings = settings
        self.prefs_model = prefs_model = prefs.PreferencesModel()

        # The widget version is used by import/export_state().
        # Change this whenever dockwidgets are removed.
        self.widget_version = 2

        # Runs asynchronous tasks
        self.runtask = qtutils.RunTask()

        create_dock = qtutils.create_dock
        cfg = gitcfg.current()
        self.browser_dockable = (cfg.get('cola.browserdockable') or
                                 cfg.get('cola.classicdockable'))
        if self.browser_dockable:
            self.browserdockwidget = create_dock(N_('Browser'), self)
            self.browserwidget = (
                    browse.worktree_browser(parent=self, update=False))
            self.browserdockwidget.setWidget(self.browserwidget)

        # "Actions" widget
        self.actionsdockwidget = create_dock(N_('Actions'), self)
        self.actionsdockwidgetcontents = action.ActionButtons(self)
        self.actionsdockwidget.setWidget(self.actionsdockwidgetcontents)
        self.actionsdockwidget.toggleViewAction().setChecked(False)
        self.actionsdockwidget.hide()

        # "Repository Status" widget
        self.statusdockwidget = create_dock(N_('Status'), self)
        titlebar = self.statusdockwidget.titleBarWidget()
        self.statuswidget = status.StatusWidget(titlebar,
                                                parent=self.statusdockwidget)
        self.statusdockwidget.setWidget(self.statuswidget)

        # "Switch Repository" widgets
        self.bookmarksdockwidget = create_dock(N_('Favorites'), self)
        self.bookmarkswidget = bookmarks.BookmarksWidget(
                bookmarks.BOOKMARKS, parent=self.bookmarksdockwidget)
        self.bookmarksdockwidget.setWidget(self.bookmarkswidget)

        self.recentdockwidget = create_dock(N_('Recent'), self)
        self.recentwidget = bookmarks.BookmarksWidget(
                bookmarks.RECENT_REPOS, parent=self.recentdockwidget)
        self.recentdockwidget.setWidget(self.recentwidget)
        self.recentdockwidget.hide()
        self.bookmarkswidget.connect_to(self.recentwidget)

        # "Branch" widgets
        self.branchdockwidget = create_dock(N_('Branches'), self)
        self.branchwidget = branch.BranchesWidget(parent=self.branchdockwidget)
        self.branchdockwidget.setWidget(self.branchwidget)

        # "Commit Message Editor" widget
        self.position_label = QtWidgets.QLabel()
        self.position_label.setAlignment(Qt.AlignCenter)
        font = qtutils.default_monospace_font()
        font.setPointSize(int(font.pointSize() * 0.8))
        self.position_label.setFont(font)

        # make the position label fixed size to avoid layout issues
        fm = self.position_label.fontMetrics()
        width = fm.width('99:999') + defs.spacing
        self.position_label.setMinimumWidth(width)

        self.commitdockwidget = create_dock(N_('Commit'), self)
        titlebar = self.commitdockwidget.titleBarWidget()
        titlebar.add_corner_widget(self.position_label)

        self.commitmsgeditor = commitmsg.CommitMessageEditor(model, self)
        self.commitdockwidget.setWidget(self.commitmsgeditor)

        # "Console" widget
        self.logwidget = log.LogWidget()
        self.logdockwidget = create_dock(N_('Console'), self)
        self.logdockwidget.setWidget(self.logwidget)
        self.logdockwidget.toggleViewAction().setChecked(False)
        self.logdockwidget.hide()

        # "Diff Viewer" widget
        self.diffdockwidget = create_dock(N_('Diff'), self)
        self.diffeditorwidget = diff.DiffEditorWidget(self.diffdockwidget)
        self.diffeditor = self.diffeditorwidget.editor
        self.diffdockwidget.setWidget(self.diffeditorwidget)

        # All Actions
        add_action = qtutils.add_action
        add_action_bool = qtutils.add_action_bool

        self.commit_amend_action = add_action_bool(
            self, N_('Amend Last Commit'), cmds.run(cmds.AmendMode), False)
        self.commit_amend_action.setShortcut(hotkeys.AMEND)
        self.commit_amend_action.setShortcutContext(Qt.WidgetShortcut)

        self.unstage_all_action = add_action(
            self, N_('Unstage All'), cmds.run(cmds.UnstageAll))
        self.unstage_all_action.setIcon(icons.remove())

        self.unstage_selected_action = add_action(
            self, N_('Unstage From Commit'), cmds.run(cmds.UnstageSelected))
        self.unstage_selected_action.setIcon(icons.remove())

        self.show_diffstat_action = add_action(
            self, N_('Diffstat'), cmds.run(cmds.Diffstat), hotkeys.DIFFSTAT)

        self.stage_modified_action = add_action(
            self, N_('Stage Changed Files To Commit'),
            cmds.run(cmds.StageModified), hotkeys.STAGE_MODIFIED)
        self.stage_modified_action.setIcon(icons.add())

        self.stage_untracked_action = add_action(
            self, N_('Stage All Untracked'),
            cmds.run(cmds.StageUntracked), hotkeys.STAGE_UNTRACKED)
        self.stage_untracked_action.setIcon(icons.add())

        self.apply_patches_action = add_action(
            self, N_('Apply Patches...'), patch.apply_patches)

        self.export_patches_action = add_action(
            self, N_('Export Patches...'), guicmds.export_patches,
            hotkeys.EXPORT)

        self.new_repository_action = add_action(
            self, N_('New Repository...'), guicmds.open_new_repo)
        self.new_repository_action.setIcon(icons.new())

        self.preferences_action = add_action(
            self, N_('Preferences'), self.preferences,
            QtGui.QKeySequence.Preferences)

        self.edit_remotes_action = add_action(
            self, N_('Edit Remotes...'),
            lambda: editremotes.remote_editor().exec_())

        self.rescan_action = add_action(
            self, cmds.Refresh.name(), cmds.run(cmds.Refresh),
            *hotkeys.REFRESH_HOTKEYS)
        self.rescan_action.setIcon(icons.sync())

        self.find_files_action = add_action(
            self, N_('Find Files'), finder.finder,
            hotkeys.FINDER, hotkeys.FINDER_SECONDARY)
        self.find_files_action.setIcon(icons.zoom_in())

        self.browse_recently_modified_action = add_action(
            self, N_('Recently Modified Files...'),
            recent.browse_recent_files, hotkeys.EDIT_SECONDARY)

        self.cherry_pick_action = add_action(
            self, N_('Cherry-Pick...'), guicmds.cherry_pick,
            hotkeys.CHERRY_PICK)

        self.load_commitmsg_action = add_action(
            self, N_('Load Commit Message...'), guicmds.load_commitmsg)

        self.prepare_commitmsg_hook_action = add_action(
            self, N_('Prepare Commit Message'),
            cmds.run(cmds.PrepareCommitMessageHook))

        self.save_tarball_action = add_action(
            self, N_('Save As Tarball/Zip...'), self.save_archive)

        self.quit_action = add_action(
            self, N_('Quit'), self.close, hotkeys.QUIT)

        self.grep_action = add_action(
            self, N_('Grep'), grep.grep, hotkeys.GREP)

        self.merge_local_action = add_action(
            self, N_('Merge...'), merge.local_merge, hotkeys.MERGE)

        self.merge_abort_action = add_action(
            self, N_('Abort Merge...'), merge.abort_merge)

        self.fetch_action = add_action(
            self, N_('Fetch...'), remote.fetch, hotkeys.FETCH)
        self.push_action = add_action(
            self, N_('Push...'), remote.push, hotkeys.PUSH)
        self.pull_action = add_action(
            self, N_('Pull...'), remote.pull, hotkeys.PULL)

        self.open_repo_action = add_action(
            self, N_('Open...'), guicmds.open_repo, hotkeys.OPEN)
        self.open_repo_action.setIcon(icons.folder())

        self.open_repo_new_action = add_action(
            self, N_('Open in New Window...'), guicmds.open_repo_in_new_window)
        self.open_repo_new_action.setIcon(icons.folder())

        self.stash_action = add_action(
            self, N_('Stash...'), stash.stash, hotkeys.STASH)

        self.reset_branch_head_action = add_action(
            self, N_('Reset Branch Head'), guicmds.reset_branch_head)

        self.reset_worktree_action = add_action(
            self, N_('Reset Worktree'), guicmds.reset_worktree)

        self.clone_repo_action = add_action(
            self, N_('Clone...'), self.clone_repo)
        self.clone_repo_action.setIcon(icons.repo())

        self.help_docs_action = add_action(
            self, N_('Documentation'), resources.show_html_docs,
            QtGui.QKeySequence.HelpContents)

        self.help_shortcuts_action = add_action(
            self, N_('Keyboard Shortcuts'), about.show_shortcuts,
            hotkeys.QUESTION)

        self.visualize_current_action = add_action(
            self, N_('Visualize Current Branch...'),
            cmds.run(cmds.VisualizeCurrent))
        self.visualize_all_action = add_action(
            self, N_('Visualize All Branches...'),
            cmds.run(cmds.VisualizeAll))
        self.search_commits_action = add_action(
            self, N_('Search...'), search.search)

        self.browse_branch_action = add_action(
            self, N_('Browse Current Branch...'), guicmds.browse_current)
        self.browse_other_branch_action = add_action(
            self, N_('Browse Other Branch...'), guicmds.browse_other)
        self.load_commitmsg_template_action = add_action(
            self, N_('Get Commit Message Template'),
            cmds.run(cmds.LoadCommitMessageFromTemplate))
        self.help_about_action = add_action(
            self, N_('About'), about.about_dialog)

        self.diff_expression_action = add_action(
            self, N_('Expression...'), guicmds.diff_expression)
        self.branch_compare_action = add_action(
            self, N_('Branches...'), compare.compare_branches)

        self.create_tag_action = add_action(
            self, N_('Create Tag...'),
            lambda: createtag.create_tag(settings=settings))

        self.create_branch_action = add_action(
            self, N_('Create...'),
            lambda: createbranch.create_new_branch(settings=settings),
            hotkeys.BRANCH)

        self.delete_branch_action = add_action(
            self, N_('Delete...'), guicmds.delete_branch)

        self.delete_remote_branch_action = add_action(
            self, N_('Delete Remote Branch...'), guicmds.delete_remote_branch)

        self.rename_branch_action = add_action(
            self, N_('Rename Branch...'), guicmds.rename_branch)

        self.checkout_branch_action = add_action(
            self, N_('Checkout...'), guicmds.checkout_branch, hotkeys.CHECKOUT)
        self.branch_review_action = add_action(
            self, N_('Review...'), guicmds.review_branch)

        self.browse_action = add_action(
            self, N_('File Browser...'),
            lambda: browse.worktree_browser(show=True))
        self.browse_action.setIcon(icons.cola())

        self.dag_action = add_action(self, N_('DAG...'), self.git_dag)
        self.dag_action.setIcon(icons.cola())

        self.rebase_start_action = add_action(
            self, N_('Start Interactive Rebase...'), self.rebase_start)

        self.rebase_edit_todo_action = add_action(
            self, N_('Edit...'), self.rebase_edit_todo)

        self.rebase_continue_action = add_action(
            self, N_('Continue'), self.rebase_continue)

        self.rebase_skip_action = add_action(
            self, N_('Skip Current Patch'), self.rebase_skip)

        self.rebase_abort_action = add_action(
            self, N_('Abort'), self.rebase_abort)

        # For "Start Rebase" only, reverse the first argument to setEnabled()
        # so that we can operate on it as a group.
        # We can do this because can_rebase == not is_rebasing
        self.rebase_start_action_proxy = utils.Proxy(
                self.rebase_start_action,
                setEnabled=lambda x: self.rebase_start_action.setEnabled(not x))

        self.rebase_group = utils.Group(self.rebase_start_action_proxy,
                                        self.rebase_edit_todo_action,
                                        self.rebase_continue_action,
                                        self.rebase_skip_action,
                                        self.rebase_abort_action)

        self.lock_layout_action = add_action_bool(
            self, N_('Lock Layout'), self.set_lock_layout, False)

        # Create the application menu
        self.menubar = QtWidgets.QMenuBar(self)

        # File Menu
        create_menu = qtutils.create_menu
        self.file_menu = create_menu(N_('File'), self.menubar)
        self.file_menu.addAction(self.new_repository_action)
        self.open_recent_menu = self.file_menu.addMenu(N_('Open Recent'))
        self.open_recent_menu.setIcon(icons.folder())
        self.file_menu.addAction(self.open_repo_action)
        self.file_menu.addAction(self.open_repo_new_action)
        self.file_menu.addAction(self.clone_repo_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.rescan_action)
        self.file_menu.addAction(self.find_files_action)
        self.file_menu.addAction(self.edit_remotes_action)
        self.file_menu.addAction(self.browse_recently_modified_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.apply_patches_action)
        self.file_menu.addAction(self.export_patches_action)
        self.file_menu.addAction(self.save_tarball_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.preferences_action)
        self.file_menu.addAction(self.quit_action)
        self.menubar.addAction(self.file_menu.menuAction())

        # Actions menu
        self.actions_menu = create_menu(N_('Actions'), self.menubar)
        self.actions_menu.addAction(self.fetch_action)
        self.actions_menu.addAction(self.push_action)
        self.actions_menu.addAction(self.pull_action)
        self.actions_menu.addAction(self.stash_action)
        self.actions_menu.addSeparator()
        self.actions_menu.addAction(self.create_tag_action)
        self.actions_menu.addAction(self.cherry_pick_action)
        self.actions_menu.addAction(self.merge_local_action)
        self.actions_menu.addAction(self.merge_abort_action)
        self.actions_menu.addSeparator()
        self.actions_reset_menu = self.actions_menu.addMenu(N_('Reset'))
        self.actions_reset_menu.addAction(self.reset_branch_head_action)
        self.actions_reset_menu.addAction(self.reset_worktree_action)
        self.actions_menu.addSeparator()
        self.actions_menu.addAction(self.grep_action)
        self.actions_menu.addAction(self.search_commits_action)
        self.menubar.addAction(self.actions_menu.menuAction())

        # Commit Menu
        self.commit_menu = create_menu(N_('Commit@@verb'), self.menubar)
        self.commit_menu.setTitle(N_('Commit@@verb'))
        self.commit_menu.addAction(self.commit_amend_action)
        self.commit_menu.addSeparator()
        self.commit_menu.addAction(self.stage_modified_action)
        self.commit_menu.addAction(self.stage_untracked_action)
        self.commit_menu.addSeparator()
        self.commit_menu.addAction(self.unstage_all_action)
        self.commit_menu.addAction(self.unstage_selected_action)
        self.commit_menu.addSeparator()
        self.commit_menu.addAction(self.load_commitmsg_action)
        self.commit_menu.addAction(self.load_commitmsg_template_action)
        self.commit_menu.addAction(self.prepare_commitmsg_hook_action)
        self.menubar.addAction(self.commit_menu.menuAction())

        # Diff Menu
        self.diff_menu = create_menu(N_('Diff'), self.menubar)
        self.diff_menu.addAction(self.diff_expression_action)
        self.diff_menu.addAction(self.branch_compare_action)
        self.diff_menu.addSeparator()
        self.diff_menu.addAction(self.show_diffstat_action)
        self.menubar.addAction(self.diff_menu.menuAction())

        # Branch Menu
        self.branch_menu = create_menu(N_('Branch'), self.menubar)
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
        self.menubar.addAction(self.branch_menu.menuAction())

        # Rebase menu
        self.rebase_menu = create_menu(N_('Rebase'), self.actions_menu)
        self.rebase_menu.addAction(self.rebase_start_action)
        self.rebase_menu.addAction(self.rebase_edit_todo_action)
        self.rebase_menu.addSeparator()
        self.rebase_menu.addAction(self.rebase_continue_action)
        self.rebase_menu.addAction(self.rebase_skip_action)
        self.rebase_menu.addSeparator()
        self.rebase_menu.addAction(self.rebase_abort_action)
        self.menubar.addAction(self.rebase_menu.menuAction())

        # View Menu
        self.view_menu = create_menu(N_('View'), self.menubar)
        self.view_menu.addAction(self.browse_action)
        self.view_menu.addAction(self.dag_action)
        self.view_menu.addSeparator()
        if self.browser_dockable:
            self.view_menu.addAction(self.browserdockwidget.toggleViewAction())

        self.setup_dockwidget_view_menu()
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.lock_layout_action)
        self.menubar.addAction(self.view_menu.menuAction())

        # Help Menu
        self.help_menu = create_menu(N_('Help'), self.menubar)
        self.help_menu.addAction(self.help_docs_action)
        self.help_menu.addAction(self.help_shortcuts_action)
        self.help_menu.addAction(self.help_about_action)
        self.menubar.addAction(self.help_menu.menuAction())

        # Set main menu
        self.setMenuBar(self.menubar)

        # Arrange dock widgets
        left = Qt.LeftDockWidgetArea
        right = Qt.RightDockWidgetArea
        bottom = Qt.BottomDockWidgetArea

        self.addDockWidget(left, self.commitdockwidget)
        if self.browser_dockable:
            self.addDockWidget(left, self.browserdockwidget)
            self.tabifyDockWidget(self.browserdockwidget, self.commitdockwidget)
        self.addDockWidget(left, self.diffdockwidget)
        self.addDockWidget(right, self.statusdockwidget)
        self.addDockWidget(right, self.bookmarksdockwidget)
        self.addDockWidget(right, self.branchdockwidget)
        self.addDockWidget(right, self.recentdockwidget)
        self.addDockWidget(bottom, self.actionsdockwidget)
        self.addDockWidget(bottom, self.logdockwidget)
        self.tabifyDockWidget(self.actionsdockwidget, self.logdockwidget)

        # Listen for model notifications
        model.add_observer(model.message_updated, self.updated.emit)
        model.add_observer(model.message_mode_changed,
                           lambda mode: self.updated.emit())

        prefs_model.add_observer(prefs_model.message_config_updated,
                                 self._config_updated)

        # Set a default value
        self.show_cursor_position(1, 0)

        self.commit_menu.aboutToShow.connect(self.update_menu_actions)
        self.open_recent_menu.aboutToShow.connect(self.build_recent_menu)
        self.commitmsgeditor.cursor_changed.connect(self.show_cursor_position)

        self.diffeditor.options_changed.connect(self.statuswidget.refresh)
        self.diffeditor.up.connect(self.statuswidget.move_up)
        self.diffeditor.down.connect(self.statuswidget.move_down)

        self.commitmsgeditor.up.connect(self.statuswidget.move_up)
        self.commitmsgeditor.down.connect(self.statuswidget.move_down)

        self.updated.connect(self.refresh, type=Qt.QueuedConnection)

        self.config_actions_changed.connect(self._install_config_actions,
                                            type=Qt.QueuedConnection)
        # Install .git-config-defined actions
        self.init_config_actions()
        self.init_state(settings, self.set_initial_size)

        # Route command output here
        Interaction.log_status = self.logwidget.log_status
        Interaction.log = self.logwidget.log
        Interaction.safe_log = self.logwidget.safe_log
        Interaction.log(version.git_version_str() + '\n' +
                        N_('git cola version %s') % version.version())
        # Focus the status widget; this must be deferred
        QtCore.QTimer.singleShot(0, lambda: self.statuswidget.setFocus())

    def set_initial_size(self):
        self.resize(987, 610)
        self.statuswidget.set_initial_size()
        self.commitmsgeditor.set_initial_size()

    def set_filter(self, txt):
        self.statuswidget.set_filter(txt)

    # Qt overrides
    def closeEvent(self, event):
        """Save state in the settings manager."""
        commit_msg = self.commitmsgeditor.commit_message(raw=True)
        self.model.save_commitmsg(msg=commit_msg)
        standard.MainWindow.closeEvent(self, event)

    def build_recent_menu(self):
        settings = Settings()
        settings.load()
        recent = settings.recent
        cmd = cmds.OpenRepo
        menu = self.open_recent_menu
        menu.clear()
        for r in recent:
            name = r['name']
            directory = r['path']
            text = '%s %s %s' % (name, unichr(0x2192), directory)
            menu.addAction(text, cmds.run(cmd, directory))

    # Accessors
    mode = property(lambda self: self.model.mode)

    def _config_updated(self, source, config, value):
        if config == prefs.FONTDIFF:
            # The diff font
            font = QtGui.QFont()
            if not font.fromString(value):
                return
            self.logwidget.setFont(font)
            self.diffeditor.setFont(font)
            self.commitmsgeditor.setFont(font)

        elif config == prefs.TABWIDTH:
            # variable-tab-width setting
            self.diffeditor.set_tabwidth(value)
            self.commitmsgeditor.set_tabwidth(value)

        elif config == prefs.LINEBREAK:
            # enables automatic line breaks
            self.commitmsgeditor.set_linebreak(value)

        elif config == prefs.SORT_BOOKMARKS:
            self.bookmarkswidget.reload_bookmarks()

        elif config == prefs.TEXTWIDTH:
            # text width used for line wrapping
            self.commitmsgeditor.set_textwidth(value)

    def init_config_actions(self):
        """Do the expensive "get_config_actions()" call in the background"""
        task = qtutils.SimpleTask(self, self.get_config_actions)
        self.runtask.start(task)

    def get_config_actions(self):
        actions = cfgactions.get_config_actions()
        self.config_actions_changed.emit(actions)

    def _install_config_actions(self, names_and_shortcuts):
        """Install .gitconfig-defined actions"""
        if not names_and_shortcuts:
            return
        menu = self.actions_menu
        menu.addSeparator()
        for (name, shortcut) in names_and_shortcuts:
            action = menu.addAction(name, cmds.run(cmds.RunConfigAction, name))
            if shortcut:
                action.setShortcut(shortcut)

    def refresh(self):
        """Update the title with the current branch and directory name."""
        alerts = []
        branch = self.model.currentbranch
        curdir = core.getcwd()
        is_merging = self.model.is_merging
        is_rebasing = self.model.is_rebasing

        msg = N_('Repository: %s') % curdir
        msg += '\n'
        msg += N_('Branch: %s') % branch

        if is_rebasing:
            msg += '\n\n'
            msg += N_('This repository is currently being rebased.\n'
                      'Resolve conflicts, commit changes, and run:\n'
                      '    Rebase > Continue')
            alerts.append(N_('Rebasing'))

        elif is_merging:
            msg += '\n\n'
            msg += N_('This repository is in the middle of a merge.\n'
                      'Resolve conflicts and commit changes.')
            alerts.append(N_('Merging'))

        if self.mode == self.model.mode_amend:
            alerts.append(N_('Amending'))
            self.commit_amend_action.setChecked(True)
        else:
            self.commit_amend_action.setChecked(False)

        l = unichr(0xab)
        r = unichr(0xbb)
        title = ('%s: %s %s%s' % (
                    self.model.project,
                    branch,
                    alerts and ((r+' %s '+l+' ') % ', '.join(alerts)) or '',
                    self.model.git.worktree()))

        self.setWindowTitle(title)
        self.commitdockwidget.setToolTip(msg)
        self.commitmsgeditor.set_mode(self.mode)
        self.update_actions()

    def update_actions(self):
        is_rebasing = self.model.is_rebasing
        self.rebase_group.setEnabled(is_rebasing)

        enabled = not self.model.is_empty_repository()
        self.rename_branch_action.setEnabled(enabled)
        self.delete_branch_action.setEnabled(enabled)

    def update_menu_actions(self):
        # Enable the Prepare Commit Message action if the hook exists
        hook = gitcmds.prepare_commit_message_hook()
        enabled = os.path.exists(hook)
        self.prepare_commitmsg_hook_action.setEnabled(enabled)

    def export_state(self):
        state = standard.MainWindow.export_state(self)
        show_status_filter = self.statuswidget.filter_widget.isVisible()
        state['show_status_filter'] = show_status_filter
        state['show_diff_line_numbers'] = self.diffeditor.show_line_numbers()
        return state

    def apply_state(self, state):
        """Imports data for save/restore"""
        result = standard.MainWindow.apply_state(self, state)
        self.lock_layout_action.setChecked(state.get('lock_layout', False))

        show_status_filter = state.get('show_status_filter', False)
        self.statuswidget.filter_widget.setVisible(show_status_filter)

        diff_numbers = state.get('show_diff_line_numbers', False)
        self.diffeditor.enable_line_numbers(diff_numbers)

        return result

    def setup_dockwidget_view_menu(self):
        # Hotkeys for toggling the dock widgets
        if utils.is_darwin():
            optkey = 'Meta'
        else:
            optkey = 'Ctrl'
        dockwidgets = (
            (optkey + '+0', self.logdockwidget),
            (optkey + '+1', self.commitdockwidget),
            (optkey + '+2', self.statusdockwidget),
            (optkey + '+3', self.diffdockwidget),
            (optkey + '+4', self.actionsdockwidget),
            (optkey + '+5', self.bookmarksdockwidget),
            (optkey + '+6', self.recentdockwidget),
            (optkey + '+7', self.branchdockwidget),
        )
        for shortcut, dockwidget in dockwidgets:
            # Associate the action with the shortcut
            toggleview = dockwidget.toggleViewAction()
            toggleview.setShortcut('Shift+' + shortcut)
            self.view_menu.addAction(toggleview)

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
        qtutils.add_action(self, 'Focus Commit Message',
                           lambda: focus_dock(self.commitdockwidget),
                           hotkeys.FOCUS)

        qtutils.add_action(self, 'Focus Status Window',
                           lambda: focus_dock(self.statusdockwidget),
                           hotkeys.FOCUS_STATUS)

        qtutils.add_action(self, 'Focus Diff Editor',
                           lambda: focus_dock(self.diffdockwidget),
                           hotkeys.FOCUS_DIFF)

    def preferences(self):
        return prefs_widget.preferences(model=self.prefs_model, parent=self)

    def git_dag(self):
        self.dag = dag.git_dag(self.model, existing_view=self.dag)
        view = self.dag
        view.show()
        view.raise_()

    def save_archive(self):
        oid = self.model.git.rev_parse('HEAD')[git.STDOUT]
        archive.show_save_dialog(oid, parent=self)

    def show_cursor_position(self, rows, cols):
        display = '%02d:%02d' % (rows, cols)
        css = """
            <style>
            .good {
            }
            .first-warning {
                color: black;
                background-color: yellow;
            }
            .second-warning {
                color: black;
                background-color: #f83;
            }
            .error {
                color: white;
                background-color: red;
            }
            </style>
        """

        if cols > 78:
            cls = 'error'
        elif cols > 72:
            cls = 'second-warning'
        elif cols > 64:
            cls = 'first-warning'
        else:
            cls = 'good'
        div = ('<div class="%s">%s</div>' % (cls, display))
        self.position_label.setText(css + div)

    def rebase_start(self):
        cfg = gitcfg.current()
        if not cfg.get('rebase.autostash', False):
            if self.model.staged or self.model.unmerged or self.model.modified:
                Interaction.information(
                        N_('Unable to rebase'),
                        N_('You cannot rebase with uncommitted changes.'))
                return
        upstream = guicmds.choose_ref(N_('Select New Upstream'),
                                      N_('Interactive Rebase'),
                                      default='@{upstream}')
        if not upstream:
            return
        self.model.is_rebasing = True
        self.refresh()
        cmds.do(cmds.Rebase, upstream=upstream)

    def rebase_edit_todo(self):
        cmds.do(cmds.RebaseEditTodo)

    def rebase_continue(self):
        cmds.do(cmds.RebaseContinue)

    def rebase_skip(self):
        cmds.do(cmds.RebaseSkip)

    def rebase_abort(self):
        cmds.do(cmds.RebaseAbort)

    def clone_repo(self):
        progress = standard.ProgressDialog('', '', self)
        guicmds.clone_repo(self, self.runtask, progress,
                           guicmds.report_clone_repo_errors, True)


def show_dock(dockwidget):
    dockwidget.raise_()
    dockwidget.widget().setFocus()


def focus_dock(dockwidget):
    if dockwidget.toggleViewAction().isChecked():
        show_dock(dockwidget)
    else:
        dockwidget.toggleViewAction().trigger()
