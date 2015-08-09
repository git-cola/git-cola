"""This view provides the main git-cola user interface.
"""
from __future__ import division, absolute_import, unicode_literals

import os

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import guicmds
from cola import gitcfg
from cola import qtutils
from cola import resources
from cola import utils
from cola import version
from cola.compat import unichr
from cola.git import git
from cola.git import STDOUT
from cola.guicmds import TaskRunner
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import prefs
from cola.qtutils import add_action
from cola.qtutils import add_action_bool
from cola.qtutils import connect_action
from cola.qtutils import connect_action_bool
from cola.qtutils import create_dock
from cola.qtutils import create_menu
from cola.settings import Settings
from cola.widgets import about
from cola.widgets import action
from cola.widgets import archive
from cola.widgets import bookmarks
from cola.widgets import browse
from cola.widgets import cfgactions
from cola.widgets import commitmsg
from cola.widgets import compare
from cola.widgets import createbranch
from cola.widgets import createtag
from cola.widgets import dag
from cola.widgets import diff
from cola.widgets import finder
from cola.widgets import editremotes
from cola.widgets import grep
from cola.widgets import log
from cola.widgets import merge
from cola.widgets import patch
from cola.widgets import prefs as prefs_widget
from cola.widgets import recent
from cola.widgets import remote
from cola.widgets import search
from cola.widgets import standard
from cola.widgets import status
from cola.widgets import stash


class MainView(standard.MainWindow):

    def __init__(self, model, parent=None, settings=None):
        standard.MainWindow.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)

        # Default size; this is thrown out when save/restore is used
        self.model = model
        self.settings = settings
        self.prefs_model = prefs_model = prefs.PreferencesModel()

        # The widget version is used by import/export_state().
        # Change this whenever dockwidgets are removed.
        self.widget_version = 2

        # Runs asynchronous tasks
        self.task_runner = TaskRunner(self)
        self.progress = standard.ProgressDialog('', '', self)

        cfg = gitcfg.current()
        self.browser_dockable = (cfg.get('cola.browserdockable') or
                                 cfg.get('cola.classicdockable'))
        if self.browser_dockable:
            self.browserdockwidget = create_dock(N_('Browser'), self)
            self.browserwidget = browse.worktree_browser_widget(self)
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

        # "Commit Message Editor" widget
        self.position_label = QtGui.QLabel()
        font = qtutils.default_monospace_font()
        font.setPointSize(int(font.pointSize() * 0.8))
        self.position_label.setFont(font)

        # make the position label fixed size to avoid layout issues
        fm = self.position_label.fontMetrics()
        width = fm.width('999:999')
        height = self.position_label.sizeHint().height()
        self.position_label.setFixedSize(width, height)

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
        self.unstage_all_action = add_action(self,
                N_('Unstage All'), cmds.run(cmds.UnstageAll))
        self.unstage_all_action.setIcon(qtutils.remove_icon())

        self.unstage_selected_action = add_action(self,
                N_('Unstage From Commit'), cmds.run(cmds.UnstageSelected))
        self.unstage_selected_action.setIcon(qtutils.remove_icon())

        self.show_diffstat_action = add_action(self,
                N_('Diffstat'), cmds.run(cmds.Diffstat), 'Alt+D')

        self.stage_modified_action = add_action(self,
                N_('Stage Changed Files To Commit'),
                cmds.run(cmds.StageModified), 'Alt+A')
        self.stage_modified_action.setIcon(qtutils.add_icon())

        self.stage_untracked_action = add_action(self,
                N_('Stage All Untracked'),
                cmds.run(cmds.StageUntracked), 'Alt+U')
        self.stage_untracked_action.setIcon(qtutils.add_icon())

        self.apply_patches_action = add_action(self,
                N_('Apply Patches...'), patch.apply_patches)

        self.export_patches_action = add_action(self,
                N_('Export Patches...'), guicmds.export_patches, 'Alt+E')

        self.new_repository_action = add_action(self,
                N_('New Repository...'), guicmds.open_new_repo)
        self.new_repository_action.setIcon(qtutils.new_icon())

        self.preferences_action = add_action(self,
                N_('Preferences'), self.preferences,
                QtGui.QKeySequence.Preferences)

        self.edit_remotes_action = add_action(self,
                N_('Edit Remotes...'), lambda: editremotes.remote_editor().exec_())

        self.rescan_action = add_action(self,
                cmds.Refresh.name(),
                cmds.run(cmds.Refresh),
                *cmds.Refresh.SHORTCUTS)
        self.rescan_action.setIcon(qtutils.reload_icon())

        self.find_files_action = add_action(self,
                N_('Find Files'), finder.finder, 'Ctrl+T', 'T')
        self.find_files_action.setIcon(qtutils.theme_icon('zoom-in.png'))

        self.browse_recently_modified_action = add_action(self,
                N_('Recently Modified Files...'),
                recent.browse_recent_files, 'Ctrl+Shift+E')

        self.cherry_pick_action = add_action(self,
                N_('Cherry-Pick...'),
                guicmds.cherry_pick, 'Ctrl+Shift+C')

        self.load_commitmsg_action = add_action(self,
                N_('Load Commit Message...'), guicmds.load_commitmsg)

        self.save_tarball_action = add_action(self,
                N_('Save As Tarball/Zip...'), self.save_archive)

        self.quit_action = add_action(self,
                N_('Quit'), self.close, 'Ctrl+Q')
        self.grep_action = add_action(self,
                N_('Grep'), grep.grep, 'Ctrl+G')
        self.merge_local_action = add_action(self,
                N_('Merge...'), merge.local_merge, 'Ctrl+Shift+M')

        self.merge_abort_action = add_action(self,
                N_('Abort Merge...'), merge.abort_merge)

        self.fetch_action = add_action(self,
                N_('Fetch...'), remote.fetch, 'Ctrl+F')
        self.push_action = add_action(self,
                N_('Push...'), remote.push, 'Ctrl+P')
        self.pull_action = add_action(self,
                N_('Pull...'), remote.pull, 'Ctrl+Shift+P')

        self.open_repo_action = add_action(self,
                N_('Open...'), guicmds.open_repo)
        self.open_repo_action.setIcon(qtutils.open_icon())

        self.open_repo_new_action = add_action(self,
                N_('Open in New Window...'), guicmds.open_repo_in_new_window)
        self.open_repo_new_action.setIcon(qtutils.open_icon())

        self.stash_action = add_action(self,
                N_('Stash...'), stash.stash, 'Alt+Shift+S')

        self.clone_repo_action = add_action(self,
                N_('Clone...'), self.clone_repo)
        self.clone_repo_action.setIcon(qtutils.git_icon())

        self.help_docs_action = add_action(self,
                N_('Documentation'), resources.show_html_docs,
                QtGui.QKeySequence.HelpContents)

        self.help_shortcuts_action = add_action(self,
                N_('Keyboard Shortcuts'), about.show_shortcuts,
                Qt.Key_Question)

        self.visualize_current_action = add_action(self,
                N_('Visualize Current Branch...'),
                cmds.run(cmds.VisualizeCurrent))
        self.visualize_all_action = add_action(self,
                N_('Visualize All Branches...'),
                cmds.run(cmds.VisualizeAll))
        self.search_commits_action = add_action(self,
                N_('Search...'), search.search)
        self.browse_branch_action = add_action(self,
                N_('Browse Current Branch...'), guicmds.browse_current)
        self.browse_other_branch_action = add_action(self,
                N_('Browse Other Branch...'), guicmds.browse_other)
        self.load_commitmsg_template_action = add_action(self,
                N_('Get Commit Message Template'),
                cmds.run(cmds.LoadCommitMessageFromTemplate))
        self.help_about_action = add_action(self,
                N_('About'), about.launch_about_dialog)

        self.diff_expression_action = add_action(self,
                N_('Expression...'), guicmds.diff_expression)
        self.branch_compare_action = add_action(self,
                N_('Branches...'), compare.compare_branches)

        self.create_tag_action = add_action(self,
                N_('Create Tag...'), createtag.create_tag)

        self.create_branch_action = add_action(self,
                N_('Create...'), createbranch.create_new_branch, 'Ctrl+B')

        self.delete_branch_action = add_action(self,
                N_('Delete...'), guicmds.delete_branch)

        self.delete_remote_branch_action = add_action(self,
                N_('Delete Remote Branch...'), guicmds.delete_remote_branch)

        self.rename_branch_action = add_action(self,
                N_('Rename Branch...'), guicmds.rename_branch)

        self.checkout_branch_action = add_action(self,
                N_('Checkout...'), guicmds.checkout_branch, 'Alt+B')
        self.branch_review_action = add_action(self,
                N_('Review...'), guicmds.review_branch)

        self.browse_action = add_action(self,
                N_('File Browser...'), browse.worktree_browser)
        self.browse_action.setIcon(qtutils.git_icon())

        self.dag_action = add_action(self, N_('DAG...'), self.git_dag)
        self.dag_action.setIcon(qtutils.git_icon())

        self.rebase_start_action = add_action(self,
                N_('Start Interactive Rebase...'), self.rebase_start)

        self.rebase_edit_todo_action = add_action(self,
                N_('Edit...'), self.rebase_edit_todo)

        self.rebase_continue_action = add_action(self,
                N_('Continue'), self.rebase_continue)

        self.rebase_skip_action = add_action(self,
                N_('Skip Current Patch'), self.rebase_skip)

        self.rebase_abort_action = add_action(self,
                N_('Abort'), self.rebase_abort)

        self.lock_layout_action = add_action_bool(self,
                N_('Lock Layout'), self.set_lock_layout, False)

        # Create the application menu
        self.menubar = QtGui.QMenuBar(self)

        # File Menu
        self.file_menu = create_menu(N_('File'), self.menubar)
        self.file_menu.addAction(self.new_repository_action)
        self.open_recent_menu = self.file_menu.addMenu(N_('Open Recent'))
        self.open_recent_menu.setIcon(qtutils.open_icon())
        self.file_menu.addAction(self.open_repo_action)
        self.file_menu.addAction(self.open_repo_new_action)
        self.file_menu.addAction(self.clone_repo_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.rescan_action)
        self.file_menu.addAction(self.find_files_action)
        self.file_menu.addAction(self.edit_remotes_action)
        self.file_menu.addAction(self.browse_recently_modified_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.load_commitmsg_action)
        self.file_menu.addAction(self.load_commitmsg_template_action)
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
        self.actions_menu.addAction(self.grep_action)
        self.actions_menu.addAction(self.search_commits_action)
        self.menubar.addAction(self.actions_menu.menuAction())

        # Staging Area Menu
        self.commit_menu = create_menu(N_('Staging Area'), self.menubar)
        self.commit_menu.setTitle(N_('Staging Area'))
        self.commit_menu.addAction(self.stage_modified_action)
        self.commit_menu.addAction(self.stage_untracked_action)
        self.commit_menu.addSeparator()
        self.commit_menu.addAction(self.unstage_all_action)
        self.commit_menu.addAction(self.unstage_selected_action)
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
        self.addDockWidget(right, self.recentdockwidget)
        self.addDockWidget(bottom, self.actionsdockwidget)
        self.addDockWidget(bottom, self.logdockwidget)
        self.tabifyDockWidget(self.actionsdockwidget, self.logdockwidget)


        # Listen for model notifications
        model.add_observer(model.message_updated, self._update)
        model.add_observer(model.message_mode_changed, lambda x: self._update())

        prefs_model.add_observer(prefs_model.message_config_updated,
                                 self._config_updated)

        # Set a default value
        self.show_cursor_position(1, 0)

        self.connect(self.open_recent_menu, SIGNAL('aboutToShow()'),
                     self.build_recent_menu)

        self.connect(self.commitmsgeditor, SIGNAL('cursorPosition(int,int)'),
                     self.show_cursor_position)

        self.connect(self.diffeditor, SIGNAL('diff_options_updated()'),
                     self.statuswidget.refresh)

        self.connect(self.diffeditor, SIGNAL('move_down()'),
                     self.statuswidget.move_down)

        self.connect(self.diffeditor, SIGNAL('move_up()'),
                     self.statuswidget.move_up)

        self.connect(self.commitmsgeditor, SIGNAL('move_down()'),
                     self.statuswidget.move_down)

        self.connect(self.commitmsgeditor, SIGNAL('move_up()'),
                     self.statuswidget.move_up)

        self.connect(self, SIGNAL('update()'),
                     self._update_callback, Qt.QueuedConnection)

        self.connect(self, SIGNAL('install_cfg_actions(PyQt_PyObject)'),
                     self._install_config_actions, Qt.QueuedConnection)

        # Install .git-config-defined actions
        self._config_task = None
        self.install_config_actions()

        # Restore saved settings
        if not self.restore_state(settings=settings):
            self.resize(987, 610)
            self.set_initial_size()

        self.statusdockwidget.widget().setFocus()

        # Route command output here
        Interaction.log_status = self.logwidget.log_status
        Interaction.log = self.logwidget.log
        Interaction.log(version.git_version_str() + '\n' +
                        N_('git cola version %s') % version.version())

    def set_initial_size(self):
        self.statuswidget.set_initial_size()
        self.commitmsgeditor.set_initial_size()

    def set_filter(self, txt):
        self.statuswidget.set_filter(txt)

    # Qt overrides
    def closeEvent(self, event):
        """Save state in the settings manager."""
        commit_msg = self.commitmsgeditor.commit_message(raw=True)
        self.model.save_commitmsg(commit_msg)
        standard.MainWindow.closeEvent(self, event)

    def build_recent_menu(self):
        settings = Settings()
        settings.load()
        recent = settings.recent
        cmd = cmds.OpenRepo
        menu = self.open_recent_menu
        menu.clear()
        for r in recent:
            name = os.path.basename(r)
            directory = os.path.dirname(r)
            text = '%s %s %s' % (name, unichr(0x2192), directory)
            menu.addAction(text, cmds.run(cmd, r))

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

    def install_config_actions(self):
        """Install .gitconfig-defined actions"""
        self._config_task = self._start_config_actions_task()

    def _start_config_actions_task(self):
        """Do the expensive "get_config_actions()" call in the background"""
        class ConfigActionsTask(QtCore.QRunnable):
            def __init__(self, sender):
                QtCore.QRunnable.__init__(self)
                self._sender = sender
            def run(self):
                actions = cfgactions.get_config_actions()
                self._sender.emit(SIGNAL('install_cfg_actions(PyQt_PyObject)'),
                                  actions)

        task = ConfigActionsTask(self)
        QtCore.QThreadPool.globalInstance().start(task)
        return task

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

    def _update(self):
        self.emit(SIGNAL('update()'))

    def _update_callback(self):
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
        can_rebase = not is_rebasing
        self.rebase_start_action.setEnabled(can_rebase)
        self.rebase_edit_todo_action.setEnabled(is_rebasing)
        self.rebase_continue_action.setEnabled(is_rebasing)
        self.rebase_skip_action.setEnabled(is_rebasing)
        self.rebase_abort_action.setEnabled(is_rebasing)
        self.rename_branch_action.setEnabled(not self.model.is_empty_repository())
        self.delete_branch_action.setEnabled(not self.model.is_empty_repository())

    def export_state(self):
        state = standard.MainWindow.export_state(self)
        show_status_filter = self.statuswidget.filter_widget.isVisible()
        state['show_status_filter'] = show_status_filter
        return state

    def apply_state(self, state):
        """Imports data for save/restore"""
        result = standard.MainWindow.apply_state(self, state)
        self.lock_layout_action.setChecked(state.get('lock_layout', False))

        show_status_filter = state.get('show_status_filter', False)
        self.statuswidget.filter_widget.setVisible(show_status_filter)
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
            connect_action_bool(toggleview, showdock)

            # Create a new shortcut Shift+<shortcut> that gives focus
            toggleview = QtGui.QAction(self)
            toggleview.setShortcut(shortcut)
            def focusdock(dockwidget=dockwidget):
                focus_dock(dockwidget)
            self.addAction(toggleview)
            connect_action(toggleview, focusdock)

        qtutils.add_action(self, 'Focus Commit Message',
                           lambda: focus_dock(self.commitdockwidget), 'Ctrl+L')

    def preferences(self):
        return prefs_widget.preferences(model=self.prefs_model, parent=self)

    def git_dag(self):
        view = dag.git_dag(self.model)
        view.show()
        view.raise_()

    def save_archive(self):
        ref = git.rev_parse('HEAD')[STDOUT]
        shortref = ref[:7]
        archive.GitArchiveDialog.save_hashed_objects(ref, shortref, self)

    def show_cursor_position(self, rows, cols):
        display = '&nbsp;%02d:%02d&nbsp;' % (rows, cols)
        if cols > 78:
            display = ('<span style="color: white; '
                       '             background-color: red;"'
                       '>%s</span>' % display)
        elif cols > 72:
            display = ('<span style="color: black; '
                       '             background-color: orange;"'
                       '>%s</span>' % display)
        elif cols > 64:
            display = ('<span style="color: black; '
                       '             background-color: yellow;"'
                       '>%s</span>' % display)
        else:
            display = ('<span style="color: grey;">%s</span>' % display)

        self.position_label.setText(display)

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
        self._update_callback()
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
        guicmds.clone_repo(self.task_runner, self.progress,
                           guicmds.report_clone_repo_errors, True)


def show_dock(dockwidget):
    dockwidget.raise_()
    dockwidget.widget().setFocus()


def focus_dock(dockwidget):
    if dockwidget.toggleViewAction().isChecked():
        show_dock(dockwidget)
    else:
        dockwidget.toggleViewAction().trigger()
