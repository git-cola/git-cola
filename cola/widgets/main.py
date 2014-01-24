"""This view provides the main git-cola user interface.
"""
import os

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import gitcmds
from cola import guicmds
from cola import gitcfg
from cola import qtutils
from cola import resources
from cola import settings
from cola import utils
from cola import version
from cola.git import git
from cola.git import STDOUT
from cola.i18n import N_
from cola.interaction import Interaction
from cola.models import prefs
from cola.qtutils import add_action
from cola.qtutils import add_action_bool
from cola.qtutils import connect_action
from cola.qtutils import connect_action_bool
from cola.qtutils import create_dock
from cola.qtutils import create_menu
from cola.widgets import action
from cola.widgets import cfgactions
from cola.widgets import editremotes
from cola.widgets import merge
from cola.widgets import remote
from cola.widgets.about import launch_about_dialog
from cola.widgets.about import show_shortcuts
from cola.widgets.archive import GitArchiveDialog
from cola.widgets.bookmarks import manage_bookmarks
from cola.widgets.bookmarks import BookmarksWidget
from cola.widgets.browse import worktree_browser
from cola.widgets.browse import worktree_browser_widget
from cola.widgets.commitmsg import CommitMessageEditor
from cola.widgets.compare import compare_branches
from cola.widgets.createtag import create_tag
from cola.widgets.createbranch import create_new_branch
from cola.widgets.dag import git_dag
from cola.widgets.diff import DiffEditor
from cola.widgets.grep import grep
from cola.widgets.log import LogWidget
from cola.widgets.patch import apply_patches
from cola.widgets.prefs import preferences
from cola.widgets.recent import browse_recent_files
from cola.widgets.status import StatusWidget
from cola.widgets.search import search
from cola.widgets.standard import MainWindow
from cola.widgets.stash import stash


class MainView(MainWindow):

    def __init__(self, model, parent=None):
        MainWindow.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)

        # Default size; this is thrown out when save/restore is used
        self.resize(987, 610)
        self.model = model
        self.prefs_model = prefs_model = prefs.PreferencesModel()

        # The widget version is used by import/export_state().
        # Change this whenever dockwidgets are removed.
        self.widget_version = 2

        # Keeps track of merge messages we've seen
        self.merge_message_hash = ''

        cfg = gitcfg.instance()
        self.browser_dockable = (cfg.get('cola.browserdockable') or
                                 cfg.get('cola.classicdockable'))
        if self.browser_dockable:
            self.browserdockwidget = create_dock(N_('Browser'), self)
            self.browserwidget = worktree_browser_widget(self)
            self.browserdockwidget.setWidget(self.browserwidget)

        # "Actions" widget
        self.actionsdockwidget = create_dock(N_('Actions'), self)
        self.actionsdockwidgetcontents = action.ActionButtons(self)
        self.actionsdockwidget.setWidget(self.actionsdockwidgetcontents)
        self.actionsdockwidget.toggleViewAction().setChecked(False)
        self.actionsdockwidget.hide()

        # "Repository Status" widget
        self.statuswidget = StatusWidget(self)
        self.statusdockwidget = create_dock(N_('Status'), self)
        self.statusdockwidget.setWidget(self.statuswidget)

        # "Switch Repository" widget
        self.bookmarksdockwidget = create_dock(N_('Bookmarks'), self)
        self.bookmarkswidget = BookmarksWidget(parent=self.bookmarksdockwidget)
        self.bookmarksdockwidget.setWidget(self.bookmarkswidget)

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

        self.commitmsgeditor = CommitMessageEditor(model, self)
        self.commitdockwidget.setWidget(self.commitmsgeditor)

        # "Console" widget
        self.logwidget = LogWidget()
        self.logdockwidget = create_dock(N_('Console'), self)
        self.logdockwidget.setWidget(self.logwidget)
        self.logdockwidget.toggleViewAction().setChecked(False)
        self.logdockwidget.hide()

        # "Diff Viewer" widget
        self.diffdockwidget = create_dock(N_('Diff'), self)
        self.diffeditor = DiffEditor(self.diffdockwidget)
        self.diffdockwidget.setWidget(self.diffeditor)

        # All Actions
        self.unstage_all_action = add_action(self,
                N_('Unstage All'), cmds.run(cmds.UnstageAll))
        self.unstage_all_action.setIcon(qtutils.icon('remove.svg'))

        self.unstage_selected_action = add_action(self,
                N_('Unstage From Commit'), cmds.run(cmds.UnstageSelected))
        self.unstage_selected_action.setIcon(qtutils.icon('remove.svg'))

        self.show_diffstat_action = add_action(self,
                N_('Diffstat'), cmds.run(cmds.Diffstat), 'Alt+D')

        self.stage_modified_action = add_action(self,
                N_('Stage Changed Files To Commit'),
                cmds.run(cmds.StageModified), 'Alt+A')
        self.stage_modified_action.setIcon(qtutils.icon('add.svg'))

        self.stage_untracked_action = add_action(self,
                N_('Stage All Untracked'),
                cmds.run(cmds.StageUntracked), 'Alt+U')
        self.stage_untracked_action.setIcon(qtutils.icon('add.svg'))

        self.apply_patches_action = add_action(self,
                N_('Apply Patches...'), apply_patches)

        self.export_patches_action = add_action(self,
                N_('Export Patches...'), guicmds.export_patches, 'Alt+E')

        self.new_repository_action = add_action(self,
                N_('New Repository...'), guicmds.open_new_repo)
        self.new_repository_action.setIcon(qtutils.new_icon())

        self.preferences_action = add_action(self,
                N_('Preferences'), self.preferences,
                QtGui.QKeySequence.Preferences, 'Ctrl+O')

        self.edit_remotes_action = add_action(self,
                N_('Edit Remotes...'), lambda: editremotes.remote_editor().exec_())
        self.rescan_action = add_action(self,
                cmds.Refresh.name(),
                cmds.run(cmds.Refresh),
                cmds.Refresh.SHORTCUT)
        self.rescan_action.setIcon(qtutils.reload_icon())

        self.browse_recently_modified_action = add_action(self,
                N_('Recently Modified Files...'),
                browse_recent_files, 'Shift+Ctrl+E')

        self.cherry_pick_action = add_action(self,
                N_('Cherry-Pick...'),
                guicmds.cherry_pick, 'Ctrl+P')

        self.load_commitmsg_action = add_action(self,
                N_('Load Commit Message...'), guicmds.load_commitmsg)

        self.save_tarball_action = add_action(self,
                N_('Save As Tarball/Zip...'), self.save_archive)

        self.quit_action = add_action(self,
                N_('Quit'), self.close, 'Ctrl+Q')
        self.manage_bookmarks_action = add_action(self,
                N_('Bookmarks...'), self.manage_bookmarks)
        self.grep_action = add_action(self,
                N_('Grep'), grep, 'Ctrl+G')
        self.merge_local_action = add_action(self,
                N_('Merge...'), merge.local_merge)

        self.merge_abort_action = add_action(self,
                N_('Abort Merge...'), merge.abort_merge)

        self.fetch_action = add_action(self,
                N_('Fetch...'), remote.fetch)
        self.push_action = add_action(self,
                N_('Push...'), remote.push)
        self.pull_action = add_action(self,
                N_('Pull...'), remote.pull)

        self.open_repo_action = add_action(self,
                N_('Open...'), guicmds.open_repo)
        self.open_repo_action.setIcon(qtutils.open_icon())

        self.open_repo_new_action = add_action(self,
                N_('Open in New Window...'), guicmds.open_repo_in_new_window)
        self.open_repo_new_action.setIcon(qtutils.open_icon())

        self.stash_action = add_action(self,
                N_('Stash...'), stash, 'Alt+Shift+S')

        self.clone_repo_action = add_action(self,
                N_('Clone...'), guicmds.clone_repo)
        self.clone_repo_action.setIcon(qtutils.git_icon())

        self.help_docs_action = add_action(self,
                N_('Documentation'), resources.show_html_docs,
                QtGui.QKeySequence.HelpContents)

        self.help_shortcuts_action = add_action(self,
                N_('Keyboard Shortcuts'),
                show_shortcuts,
                QtCore.Qt.Key_Question)

        self.visualize_current_action = add_action(self,
                N_('Visualize Current Branch...'),
                cmds.run(cmds.VisualizeCurrent))
        self.visualize_all_action = add_action(self,
                N_('Visualize All Branches...'),
                cmds.run(cmds.VisualizeAll))
        self.search_commits_action = add_action(self,
                N_('Search...'), search)
        self.browse_branch_action = add_action(self,
                N_('Browse Current Branch...'), guicmds.browse_current)
        self.browse_other_branch_action = add_action(self,
                N_('Browse Other Branch...'), guicmds.browse_other)
        self.load_commitmsg_template_action = add_action(self,
                N_('Get Commit Message Template'),
                cmds.run(cmds.LoadCommitMessageFromTemplate))
        self.help_about_action = add_action(self,
                N_('About'), launch_about_dialog)

        self.diff_expression_action = add_action(self,
                N_('Expression...'), guicmds.diff_expression)
        self.branch_compare_action = add_action(self,
                N_('Branches...'), compare_branches)

        self.create_tag_action = add_action(self,
                N_('Create Tag...'), create_tag)

        self.create_branch_action = add_action(self,
                N_('Create...'), create_new_branch, 'Ctrl+B')

        self.delete_branch_action = add_action(self,
                N_('Delete...'), guicmds.delete_branch)

        self.delete_remote_branch_action = add_action(self,
                N_('Delete Remote Branch...'), guicmds.delete_remote_branch)

        self.checkout_branch_action = add_action(self,
                N_('Checkout...'), guicmds.checkout_branch, 'Alt+B')
        self.branch_review_action = add_action(self,
                N_('Review...'), guicmds.review_branch)

        self.browse_action = add_action(self,
                N_('Browser...'), worktree_browser)
        self.browse_action.setIcon(qtutils.git_icon())

        self.dag_action = add_action(self,
                N_('DAG...'), lambda: git_dag(self.model).show())
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

        # Relayed actions
        status_tree = self.statusdockwidget.widget().tree
        self.addAction(status_tree.revert_unstaged_edits_action)
        if not self.browser_dockable:
            # These shortcuts conflict with those from the
            # 'Browser' widget so don't register them when
            # the browser is a dockable tool.
            self.addAction(status_tree.up)
            self.addAction(status_tree.down)
            self.addAction(status_tree.process_selection)

        self.lock_layout_action = add_action_bool(self,
                N_('Lock Layout'), self.set_lock_layout, False)

        # Create the application menu
        self.menubar = QtGui.QMenuBar(self)

        # File Menu
        self.file_menu = create_menu(N_('File'), self.menubar)
        self.open_recent_menu = self.file_menu.addMenu(N_('Open Recent'))
        self.open_recent_menu.setIcon(qtutils.open_icon())
        self.file_menu.addAction(self.open_repo_action)
        self.file_menu.addAction(self.open_repo_new_action)
        self.file_menu.addAction(self.clone_repo_action)
        self.file_menu.addAction(self.new_repository_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.rescan_action)
        self.file_menu.addAction(self.edit_remotes_action)
        self.file_menu.addAction(self.browse_recently_modified_action)
        self.file_menu.addAction(self.manage_bookmarks_action)
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

        # Index Menu
        self.commit_menu = create_menu(N_('Index'), self.menubar)
        self.commit_menu.setTitle(N_('Index'))
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

        self.connect(self, SIGNAL('update'), self._update_callback)
        self.connect(self, SIGNAL('install_config_actions'),
                     self._install_config_actions)

        # Install .git-config-defined actions
        self._config_task = None
        self.install_config_actions()

        # Restore saved settings
        if not qtutils.apply_state(self):
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

    # Qt overrides
    def closeEvent(self, event):
        """Save state in the settings manager."""
        commit_msg = self.commitmsgeditor.commit_message(raw=True)
        self.model.save_commitmsg(commit_msg)
        MainWindow.closeEvent(self, event)

    def build_recent_menu(self):
        recent = settings.Settings().recent
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
                names = cfgactions.get_config_actions()
                self._sender.emit(SIGNAL('install_config_actions'), names)

        task = ConfigActionsTask(self)
        QtCore.QThreadPool.globalInstance().start(task)
        return task

    def _install_config_actions(self, names):
        """Install .gitconfig-defined actions"""
        if not names:
            return
        menu = self.actions_menu
        menu.addSeparator()
        for name in names:
            menu.addAction(name, cmds.run(cmds.RunConfigAction, name))

    def _update(self):
        self.emit(SIGNAL('update'))

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

        if not self.model.amending():
            # Check if there's a message file in .git/
            merge_msg_path = gitcmds.merge_message_path()
            if merge_msg_path is None:
                return
            merge_msg_hash = utils.checksum(merge_msg_path)
            if merge_msg_hash == self.merge_message_hash:
                return
            self.merge_message_hash = merge_msg_hash
            cmds.do(cmds.LoadCommitMessageFromFile, merge_msg_path)

    def update_actions(self):
        is_rebasing = self.model.is_rebasing
        can_rebase = not is_rebasing
        self.rebase_start_action.setEnabled(can_rebase)
        self.rebase_edit_todo_action.setEnabled(is_rebasing)
        self.rebase_continue_action.setEnabled(is_rebasing)
        self.rebase_skip_action.setEnabled(is_rebasing)
        self.rebase_abort_action.setEnabled(is_rebasing)

    def apply_state(self, state):
        """Imports data for save/restore"""
        result = MainWindow.apply_state(self, state)
        self.lock_layout_action.setChecked(state.get('lock_layout', False))
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
            def focusdock(dockwidget=dockwidget, showdock=showdock):
                if dockwidget.toggleViewAction().isChecked():
                    showdock(True)
                else:
                    dockwidget.toggleViewAction().trigger()
            self.addAction(toggleview)
            connect_action(toggleview, focusdock)

    def preferences(self):
        return preferences(model=self.prefs_model, parent=self)

    def save_archive(self):
        ref = git.rev_parse('HEAD')[STDOUT]
        shortref = ref[:7]
        GitArchiveDialog.save_hashed_objects(ref, shortref, self)

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

    def manage_bookmarks(self):
        manage_bookmarks()
        self.bookmarkswidget.refresh()

    def rebase_start(self):
        branch = guicmds.choose_ref(N_('Select New Upstream'),
                                    N_('Interactive Rebase'))
        if not branch:
            return None
        self.model.is_rebasing = True
        self._update_callback()
        cmds.do(cmds.Rebase, branch)

    def rebase_edit_todo(self):
        cmds.do(cmds.RebaseEditTodo)

    def rebase_continue(self):
        cmds.do(cmds.RebaseContinue)

    def rebase_skip(self):
        cmds.do(cmds.RebaseSkip)

    def rebase_abort(self):
        cmds.do(cmds.RebaseAbort)
