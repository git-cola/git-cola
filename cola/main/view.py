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
from cola import merge
from cola import gitcfg
from cola import prefs
from cola import qtutils
from cola import qtcompat
from cola import resources
from cola import settings
from cola import stash
from cola import utils
from cola import version
from cola.bookmarks import manage_bookmarks
from cola.classic import cola_classic
from cola.classic import classic_widget
from cola.dag import git_dag
from cola.git import git
from cola.i18n import N_
from cola.interaction import Interaction
from cola.qt import create_dock
from cola.qt import create_menu
from cola.qtutils import add_action
from cola.qtutils import connect_action
from cola.qtutils import connect_action_bool
from cola.widgets import action
from cola.widgets import cfgactions
from cola.widgets import editremotes
from cola.widgets import remote
from cola.widgets.about import launch_about_dialog
from cola.widgets.about import show_shortcuts
from cola.widgets.archive import GitArchiveDialog
from cola.widgets.commitmsg import CommitMessageEditor
from cola.widgets.compare import compare_branches
from cola.widgets.createtag import create_tag
from cola.widgets.createbranch import create_new_branch
from cola.widgets.diff import DiffEditor
from cola.widgets.log import LogWidget
from cola.widgets.recent import browse_recent
from cola.widgets.status import StatusWidget
from cola.widgets.search import search
from cola.widgets.standard import MainWindow


class MainView(MainWindow):
    def __init__(self, model, parent):
        MainWindow.__init__(self, parent)
        # Default size; this is thrown out when save/restore is used
        self.resize(987, 610)
        self.model = model
        self.prefs_model = prefs_model = prefs.PreferencesModel()

        # Internal field used by import/export_state().
        # Change this whenever dockwidgets are removed.
        self.widget_version = 2

        # Keeps track of merge messages we've seen
        self.merge_message_hash = ''

        self.setAcceptDrops(True)
        self.setAttribute(Qt.WA_MacMetalStyle)

        # Dockwidget options
        qtcompat.set_common_dock_options(self)

        cfg = gitcfg.instance()
        self.classic_dockable = (cfg.get('cola.browserdockable') or
                                 cfg.get('cola.classicdockable'))
        if self.classic_dockable:
            self.classicdockwidget = create_dock(N_('Browser'), self)
            self.classicwidget = classic_widget(self)
            self.classicdockwidget.setWidget(self.classicwidget)

        # "Actions" widget
        self.actionsdockwidget = create_dock(N_('Action'), self)
        self.actionsdockwidgetcontents = action.ActionButtons(self)
        self.actionsdockwidget.setWidget(self.actionsdockwidgetcontents)
        self.actionsdockwidget.toggleViewAction().setChecked(False)
        self.actionsdockwidget.hide()

        # "Repository Status" widget
        self.statuswidget = StatusWidget(self)
        self.statusdockwidget = create_dock(N_('Status'), self)
        self.statusdockwidget.setWidget(self.statuswidget)

        # "Commit Message Editor" widget
        self.position_label = QtGui.QLabel()
        font = qtutils.default_monospace_font()
        font.setPointSize(int(font.pointSize() * 0.8))
        self.position_label.setFont(font)
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
        self.menu_unstage_all = add_action(self,
                N_('Unstage All'), cmds.run(cmds.UnstageAll))
        self.menu_unstage_all.setIcon(qtutils.icon('remove.svg'))

        self.menu_unstage_selected = add_action(self,
                N_('Unstage From Commit'), cmds.run(cmds.UnstageSelected))
        self.menu_unstage_selected.setIcon(qtutils.icon('remove.svg'))

        self.menu_show_diffstat = add_action(self,
                N_('Diffstat'), cmds.run(cmds.Diffstat), 'Alt+D')

        self.menu_stage_modified = add_action(self,
                N_('Stage Changed Files To Commit'),
                cmds.run(cmds.StageModified), 'Alt+A')
        self.menu_stage_modified.setIcon(qtutils.icon('add.svg'))

        self.menu_stage_untracked = add_action(self,
                N_('Stage All Untracked'),
                cmds.run(cmds.StageUntracked), 'Alt+U')
        self.menu_stage_untracked.setIcon(qtutils.icon('add.svg'))

        self.menu_export_patches = add_action(self,
                N_('Export Patches...'), guicmds.export_patches, 'Alt+E')
        self.menu_preferences = add_action(self,
                N_('Preferences'), self.preferences,
                QtGui.QKeySequence.Preferences, 'Ctrl+O')

        self.menu_edit_remotes = add_action(self,
                N_('Edit Remotes...'), lambda: editremotes.edit().exec_())
        self.menu_rescan = add_action(self,
                cmds.RescanAndRefresh.name(),
                cmds.run(cmds.RescanAndRefresh),
                cmds.RescanAndRefresh.SHORTCUT)
        self.menu_rescan.setIcon(qtutils.reload_icon())

        self.menu_browse_recent = add_action(self,
                N_('Recently Modified Files...'),
                browse_recent, 'Shift+Ctrl+E')

        self.menu_cherry_pick = add_action(self,
                N_('Cherry-Pick...'),
                guicmds.cherry_pick, 'Ctrl+P')

        self.menu_load_commitmsg = add_action(self,
                N_('Load Commit Message...'), guicmds.load_commitmsg)

        self.menu_save_tarball = add_action(self,
                N_('Save As Tarball/Zip...'), self.save_archive)

        self.menu_quit = add_action(self,
                N_('Quit'), self.close, 'Ctrl+Q')
        self.menu_manage_bookmarks = add_action(self,
                N_('Bookmarks...'), manage_bookmarks)
        self.menu_grep = add_action(self,
                N_('Grep'), guicmds.grep, 'Ctrl+G')
        self.menu_merge_local = add_action(self,
                N_('Merge...'), merge.local_merge)

        self.menu_merge_abort = add_action(self,
                N_('Abort Merge...'), merge.abort_merge)

        self.menu_fetch = add_action(self,
                N_('Fetch...'), remote.fetch)
        self.menu_push = add_action(self,
                N_('Push...'), remote.push)
        self.menu_pull = add_action(self,
                N_('Pull...'), remote.pull)

        self.menu_open_repo = add_action(self,
                N_('Open...'), guicmds.open_repo)
        self.menu_open_repo.setIcon(qtutils.open_icon())

        self.menu_stash = add_action(self,
                N_('Stash...'), stash.stash, 'Alt+Shift+S')

        self.menu_clone_repo = add_action(self,
                N_('Clone...'), guicmds.clone_repo)
        self.menu_clone_repo.setIcon(qtutils.git_icon())

        self.menu_help_docs = add_action(self,
                N_('Documentation'), resources.show_html_docs,
                QtGui.QKeySequence.HelpContents)

        self.menu_help_shortcuts = add_action(self,
                N_('Keyboard Shortcuts'),
                show_shortcuts,
                QtCore.Qt.Key_Question)

        self.menu_visualize_current = add_action(self,
                N_('Visualize Current Branch...'),
                cmds.run(cmds.VisualizeCurrent))
        self.menu_visualize_all = add_action(self,
                N_('Visualize All Branches...'),
                cmds.run(cmds.VisualizeAll))
        self.menu_search_commits = add_action(self,
                N_('Search...'), search)
        self.menu_browse_branch = add_action(self,
                N_('Browse Current Branch...'), guicmds.browse_current)
        self.menu_browse_other_branch = add_action(self,
                N_('Browse Other Branch...'), guicmds.browse_other)
        self.menu_load_commitmsg_template = add_action(self,
                N_('Get Commit Message Template'),
                cmds.run(cmds.LoadCommitTemplate))
        self.menu_help_about = add_action(self,
                N_('About'), launch_about_dialog)

        self.menu_branch_diff = add_action(self,
                N_('SHA-1...'), guicmds.diff_revision)
        self.menu_diff_expression = add_action(self,
                N_('Expression...'), guicmds.diff_expression)
        self.menu_branch_compare = add_action(self,
                N_('Branches...'), compare_branches)

        self.menu_create_tag = add_action(self,
                N_('Create Tag...'), create_tag)

        self.menu_create_branch = add_action(self,
                N_('Create...'), create_new_branch, 'Ctrl+B')

        self.menu_delete_branch = add_action(self,
                N_('Delete...'), guicmds.branch_delete)

        self.menu_checkout_branch = add_action(self,
                N_('Checkout...'), guicmds.checkout_branch, 'Alt+B')
        self.menu_rebase_branch = add_action(self,
                N_('Rebase...'), guicmds.rebase)
        self.menu_branch_review = add_action(self,
                N_('Review...'), guicmds.review_branch)

        self.menu_classic = add_action(self,
                N_('Browser...'), cola_classic)
        self.menu_classic.setIcon(qtutils.git_icon())

        self.menu_dag = add_action(self,
                N_('DAG...'), lambda: git_dag(self.model))
        self.menu_dag.setIcon(qtutils.git_icon())

        # Relayed actions
        if not self.classic_dockable:
            # These shortcuts conflict with those from the
            # 'Browser' widget so don't register them when
            # the browser is a dockable tool.
            status_tree = self.statusdockwidget.widget().tree
            self.addAction(status_tree.up)
            self.addAction(status_tree.down)
            self.addAction(status_tree.process_selection)

        # Create the application menu
        self.menubar = QtGui.QMenuBar(self)

        # File Menu
        self.file_menu = create_menu(N_('File'), self.menubar)
        self.file_menu.addAction(self.menu_preferences)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_open_repo)
        self.menu_open_recent = self.file_menu.addMenu(N_('Open Recent'))
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_clone_repo)
        self.file_menu.addAction(self.menu_manage_bookmarks)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_edit_remotes)
        self.file_menu.addAction(self.menu_rescan)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_browse_recent)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_load_commitmsg)
        self.file_menu.addAction(self.menu_load_commitmsg_template)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_save_tarball)
        self.file_menu.addAction(self.menu_quit)
        # Add to menubar
        self.menubar.addAction(self.file_menu.menuAction())

        # Commit Menu
        self.commit_menu = create_menu(N_('Commit@@verb'), self.menubar)
        self.commit_menu.setTitle(N_('Commit@@verb'))
        self.commit_menu.addAction(self.menu_stage_modified)
        self.commit_menu.addAction(self.menu_stage_untracked)
        self.commit_menu.addSeparator()
        self.commit_menu.addAction(self.menu_unstage_all)
        self.commit_menu.addAction(self.menu_unstage_selected)
        self.commit_menu.addSeparator()
        self.commit_menu.addAction(self.menu_search_commits)
        # Add to menubar
        self.menubar.addAction(self.commit_menu.menuAction())

        # Branch Menu
        self.branch_menu = create_menu(N_('Branch'), self.menubar)
        self.branch_menu.addAction(self.menu_branch_review)
        self.branch_menu.addSeparator()
        self.branch_menu.addAction(self.menu_create_branch)
        self.branch_menu.addAction(self.menu_checkout_branch)
        self.branch_menu.addAction(self.menu_rebase_branch)
        self.branch_menu.addAction(self.menu_delete_branch)
        self.branch_menu.addSeparator()
        self.branch_menu.addAction(self.menu_browse_branch)
        self.branch_menu.addAction(self.menu_browse_other_branch)
        self.branch_menu.addSeparator()
        self.branch_menu.addAction(self.menu_visualize_current)
        self.branch_menu.addAction(self.menu_visualize_all)
        # Add to menubar
        self.menubar.addAction(self.branch_menu.menuAction())

        # Actions menu
        self.actions_menu = create_menu(N_('Actions'), self.menubar)
        self.actions_menu.addAction(self.menu_merge_local)
        self.actions_menu.addAction(self.menu_stash)
        self.actions_menu.addSeparator()
        self.actions_menu.addAction(self.menu_fetch)
        self.actions_menu.addAction(self.menu_push)
        self.actions_menu.addAction(self.menu_pull)
        self.actions_menu.addSeparator()
        self.actions_menu.addAction(self.menu_create_tag)
        self.actions_menu.addSeparator()
        self.actions_menu.addAction(self.menu_export_patches)
        self.actions_menu.addAction(self.menu_cherry_pick)
        self.actions_menu.addSeparator()
        self.actions_menu.addAction(self.menu_merge_abort)
        self.actions_menu.addAction(self.menu_grep)
        # Add to menubar
        self.menubar.addAction(self.actions_menu.menuAction())

        # Diff Menu
        self.diff_menu = create_menu(N_('Diff'), self.menubar)
        self.diff_menu.addAction(self.menu_branch_diff)
        self.diff_menu.addAction(self.menu_diff_expression)
        self.diff_menu.addAction(self.menu_branch_compare)
        self.diff_menu.addSeparator()
        self.diff_menu.addAction(self.menu_show_diffstat)
        # Add to menubar
        self.menubar.addAction(self.diff_menu.menuAction())

        # Tools Menu
        self.tools_menu = create_menu(N_('Tools'), self.menubar)
        self.tools_menu.addAction(self.menu_classic)
        self.tools_menu.addAction(self.menu_dag)
        self.tools_menu.addSeparator()
        if self.classic_dockable:
            self.tools_menu.addAction(self.classicdockwidget.toggleViewAction())

        self.setup_dockwidget_tools_menu()
        self.menubar.addAction(self.tools_menu.menuAction())

        # Help Menu
        self.help_menu = create_menu(N_('Help'), self.menubar)
        self.help_menu.addAction(self.menu_help_docs)
        self.help_menu.addAction(self.menu_help_shortcuts)
        self.help_menu.addAction(self.menu_help_about)
        # Add to menubar
        self.menubar.addAction(self.help_menu.menuAction())

        # Set main menu
        self.setMenuBar(self.menubar)

        # Arrange dock widgets
        left = Qt.LeftDockWidgetArea
        right = Qt.RightDockWidgetArea
        bottom = Qt.BottomDockWidgetArea

        self.addDockWidget(left, self.commitdockwidget)
        if self.classic_dockable:
            self.addDockWidget(left, self.classicdockwidget)
            self.tabifyDockWidget(self.classicdockwidget, self.commitdockwidget)
        self.addDockWidget(left, self.diffdockwidget)
        self.addDockWidget(bottom, self.actionsdockwidget)
        self.addDockWidget(bottom, self.logdockwidget)
        self.tabifyDockWidget(self.actionsdockwidget, self.logdockwidget)

        self.addDockWidget(right, self.statusdockwidget)

        # Listen for model notifications
        model.add_observer(model.message_updated, self._update_view)

        prefs_model.add_observer(prefs_model.message_config_updated,
                                 self._config_updated)

        # Set a default value
        self.show_cursor_position(1, 0)

        self.connect(self.menu_open_recent, SIGNAL('aboutToShow()'),
                     self.build_recent_menu)

        self.connect(self.commitmsgeditor, SIGNAL('cursorPosition(int,int)'),
                     self.show_cursor_position)
        self.connect(self, SIGNAL('update'), self._update_callback)
        self.connect(self, SIGNAL('install_config_actions'),
                     self._install_config_actions)

        # Install .git-config-defined actions
        self._config_task = None
        self.install_config_actions()

        self.dockwidgets = (
                self.logdockwidget,
                self.commitdockwidget,
                self.statusdockwidget,
                self.diffdockwidget,
                self.actionsdockwidget,
        )
        # Restore saved settings
        if not qtutils.apply_state(self):
            self.set_initial_size()

        self.statusdockwidget.widget().setFocus()

        # Route command output here
        Interaction.log_status = self.logwidget.log_status
        Interaction.log = self.logwidget.log

        Interaction.log(version.git_version_str() + '\n' +
                        N_('git-cola version %s') % version.version())

    def set_initial_size(self):
        self.statuswidget.set_initial_size()
        self.commitmsgeditor.set_initial_size()

    # Qt overrides
    def closeEvent(self, event):
        """Save state in the settings manager."""
        s = settings.Settings()
        s.add_recent(core.decode(os.getcwd()))
        qtutils.save_state(self, handler=s)
        MainWindow.closeEvent(self, event)

    def build_recent_menu(self):
        recent = settings.Settings().recent
        menu = self.menu_open_recent
        menu.clear()
        for r in recent:
            name = os.path.basename(r)
            directory = os.path.dirname(r)
            text = '%s %s %s' % (name, unichr(0x2192), directory)
            menu.addAction(text, cmds.run(cmds.OpenRepo, r))

    # Accessors
    mode = property(lambda self: self.model.mode)

    def _config_updated(self, source, config, value):
        if config == 'cola.fontdiff':
            # The diff font
            font = QtGui.QFont()
            if not font.fromString(value):
                return
            self.logwidget.setFont(font)
            self.diffeditor.setFont(font)
            self.commitmsgeditor.setFont(font)

        elif config == 'cola.tabwidth':
            # variable-tab-width setting
            self.diffeditor.set_tabwidth(value)
            self.commitmsgeditor.set_tabwidth(value)

        elif config == 'cola.linebreak':
            # enables automatic line breaks
            self.commitmsgeditor.set_linebreak(value)

        elif config == 'cola.textwidth':
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

    def _update_view(self):
        self.emit(SIGNAL('update'))

    def _update_callback(self):
        """Update the title with the current branch and directory name."""
        branch = self.model.currentbranch
        curdir = core.decode(os.getcwd())
        msg = N_('Repository: %s') % curdir
        msg += '\n'
        msg += N_('Branch: %s') % branch
        self.commitdockwidget.setToolTip(msg)

        title = '%s: %s' % (self.model.project, branch)
        if self.mode == self.model.mode_amend:
            title += ' (%s)' %  N_('Amending')
        self.setWindowTitle(title)

        self.commitmsgeditor.set_mode(self.mode)

        if not self.model.amending():
            # Check if there's a message file in .git/
            merge_msg_path = gitcmds.merge_message_path()
            if merge_msg_path is None:
                return
            merge_msg_hash = utils.checksum(core.decode(merge_msg_path))
            if merge_msg_hash == self.merge_message_hash:
                return
            self.merge_message_hash = merge_msg_hash
            cmds.do(cmds.LoadCommitMessage, core.decode(merge_msg_path))

    def apply_state(self, state):
        """Imports data for save/restore"""
        # 1 is the widget version; change when widgets are added/removed
        MainWindow.apply_state(self, state)
        result = qtutils.apply_window_state(self, state, self.widget_version)
        for widget in self.dockwidgets:
            widget.titleBarWidget().update_tooltips()
        return result

    def export_state(self):
        """Exports data for save/restore"""
        state = MainWindow.export_state(self)
        return qtutils.export_window_state(self, state, self.widget_version)

    def setup_dockwidget_tools_menu(self):
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
        )
        for shortcut, dockwidget in dockwidgets:
            # Associate the action with the shortcut
            toggleview = dockwidget.toggleViewAction()
            toggleview.setShortcut(shortcut)
            self.tools_menu.addAction(toggleview)
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
            toggleview.setShortcut('Shift+' + shortcut)
            def focusdock(dockwidget=dockwidget, showdock=showdock):
                if dockwidget.toggleViewAction().isChecked():
                    showdock(True)
                else:
                    dockwidget.toggleViewAction().trigger()
            self.addAction(toggleview)
            connect_action(toggleview, focusdock)

    def preferences(self):
        return prefs.preferences(model=self.prefs_model, parent=self)

    def save_archive(self):
        ref = git.rev_parse('HEAD')
        shortref = ref[:7]
        GitArchiveDialog.save(ref, shortref, self)

    def dragEnterEvent(self, event):
        """Accepts drops"""
        MainWindow.dragEnterEvent(self, event)
        event.acceptProposedAction()

    def dropEvent(self, event):
        """Apply dropped patches with git-am"""
        event.accept()
        urls = event.mimeData().urls()
        if not urls:
            return
        paths = map(lambda x: unicode(x.path()), urls)
        patches = [p for p in paths if p.endswith('.patch')]
        dirs = [p for p in paths if os.path.isdir(p)]
        dirs.sort()
        for d in dirs:
            patches.extend(self._gather_patches(d))
        cmds.do(cmds.ApplyPatches, patches)

    def _gather_patches(self, path):
        """Find patches in a subdirectory"""
        patches = []
        for root, subdirs, files in os.walk(path):
            for name in [f for f in files if f.endswith('.patch')]:
                patches.append(os.path.join(root, name))
        return patches

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
