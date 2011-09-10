from PyQt4 import QtGui
from PyQt4 import QtCore
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
from cola.qtutils import tr
from cola.qtutils import SLOT
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
from cola.views.standard import create_standard_widget


class DiffTextEdit(QtGui.QTextEdit):
    def __init__(self, parent):
        QtGui.QTextEdit.__init__(self, parent)
        self.setMinimumSize(QtCore.QSize(1, 1))
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.setAcceptRichText(False)
        self.setCursorWidth(2)
        self.setTextInteractionFlags(Qt.TextSelectableByKeyboard |
                                     Qt.TextSelectableByMouse)


MainWindowBase = create_standard_widget(QtGui.QMainWindow)
class MainWindow(MainWindowBase):
    def __init__(self, model, parent=None, add_action=qtutils.add_action, SLOT=SLOT):
        MainWindowBase.__init__(self, parent)
        # Default size; this is thrown out when save/restore is used
        self.resize(987, 610)
        self.model = cola.model()

        # Dockwidget options
        qtcompat.set_common_dock_options(self)

        self.classic_dockable = gitcfg.instance().get('cola.classicdockable')

        if self.classic_dockable:
            self.classicdockwidget = self.create_dock('Cola Classic')
            self.classicwidget = classic.widget(parent=self)
            self.classicdockwidget.setWidget(self.classicwidget)

        # "Actions" widget
        self.actiondockwidget = self.create_dock('Actions')
        self.actiondockwidgetcontents = qt.QFlowLayoutWidget(parent=self)
        layout = self.actiondockwidgetcontents.layout()
        self.rescan_button = qt.create_button('Rescan', layout)
        self.stage_button = qt.create_button('Stage', layout)
        self.unstage_button = qt.create_button('Unstage', layout)
        self.fetch_button = qt.create_button('Fetch...', layout)
        self.push_button = qt.create_button('Push...', layout)
        self.pull_button = qt.create_button('Pull...', layout)
        self.stash_button = qt.create_button('Stash...', layout)
        self.alt_button = qt.create_button('Exit Diff Mode', layout)
        self.alt_button.hide()
        layout.addStretch()
        self.actiondockwidget.setWidget(self.actiondockwidgetcontents)

        # "Repository Status" widget
        self.statusdockwidget = self.create_dock('Repository Status')
        self.statusdockwidget.setWidget(status.StatusWidget(self))

        # "Commit Message Editor" widget
        self.commitdockwidget = self.create_dock('Commit Message Editor')
        self.commitdockwidgetcontents = QtGui.QWidget()

        self.commitdockwidgetlayout = QtGui.QVBoxLayout(self.commitdockwidgetcontents)
        self.commitdockwidgetlayout.setMargin(0)
        self.commitdockwidgetlayout.setSpacing(0)

        self.commitmsg = QtGui.QTextEdit(self.commitdockwidgetcontents)
        self.commitmsg.setMinimumSize(QtCore.QSize(1, 1))
        policy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,
                                   QtGui.QSizePolicy.Minimum)
        self.commitmsg.setSizePolicy(policy)
        self.commitmsg.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.commitmsg.setAcceptRichText(False)

        self.commit_ctrls_layt = QtGui.QHBoxLayout()
        self.commit_ctrls_layt.setSpacing(4)
        self.commit_ctrls_layt.setMargin(4)

        # Sign off and commit buttons
        self.signoff_button = qt.create_toolbutton(self,
                                                   text='Sign Off',
                                                   tooltip='Sign off on this commit',
                                                   icon=qtutils.apply_icon())

        self.commit_button = qt.create_toolbutton(self,
                                                  text='Commit@@verb',
                                                  tooltip='Commit staged changes',
                                                  icon=qtutils.save_icon())
        # Position display
        self.position_label = QtGui.QLabel(self.actiondockwidgetcontents)
        self.position_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)

        # Amend checkbox
        self.amend_checkbox = QtGui.QCheckBox(self.commitdockwidgetcontents)
        self.amend_checkbox.setText(tr('Amend Last Commit'))

        self.commit_ctrls_layt.addWidget(self.signoff_button)
        self.commit_ctrls_layt.addWidget(self.commit_button)
        self.commit_ctrls_layt.addWidget(self.position_label)
        self.commit_ctrls_layt.addStretch()
        self.commit_ctrls_layt.addWidget(self.amend_checkbox)

        self.commitdockwidgetlayout.addWidget(self.commitmsg)
        self.commitdockwidgetlayout.addLayout(self.commit_ctrls_layt)

        self.commitdockwidget.setWidget(self.commitdockwidgetcontents)

        # "Command Output" widget
        logwidget = qtutils.logger()
        self.logdockwidget = self.create_dock('Command Output')
        self.logdockwidget.setWidget(logwidget)

        # "Diff Viewer" widget
        self.diffdockwidget = self.create_dock('Diff Viewer')
        self.diffdockwidgetcontents = QtGui.QWidget()
        self.diffdockwidgetlayout = QtGui.QVBoxLayout(self.diffdockwidgetcontents)
        self.diffdockwidgetlayout.setMargin(0)

        self.display_text = DiffTextEdit(self.diffdockwidgetcontents)
        self.diffdockwidgetlayout.addWidget(self.display_text)
        self.diffdockwidget.setWidget(self.diffdockwidgetcontents)

        # All Actions
        self.menu_unstage_selected = add_action(self,
                'Unstage From Commit', SLOT(signals.unstage_selected))
        self.menu_show_diffstat = add_action(self,
                'Diffstat', SLOT(signals.diffstat), 'Ctrl+D')
        self.menu_stage_modified = add_action(self,
                'Stage Changed Files To Commit',
                SLOT(signals.stage_modified), 'Alt+A')
        self.menu_stage_untracked = add_action(self,
                'Stage All Untracked', SLOT(signals.stage_untracked), 'Alt+U')
        self.menu_export_patches = add_action(self,
                'Export Patches...', guicmds.export_patches, 'Ctrl+E')
        self.menu_preferences = add_action(self,
                'Preferences', update_options,
                QtGui.QKeySequence.Preferences, 'Ctrl+O')
        self.menu_undo = add_action(self,
                'Undo', self.commitmsg.undo, QtGui.QKeySequence.Undo)
        self.menu_redo = add_action(self,
                'Redo', self.commitmsg.redo, QtGui.QKeySequence.Redo)
        self.menu_rescan = add_action(self,
                'Rescan', SLOT(signals.rescan),
                'Ctrl+R', QtGui.QKeySequence.Refresh)
        self.menu_cherry_pick = add_action(self,
                'Cherry-Pick...', guicmds.cherry_pick, 'Ctrl+P')
        self.menu_unstage_all = add_action(self,
                'Unstage All', SLOT(signals.unstage_all))
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
                'Visualize Current Branch...', SLOT(signals.visualize_current))
        self.menu_visualize_all = add_action(self,
                'Visualize All Branches...', SLOT(signals.visualize_all))
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
                SLOT(signals.load_commit_template))
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

        # Broadcast the amend mode
        self.connect(self.amend_checkbox, SIGNAL('toggled(bool)'),
                     SLOT(signals.amend_mode))

        # Add button callbacks
        self._relay_button(self.alt_button, signals.reset_mode)
        self._relay_button(self.rescan_button, signals.rescan)

        self._connect_button(self.signoff_button, self.signoff)
        self._connect_button(self.stage_button, self.stage)
        self._connect_button(self.unstage_button, self.unstage)
        self._connect_button(self.commit_button, self.commit)
        self._connect_button(self.fetch_button, guicmds.fetch_slot(self))
        self._connect_button(self.push_button, guicmds.push_slot(self))
        self._connect_button(self.pull_button, guicmds.pull_slot(self))
        self._connect_button(self.stash_button, lambda: stash.stash(parent=self))

        # Listen for text and amend messages
        cola.notifier().connect(signals.diff_text, self.set_display)
        cola.notifier().connect(signals.mode, self._mode_changed)
        cola.notifier().connect(signals.amend, self.amend_checkbox.setChecked)

        # Create the application menu
        self.menubar = QtGui.QMenuBar(self)

        # File Menu
        self.file_menu = self.create_menu('&File', self.menubar)
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
        self.commit_menu = self.create_menu('Co&mmit', self.menubar)
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
        self.branch_menu = self.create_menu('B&ranch', self.menubar)
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
        self.actions_menu = self.create_menu('Act&ions', self.menubar)
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
        self.diff_menu = self.create_menu('&Diff', self.menubar)
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
        self.tools_menu = self.create_menu('&Tools', self.menubar)
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
        self.help_menu = self.create_menu('&Help', self.menubar)
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

    def create_dock(self, title):
        """Create a dock widget and set it up accordingly."""
        dock = QtGui.QDockWidget(self)
        dock.setWindowTitle(tr(title))
        dock.setObjectName(title)
        return dock

    def create_menu(self, title, parent):
        """Create a menu and set its title."""
        qmenu = QtGui.QMenu(parent)
        qmenu.setTitle(tr(title))
        return qmenu

    def closeEvent(self, event):
        """Save state in the settings manager."""
        if cola.model().remember_gui_settings():
            settings.SettingsManager.save_gui_state(self)
        self.close()

    def _relay_button(self, button, signal):
        callback = SLOT(signal)
        self._connect_button(button, callback)

    def _connect_button(self, button, callback):
        self.connect(button, SIGNAL('clicked()'), callback)

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

    def set_display(self, text):
        """Set the diff text display."""
        scrollbar = self.display_text.verticalScrollBar()
        scrollvalue = scrollbar.value()
        if text is not None:
            self.display_text.setPlainText(text)
            scrollbar.setValue(scrollvalue)
