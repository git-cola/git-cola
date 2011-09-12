from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

import cola
from cola import guicmds
from cola import settings
from cola import signals
from cola import gitcfg
from cola import qtutils
from cola import qtcompat
from cola import qt
from cola import resources
from cola.qt import create_button
from cola.qt import create_dock
from cola.qt import create_menu
from cola.qtutils import add_action
from cola.qtutils import connect_button
from cola.qtutils import emit
from cola.qtutils import relay_signal
from cola.qtutils import SLOT
from cola.qtutils import tr
from cola.controllers import classic
from cola.controllers import compare
from cola.controllers import createtag
from cola.controllers import merge
from cola.controllers import stash
from cola.controllers import search
from cola.controllers.bookmark import manage_bookmarks
from cola.controllers.bookmark import save_bookmark
from cola.controllers.createbranch import create_new_branch
from cola.controllers.options import update_options
from cola.views import about
from cola.views import dag
from cola.views import status
from cola.views.diff import DiffTextEdit
from cola.views.commitmsg import CommitMessageEditor
from cola.views.standard import create_standard_widget


MainWindowBase = create_standard_widget(QtGui.QMainWindow)
class MainWindow(MainWindowBase):
    def __init__(self, model, parent=None,
                 add_action=add_action,
                 connect_button=connect_button,
                 create_button=create_button,
                 create_dock=create_dock,
                 create_menu=create_menu,
                 emit=emit,
                 relay_signal=relay_signal,
                 SLOT=SLOT,
                 tr=tr):
        MainWindowBase.__init__(self, parent)
        # Default size; this is thrown out when save/restore is used
        self.resize(987, 610)
        self.model = model
        self.setAcceptDrops(True)

        # Dockwidget options
        qtcompat.set_common_dock_options(self)

        self.classic_dockable = gitcfg.instance().get('cola.classicdockable')

        if self.classic_dockable:
            self.classicdockwidget = create_dock('Cola Classic', self)
            self.classicwidget = classic.widget(parent=self)
            self.classicdockwidget.setWidget(self.classicwidget)

        # "Actions" widget
        self.actiondockwidget = create_dock('Actions', self)
        self.actiondockwidgetcontents = qt.QFlowLayoutWidget(parent=self)
        layout = self.actiondockwidgetcontents.layout()
        self.rescan_button = create_button('Rescan', layout)
        self.stage_button = create_button('Stage', layout)
        self.unstage_button = create_button('Unstage', layout)
        self.fetch_button = create_button('Fetch...', layout)
        self.push_button = create_button('Push...', layout)
        self.pull_button = create_button('Pull...', layout)
        self.stash_button = create_button('Stash...', layout)
        self.alt_button = create_button('Exit Diff Mode', layout)
        self.alt_button.hide()
        layout.addStretch()
        self.actiondockwidget.setWidget(self.actiondockwidgetcontents)

        # "Repository Status" widget
        self.statusdockwidget = create_dock('Repository Status', self)
        self.statusdockwidget.setWidget(status.StatusWidget(self))

        # "Commit Message Editor" widget
        self.commitdockwidget = create_dock('Commit Message Editor', self)
        self.commitmsgeditor = CommitMessageEditor(model, self)
        relay_signal(self, self.commitmsgeditor, SIGNAL(signals.amend_mode))
        relay_signal(self, self.commitmsgeditor, SIGNAL(signals.signoff))
        self.commitdockwidget.setWidget(self.commitmsgeditor)

        # "Command Output" widget
        logwidget = qtutils.logger()
        self.logdockwidget = create_dock('Command Output', self)
        self.logdockwidget.setWidget(logwidget)

        # "Diff Viewer" widget
        self.diffdockwidget = create_dock('Diff Viewer', self)
        self.diff_viewer = DiffTextEdit(self.diffdockwidget)
        self.diffdockwidget.setWidget(self.diff_viewer)

        # All Actions
        self.menu_unstage_selected = add_action(self,
                'Unstage From Commit', emit(self, signals.unstage_selected))
        self.menu_show_diffstat = add_action(self,
                'Diffstat', emit(self, signals.diffstat), 'Ctrl+D')
        self.menu_stage_modified = add_action(self,
                'Stage Changed Files To Commit',
                emit(self, signals.stage_modified), 'Alt+A')
        self.menu_stage_untracked = add_action(self,
                'Stage All Untracked', emit(self, signals.stage_untracked), 'Alt+U')
        self.menu_export_patches = add_action(self,
                'Export Patches...', guicmds.export_patches, 'Ctrl+E')
        self.menu_preferences = add_action(self,
                'Preferences', update_options,
                QtGui.QKeySequence.Preferences, 'Ctrl+O')
        self.menu_rescan = add_action(self,
                'Rescan', emit(self, signals.rescan),
                'Ctrl+R', QtGui.QKeySequence.Refresh)
        self.menu_cherry_pick = add_action(self,
                'Cherry-Pick...', guicmds.cherry_pick, 'Ctrl+P')
        self.menu_unstage_all = add_action(self,
                'Unstage All', emit(self, signals.unstage_all))
        self.menu_load_commitmsg = add_action(self,
                'Load Commit Message...', guicmds.load_commitmsg_slot(self))
        self.menu_quit = add_action(self,
                'Quit', self.close, 'Ctrl+Q')
        self.menu_manage_bookmarks = add_action(self,
                'Bookmarks...', manage_bookmarks)
        self.menu_save_bookmark = add_action(self,
                'Bookmark Current...', save_bookmark)
        self.menu_grep = add_action(self,
                'Grep', guicmds.grep)
        self.menu_merge_local = add_action(self,
                'Merge...', merge.local_merge)
        self.menu_merge_abort = add_action(self,
                'Abort Merge...', merge.abort_merge)
        self.menu_fetch = add_action(self,
                'Fetch...', guicmds.fetch_slot(self))
        self.menu_push = add_action(self,
                'Push...', guicmds.push_slot(self))
        self.menu_pull = add_action(self,
                'Pull...', guicmds.pull_slot(self))
        self.menu_open_repo = add_action(self,
                'Open...', guicmds.open_repo_slot(self))
        self.menu_stash = add_action(self,
                'Stash...', lambda: stash.stash(parent=self), 'Alt+Shift+S')
        self.menu_diff_branch = add_action(self,
                'Apply Changes From Branch...', guicmds.diff_branch)
        self.menu_branch_compare = add_action(self,
                'Branches...', compare.branch_compare)
        self.menu_clone_repo = add_action(self,
                'Clone...', guicmds.clone_repo)
        self.menu_help_docs = add_action(self,
                'Documentation',
                lambda: self.model.git.web__browse(resources.html_docs()),
                QtGui.QKeySequence.HelpContents)
        self.menu_commit_compare = add_action(self,
                'Commits...', compare.compare)
        self.menu_commit_compare_file = add_action(self,
                'Commits Touching File...', compare.compare_file)
        self.menu_visualize_current = add_action(self,
                'Visualize Current Branch...',
                emit(self, signals.visualize_current))
        self.menu_visualize_all = add_action(self,
                'Visualize All Branches...',
                emit(self, signals.visualize_all))
        self.menu_browse_commits = add_action(self,
                'Browse...', guicmds.browse_commits)
        self.menu_search_commits = add_action(self,
                'Search...', search.search)
        self.menu_browse_branch = add_action(self,
                'Browse Current Branch...', guicmds.browse_current)
        self.menu_browse_other_branch = add_action(self,
                'Browse Other Branch...', guicmds.browse_other)
        self.menu_load_commitmsg_template = add_action(self,
                'Get Commit Message Template',
                emit(self, signals.load_commit_template))
        self.menu_help_about = add_action(self,
                'About', about.launch_about_dialog)
        self.menu_branch_diff = add_action(self,
                'SHA-1...', guicmds.branch_diff)
        self.menu_diff_expression = add_action(self,
                'Expression...', guicmds.diff_expression)
        self.menu_create_tag = add_action(self,
                'Create Tag...', createtag.create_tag)
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
                'Cola Classic...', classic.cola_classic)
        self.menu_dag = add_action(self,
                'DAG...', lambda: dag.git_dag(self.model, self))

        # Create the application menu
        self.menubar = QtGui.QMenuBar(self)

        # File Menu
        self.file_menu = create_menu('&File', self.menubar)
        self.file_menu.addAction(self.menu_preferences)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_open_repo)
        self.file_menu.addAction(self.menu_clone_repo)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_rescan)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_manage_bookmarks)
        self.file_menu.addAction(self.menu_save_bookmark)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.menu_load_commitmsg)
        self.file_menu.addAction(self.menu_load_commitmsg_template)
        self.file_menu.addSeparator()
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
        self.commit_menu.addAction(self.menu_browse_commits)
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
        self.branch_menu.addSeparator()
        self.branch_menu.addAction(self.menu_diff_branch)
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
        self.diff_menu.addSeparator()
        self.diff_menu.addAction(self.menu_branch_compare)
        self.diff_menu.addAction(self.menu_commit_compare)
        self.diff_menu.addAction(self.menu_commit_compare_file)
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
        self.tools_menu.addAction(self.diffdockwidget.toggleViewAction())
        self.tools_menu.addAction(self.actiondockwidget.toggleViewAction())
        self.tools_menu.addAction(self.commitdockwidget.toggleViewAction())
        self.tools_menu.addAction(self.statusdockwidget.toggleViewAction())
        self.tools_menu.addAction(self.logdockwidget.toggleViewAction())
        self.menubar.addAction(self.tools_menu.menuAction())

        # Help Menu
        self.help_menu = create_menu('&Help', self.menubar)
        self.help_menu.addAction(self.menu_help_docs)
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
        self.addDockWidget(top, self.actiondockwidget)
        self.addDockWidget(bottom, self.logdockwidget)
        if self.classic_dockable:
            self.tabifyDockWidget(self.classicdockwidget, self.commitdockwidget)
        self.tabifyDockWidget(self.logdockwidget, self.diffdockwidget)

        # Add button callbacks
        connect_button(self.rescan_button, emit(self, signals.rescan))
        connect_button(self.alt_button, emit(self, signals.reset_mode))
        connect_button(self.fetch_button, guicmds.fetch_slot(self))
        connect_button(self.push_button, guicmds.push_slot(self))
        connect_button(self.pull_button, guicmds.pull_slot(self))
        connect_button(self.stash_button, lambda: stash.stash(parent=self))

        # Listen for text and amend messages
        model.add_message_observer(model.message_mode_changed,
                                   self._mode_changed)


    def closeEvent(self, event):
        """Save state in the settings manager."""
        if cola.model().remember_gui_settings():
            settings.SettingsManager.save_gui_state(self)
        MainWindowBase.closeEvent(self, event)

    def _mode_changed(self, mode):
        """React to mode changes; hide/show the "Exit Diff Mode" button."""
        if mode in (self.model.mode_review,
                    self.model.mode_diff,
                    self.model.mode_diff_expr):
            self.alt_button.setMinimumHeight(40)
            self.alt_button.show()
        else:
            self.alt_button.setMinimumHeight(1)
            self.alt_button.hide()
