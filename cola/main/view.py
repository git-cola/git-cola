"""This view provides the main git-cola user interface.
"""
import os

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import core
from cola import gitcmds
from cola import guicmds
from cola import merge
from cola import settings
from cola import signals
from cola import gitcfg
from cola import qtutils
from cola import qtcompat
from cola import qt
from cola import resources
from cola import stash
from cola import utils
from cola import version
from cola.bookmarks import manage_bookmarks
from cola.classic import cola_classic
from cola.classic import classic_widget
from cola.dag import git_dag
from cola.git import git
from cola.prefs import diff_font
from cola.prefs import PreferencesModel
from cola.prefs import preferences
from cola.qt import create_button
from cola.qt import create_dock
from cola.qt import create_menu
from cola.qtutils import add_action
from cola.qtutils import connect_action
from cola.qtutils import connect_action_bool
from cola.qtutils import connect_button
from cola.qtutils import emit
from cola.qtutils import log
from cola.qtutils import relay_signal
from cola.qtutils import tr
from cola.views import standard
from cola.widgets import cfgactions
from cola.widgets import remote
from cola.widgets.about import launch_about_dialog
from cola.widgets.about import show_shortcuts
from cola.widgets.archive import GitArchiveDialog
from cola.widgets.commitmsg import CommitMessageEditor
from cola.widgets.compare import compare_branches
from cola.widgets.createtag import create_tag
from cola.widgets.createbranch import create_new_branch
from cola.widgets.diff import DiffEditor
from cola.widgets.recent import browse_recent
from cola.widgets.status import StatusWidget
from cola.widgets.search import search


class MainView(standard.MainWindow):
    def __init__(self, model, parent):
        standard.MainWindow.__init__(self, parent)
        # Default size; this is thrown out when save/restore is used
        self.resize(987, 610)
        self.model = model
        self.prefs_model = prefs_model = PreferencesModel()

        # Internal field used by import/export_state().
        # Change this whenever dockwidgets are removed.
        self.widget_version = 1

        # Keeps track of merge messages we've seen
        self.merge_message_hash = ''

        self.setAcceptDrops(True)

        # Dockwidget options
        qtcompat.set_common_dock_options(self)

        self.classic_dockable = gitcfg.instance().get('cola.classicdockable')

        if self.classic_dockable:
            self.classicdockwidget = create_dock('Classic', self)
            self.classicwidget = classic_widget(self)
            self.classicdockwidget.setWidget(self.classicwidget)

        # "Actions" widget
        self.actionsdockwidget = create_dock('Action', self)
        self.actionsdockwidgetcontents = qt.QFlowLayoutWidget(self)
        layout = self.actionsdockwidgetcontents.layout()
        self.stage_button = create_button(text='Stage', layout=layout)
        self.unstage_button = create_button(text='Unstage', layout=layout)
        self.rescan_button = create_button(text='Rescan', layout=layout)
        self.fetch_button = create_button(text='Fetch...', layout=layout)
        self.push_button = create_button(text='Push...', layout=layout)
        self.pull_button = create_button(text='Pull...', layout=layout)
        self.stash_button = create_button(text='Stash...', layout=layout)
        self.alt_button = create_button(text='Exit Diff Mode', layout=layout)
        self.alt_button.hide()
        layout.addStretch()
        self.actionsdockwidget.setWidget(self.actionsdockwidgetcontents)

        # "Repository Status" widget
        self.statusdockwidget = create_dock('Status', self)
        self.statusdockwidget.setWidget(StatusWidget(self))

        # "Commit Message Editor" widget
        self.position_label = QtGui.QLabel()
        font = qtutils.default_monospace_font()
        font.setPointSize(int(font.pointSize() * 0.8))
        self.position_label.setFont(font)
        self.commitdockwidget = create_dock('Commit', self)
        titlebar = self.commitdockwidget.titleBarWidget()
        titlebar.add_corner_widget(self.position_label)

        self.commitmsgeditor = CommitMessageEditor(model, self)
        relay_signal(self, self.commitmsgeditor, SIGNAL(signals.amend_mode))
        relay_signal(self, self.commitmsgeditor, SIGNAL(signals.signoff))
        relay_signal(self, self.commitmsgeditor,
                     SIGNAL(signals.load_previous_message))
        self.commitdockwidget.setWidget(self.commitmsgeditor)

        # "Command Output" widget
        logwidget = qtutils.logger()
        logwidget.setFont(diff_font())
        self.logdockwidget = create_dock('Console', self)
        self.logdockwidget.setWidget(logwidget)

        # "Diff Viewer" widget
        self.diffdockwidget = create_dock('Diff', self)
        self.diff_editor = DiffEditor(self.diffdockwidget)
        self.diffdockwidget.setWidget(self.diff_editor)

        # All Actions
        self.menu_unstage_all = add_action(self,
                'Unstage All', emit(self, signals.unstage_all))
        self.menu_unstage_all.setIcon(qtutils.icon('remove.svg'))

        self.menu_unstage_selected = add_action(self,
                'Unstage From Commit', emit(self, signals.unstage_selected))
        self.menu_unstage_selected.setIcon(qtutils.icon('remove.svg'))

        self.menu_show_diffstat = add_action(self,
                'Diffstat', emit(self, signals.diffstat), 'Alt+D')

        self.menu_stage_modified = add_action(self,
                'Stage Changed Files To Commit',
                emit(self, signals.stage_modified), 'Alt+A')
        self.menu_stage_modified.setIcon(qtutils.icon('add.svg'))

        self.menu_stage_untracked = add_action(self,
                'Stage All Untracked', emit(self, signals.stage_untracked), 'Alt+U')
        self.menu_stage_untracked.setIcon(qtutils.icon('add.svg'))

        self.menu_export_patches = add_action(self,
                'Export Patches...', guicmds.export_patches, 'Alt+E')
        self.menu_preferences = add_action(self,
                'Preferences', lambda: preferences(model=prefs_model),
                QtGui.QKeySequence.Preferences, 'Ctrl+O')

        self.menu_rescan = add_action(self,
                'Rescan', emit(self, signals.rescan_and_refresh), 'Ctrl+R')
        self.menu_rescan.setIcon(qtutils.reload_icon())

        self.menu_browse_recent = add_action(self,
                'Recently Modified Files...', browse_recent, 'Shift+Ctrl+E')

        self.menu_cherry_pick = add_action(self,
                'Cherry-Pick...', guicmds.cherry_pick, 'Ctrl+P')

        self.menu_load_commitmsg = add_action(self,
                'Load Commit Message...', guicmds.load_commitmsg)

        self.menu_save_tarball = add_action(self,
                'Save As Tarball/Zip...', self.save_archive)

        self.menu_quit = add_action(self,
                'Quit', self.close, 'Ctrl+Q')
        self.menu_manage_bookmarks = add_action(self,
                'Bookmarks...', manage_bookmarks)
        self.menu_grep = add_action(self,
                'Grep', guicmds.grep)
        self.menu_merge_local = add_action(self,
                'Merge...', merge.local_merge)

        self.menu_merge_abort = add_action(self,
                'Abort Merge...', merge.abort_merge)

        self.menu_fetch = add_action(self,
                'Fetch...', remote.fetch)
        self.menu_push = add_action(self,
                'Push...', remote.push)
        self.menu_pull = add_action(self,
                'Pull...', remote.pull)

        self.menu_open_repo = add_action(self,
                'Open...', guicmds.open_repo)
        self.menu_open_repo.setIcon(qtutils.open_icon())

        self.menu_stash = add_action(self,
                'Stash...', stash.stash, 'Alt+Shift+S')

        self.menu_clone_repo = add_action(self,
                'Clone...', guicmds.clone_repo)
        self.menu_clone_repo.setIcon(qtutils.git_icon())

        self.menu_help_docs = add_action(self,
                'Documentation', resources.show_html_docs,
                QtGui.QKeySequence.HelpContents)

        self.menu_help_shortcuts = add_action(self,
                'Keyboard Shortcuts',
                show_shortcuts,
                QtCore.Qt.Key_Question)

        self.menu_visualize_current = add_action(self,
                'Visualize Current Branch...',
                emit(self, signals.visualize_current))
        self.menu_visualize_all = add_action(self,
                'Visualize All Branches...',
                emit(self, signals.visualize_all))
        self.menu_search_commits = add_action(self,
                'Search...', search)
        self.menu_browse_branch = add_action(self,
                'Browse Current Branch...', guicmds.browse_current)
        self.menu_browse_other_branch = add_action(self,
                'Browse Other Branch...', guicmds.browse_other)
        self.menu_load_commitmsg_template = add_action(self,
                'Get Commit Message Template',
                emit(self, signals.load_commit_template))
        self.menu_help_about = add_action(self,
                'About', launch_about_dialog)

        self.menu_branch_diff = add_action(self,
                'SHA-1...', guicmds.branch_diff)
        self.menu_diff_expression = add_action(self,
                'Expression...', guicmds.diff_expression)
        self.menu_branch_compare = add_action(self,
                'Branches...', compare_branches)

        self.menu_create_tag = add_action(self,
                'Create Tag...', create_tag)

        self.menu_create_branch = add_action(self,
                'Create...', create_new_branch, 'Ctrl+B')

        self.menu_delete_branch = add_action(self,
                'Delete...', guicmds.branch_delete)

        self.menu_checkout_branch = add_action(self,
                'Checkout...', guicmds.checkout_branch, 'Alt+B')
        self.menu_rebase_branch = add_action(self,
                'Rebase...', guicmds.rebase)
        self.menu_branch_review = add_action(self,
                'Review...', guicmds.review_branch)

        self.menu_classic = add_action(self,
                'Cola Classic...', cola_classic)
        self.menu_classic.setIcon(qtutils.git_icon())

        self.menu_dag = add_action(self,
                'DAG...', lambda: git_dag(self.model))
        self.menu_dag.setIcon(qtutils.git_icon())

        # Relayed actions
        status_tree = self.statusdockwidget.widget().tree
        self.addAction(status_tree.up)
        self.addAction(status_tree.down)
        self.addAction(status_tree.process_selection)
        self.addAction(status_tree.launch_difftool)

        # Create the application menu
        self.menubar = QtGui.QMenuBar(self)

        # File Menu
        self.file_menu = create_menu('&File', self.menubar)
        self.file_menu.addAction(self.menu_preferences)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_open_repo)
        self.file_menu.addAction(self.menu_clone_repo)
        self.file_menu.addAction(self.menu_manage_bookmarks)
        self.file_menu.addSeparator()
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
        self.commit_menu = create_menu('Co&mmit', self.menubar)
        self.commit_menu.setTitle(tr('Commit@@verb'))
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
        self.branch_menu = create_menu('B&ranch', self.menubar)
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
        self.actions_menu = create_menu('Act&ions', self.menubar)
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
        self.diff_menu = create_menu('&Diff', self.menubar)
        self.diff_menu.addAction(self.menu_branch_diff)
        self.diff_menu.addAction(self.menu_diff_expression)
        self.diff_menu.addAction(self.menu_branch_compare)
        self.diff_menu.addSeparator()
        self.diff_menu.addAction(self.menu_show_diffstat)
        # Add to menubar
        self.menubar.addAction(self.diff_menu.menuAction())

        # Tools Menu
        self.tools_menu = create_menu('&Tools', self.menubar)
        self.tools_menu.addAction(self.menu_classic)
        self.tools_menu.addAction(self.menu_dag)
        self.tools_menu.addSeparator()
        if self.classic_dockable:
            self.tools_menu.addAction(self.classicdockwidget.toggleViewAction())

        self.setup_dockwidget_tools_menu()
        self.menubar.addAction(self.tools_menu.menuAction())

        # Help Menu
        self.help_menu = create_menu('&Help', self.menubar)
        self.help_menu.addAction(self.menu_help_docs)
        self.help_menu.addAction(self.menu_help_shortcuts)
        self.help_menu.addAction(self.menu_help_about)
        # Add to menubar
        self.menubar.addAction(self.help_menu.menuAction())

        # Set main menu
        self.setMenuBar(self.menubar)

        # Arrange dock widgets
        top = Qt.TopDockWidgetArea
        bottom = Qt.BottomDockWidgetArea

        self.addDockWidget(top, self.commitdockwidget)
        if self.classic_dockable:
            self.addDockWidget(top, self.classicdockwidget)
        self.addDockWidget(top, self.statusdockwidget)
        self.addDockWidget(top, self.actionsdockwidget)
        self.addDockWidget(bottom, self.logdockwidget)
        if self.classic_dockable:
            self.tabifyDockWidget(self.classicdockwidget, self.commitdockwidget)
        self.tabifyDockWidget(self.logdockwidget, self.diffdockwidget)

        # Listen for model notifications
        model.add_message_observer(model.message_mode_changed,
                                   self._mode_changed)

        model.add_message_observer(model.message_updated,
                                   self._update_view)

        prefs_model.add_message_observer(prefs_model.message_config_updated,
                                         self._config_updated)

        # Set a default value
        self.show_cursor_position(1, 0)

        # Add button callbacks
        connect_button(self.rescan_button,
                       emit(self, signals.rescan_and_refresh))
        connect_button(self.alt_button, emit(self, signals.reset_mode))
        connect_button(self.fetch_button, remote.fetch)
        connect_button(self.push_button, remote.push)
        connect_button(self.pull_button, remote.pull)
        connect_button(self.stash_button, stash.stash)

        connect_button(self.stage_button, self.stage)
        connect_button(self.unstage_button, self.unstage)

        self.connect(self.commitmsgeditor, SIGNAL('cursorPosition(int,int)'),
                     self.show_cursor_position)
        self.connect(self, SIGNAL('update'), self._update_callback)
        self.connect(self, SIGNAL('apply_state'), self.apply_state)
        self.connect(self, SIGNAL('install_config_actions'),
                     self._install_config_actions)

        # Install .git-config-defined actions
        self._config_task = None
        self.install_config_actions()

        # Restore saved settings
        self._gui_state_task = None
        self._load_gui_state()

        log(0, version.git_version_str() + '\ncola version ' + version.version())

    # Qt overrides
    def closeEvent(self, event):
        """Save state in the settings manager."""
        qtutils.save_state(self)
        standard.MainWindow.closeEvent(self, event)

    # Accessors
    mode = property(lambda self: self.model.mode)

    def _mode_changed(self, mode):
        """React to mode changes; hide/show the "Exit Diff Mode" button."""
        if mode in (self.model.mode_review,
                    self.model.mode_diff,
                    self.model.mode_diff_expr):
            height = self.stage_button.minimumHeight()
            self.alt_button.setMinimumHeight(height)
            self.alt_button.show()
        else:
            self.alt_button.setMinimumHeight(1)
            self.alt_button.hide()

    def _config_updated(self, source, config, value):
        if config == 'cola.fontdiff':
            font = QtGui.QFont()
            if not font.fromString(value):
                return
            qtutils.logger().setFont(font)
            self.diff_editor.setFont(font)
            self.commitmsgeditor.setFont(font)

        elif config == 'cola.tabwidth':
            # variable-tab-width setting
            self.diff_editor.set_tab_width(value)

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
            menu.addAction(name, emit(self, signals.run_config_action, name))

    def _update_view(self):
        self.emit(SIGNAL('update'))

    def _update_callback(self):
        """Update the title with the current branch and directory name."""
        branch = self.model.currentbranch
        curdir = core.decode(os.getcwd())
        msg = 'Repository: %s\nBranch: %s' % (curdir, branch)
        self.commitdockwidget.setToolTip(msg)

        title = '%s: %s' % (self.model.project, branch)
        if self.mode in (self.model.mode_diff, self.model.mode_diff_expr):
            title += ' *** diff mode***'
        elif self.mode == self.model.mode_review:
            title += ' *** review mode***'
        elif self.mode == self.model.mode_amend:
            title += ' *** amending ***'
        self.setWindowTitle(title)

        self.commitmsgeditor.set_mode(self.mode)

        if not self.model.read_only() and self.mode != self.model.mode_amend:
            # Check if there's a message file in .git/
            merge_msg_path = gitcmds.merge_message_path()
            if merge_msg_path is None:
                return
            merge_msg_hash = utils.checksum(core.decode(merge_msg_path))
            if merge_msg_hash == self.merge_message_hash:
                return
            self.merge_message_hash = merge_msg_hash
            cola.notifier().broadcast(signals.load_commit_message,
                                      core.decode(merge_msg_path))

    def apply_state(self, state):
        """Imports data for save/restore"""
        # 1 is the widget version; change when widgets are added/removed
        standard.MainWindow.apply_state(self, state)
        qtutils.apply_window_state(self, state, 1)

    def export_state(self):
        """Exports data for save/restore"""
        state = standard.MainWindow.export_state(self)
        return qtutils.export_window_state(self, state, self.widget_version)

    def _load_gui_state(self):
        """Restores the gui from the preferences file."""
        self._gui_state_task = self._start_gui_state_loading_thread()

    def _start_gui_state_loading_thread(self):
        """Do expensive file reading and json decoding in the background"""
        class LoadGUIStateTask(QtCore.QRunnable):
            def __init__(self, sender):
                QtCore.QRunnable.__init__(self)
                self._sender = sender
            def run(self):
                state = settings.Settings().get_gui_state(self._sender)
                self._sender.emit(SIGNAL('apply_state'), state)

        task = LoadGUIStateTask(self)
        QtCore.QThreadPool.globalInstance().start(task)
        return task

    def setup_dockwidget_tools_menu(self):
        # Hotkeys for toggling the dock widgets
        dockwidgets = (
            (self.logdockwidget, 'Alt+0'),
            (self.commitdockwidget, 'Alt+1'),
            (self.statusdockwidget, 'Alt+2'),
            (self.diffdockwidget, 'Alt+3'),
            (self.actionsdockwidget, 'Alt+4'),
        )
        for dockwidget, shortcut in dockwidgets:
            # Associate the action with the shortcut
            action = dockwidget.toggleViewAction()
            action.setShortcut(shortcut)
            self.tools_menu.addAction(action)
            def showdock(show, dockwidget=dockwidget):
                if show:
                    dockwidget.raise_()
                    dockwidget.widget().setFocus(True)
                else:
                    self.setFocus(True)
            self.addAction(action)
            connect_action_bool(action, showdock)

            # Create a new shortcut Shift+<shortcut> that gives focus
            action = QtGui.QAction(self)
            action.setShortcut('Shift+' + shortcut)
            def focusdock(dockwidget=dockwidget, showdock=showdock):
                if dockwidget.toggleViewAction().isChecked():
                    showdock(True)
                else:
                    dockwidget.toggleViewAction().trigger()
            self.addAction(action)
            connect_action(action, focusdock)

    def save_archive(self):
        ref = git.rev_parse('HEAD')
        shortref = ref[:7]
        GitArchiveDialog.save(ref, shortref, self)

    def stage(self):
        """Stage selected files, or all files if no selection exists."""
        paths = cola.selection_model().unstaged
        if not paths:
            cola.notifier().broadcast(signals.stage_modified)
        else:
            cola.notifier().broadcast(signals.stage, paths)

    def unstage(self):
        """Unstage selected files, or all files if no selection exists."""
        paths = cola.selection_model().staged
        if not paths:
            cola.notifier().broadcast(signals.unstage_all)
        else:
            cola.notifier().broadcast(signals.unstage, paths)

    def dragEnterEvent(self, event):
        """Accepts drops"""
        standard.MainWindow.dragEnterEvent(self, event)
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
        # Broadcast the patches to apply
        cola.notifier().broadcast(signals.apply_patches, patches)

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
