from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt

import cola
from cola import settings
from cola import gitcfg
from cola import qtutils
from cola import qtcompat
from cola import qt
from cola.views import log
from cola.qtutils import tr
from cola.views import status
from cola.views.standard import create_standard_widget
from cola.controllers import classic


MainWindowBase = create_standard_widget(QtGui.QMainWindow)
class MainWindow(MainWindowBase):
    def __init__(self, parent=None):
        MainWindowBase.__init__(self, parent)
        # Default size; this is thrown out when save/restore is used
        self.resize(987, 610)

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
        self.statusdockwidget.setWidget(status.widget())

        # "Commit Message Editor" widget
        self.commitdockwidget = self.create_dock('Commit Message Editor')
        self.commitdockwidgetcontents = QtGui.QWidget()

        self.commitdockwidgetlayout = QtGui.QVBoxLayout(self.commitdockwidgetcontents)
        self.commitdockwidgetlayout.setMargin(4)

        self.vboxlayout = QtGui.QVBoxLayout()
        self.vboxlayout.setSpacing(0)

        self.commitmsg = QtGui.QTextEdit(self.commitdockwidgetcontents)
        self.commitmsg.setMinimumSize(QtCore.QSize(1, 1))
        policy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,
                                   QtGui.QSizePolicy.Minimum)
        self.commitmsg.setSizePolicy(policy)
        self.commitmsg.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.commitmsg.setAcceptRichText(False)

        self.hboxlayout = QtGui.QHBoxLayout()
        self.hboxlayout.setSpacing(3)
        self.hboxlayout.setContentsMargins(2, 6, 2, 0)

        # Sign off and commit buttons
        self.signoff_button = qt.create_button('Sign Off')
        self.commit_button = qt.create_button('Commit@@verb')

        # Position display
        self.position_label = QtGui.QLabel(self.actiondockwidgetcontents)
        self.position_label.setAlignment(Qt.AlignLeft)

        # Amend checkbox
        self.amend_checkbox = QtGui.QCheckBox(self.commitdockwidgetcontents)
        self.amend_checkbox.setText(tr('Amend Last Commit'))

        self.hboxlayout.addWidget(self.signoff_button)
        self.hboxlayout.addWidget(self.commit_button)
        self.hboxlayout.addWidget(self.position_label)
        self.hboxlayout.addStretch()
        self.hboxlayout.addWidget(self.amend_checkbox)

        self.vboxlayout.addWidget(self.commitmsg)
        self.vboxlayout.addLayout(self.hboxlayout)
        self.commitdockwidgetlayout.addLayout(self.vboxlayout)
        self.commitdockwidget.setWidget(self.commitdockwidgetcontents)

        # "Command Output" widget
        logwidget = qtutils.logger()
        self.logdockwidget = self.create_dock('Command Output')
        self.logdockwidget.setWidget(logwidget)

        # "Diff Viewer" widget
        self.diffdockwidget = self.create_dock('Diff Viewer')
        self.diffdockwidgetcontents = QtGui.QWidget()
        self.diffdockwidgetlayout = QtGui.QVBoxLayout(self.diffdockwidgetcontents)
        self.diffdockwidgetlayout.setMargin(3)

        self.display_text = QtGui.QTextEdit(self.diffdockwidgetcontents)
        self.display_text.setMinimumSize(QtCore.QSize(1, 1))
        self.display_text.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.display_text.setReadOnly(True)
        self.display_text.setAcceptRichText(False)
        self.display_text.setCursorWidth(2)
        self.display_text.setTextInteractionFlags(Qt.LinksAccessibleByKeyboard |
                                                  Qt.LinksAccessibleByMouse |
                                                  Qt.TextBrowserInteraction |
                                                  Qt.TextSelectableByKeyboard |
                                                  Qt.TextSelectableByMouse)

        self.diffdockwidgetlayout.addWidget(self.display_text)
        self.diffdockwidget.setWidget(self.diffdockwidgetcontents)

        # All Actions
        self.menu_unstage_selected = self.create_action('Unstage From Commit')
        self.menu_show_diffstat = self.create_action('Diffstat')
        self.menu_stage_modified =\
                self.create_action('Stage Changed Files To Commit')
        self.menu_stage_untracked = self.create_action('Stage All Untracked')
        self.menu_export_patches = self.create_action('Export Patches...')
        self.menu_cut = self.create_action('Cut')
        self.menu_copy = self.create_action('Copy', local=True)
        self.menu_paste = self.create_action('Paste')
        self.menu_select_all = self.create_action('Select All')
        self.menu_options = self.create_action('Preferences')
        self.menu_delete = self.create_action('Delete')
        self.menu_undo = self.create_action('Undo')
        self.menu_redo = self.create_action('Redo')
        self.menu_rescan = self.create_action('Rescan')
        self.menu_cherry_pick = self.create_action('Cherry-Pick...')
        self.menu_unstage_all = self.create_action('Unstage All')
        self.menu_load_commitmsg = self.create_action('Load Commit Message...')
        self.menu_quit = self.create_action('Quit')
        self.menu_search_revision = self.create_action('Revision ID...')
        self.menu_search_path =\
                self.create_action('Commits Touching Path(s)...')
        self.menu_search_revision_range =\
                self.create_action('Revision Range...')
        self.menu_search_date_range = self.create_action('Latest Commits...')
        self.menu_search_message = self.create_action('Commit Messages...')
        self.menu_search_diff =\
                self.create_action('Content Introduced in Commit...')
        self.menu_search_author = self.create_action('Commits By Author...')
        self.menu_search_committer =\
                self.create_action('Commits By Committer...')
        self.menu_manage_bookmarks = self.create_action('Bookmarks...')
        self.menu_save_bookmark = self.create_action('Bookmark Current...')
        self.menu_search_grep = self.create_action('Grep')
        self.menu_merge_local = self.create_action('Merge...')
        self.menu_merge_abort = self.create_action('Abort Merge...')
        self.menu_fetch = self.create_action('Fetch...')
        self.menu_push = self.create_action('Push...')
        self.menu_pull = self.create_action('Pull...')
        self.menu_open_repo = self.create_action('Open...')
        self.menu_stash = self.create_action('Stash...')
        self.menu_diff_branch =\
                self.create_action('Apply Changes From Branch...')
        self.menu_branch_compare = self.create_action('Branches...')
        self.menu_clone_repo = self.create_action('Clone...')
        self.menu_help_docs = self.create_action('Documentation')
        self.menu_commit_compare = self.create_action('Commits...')
        self.menu_visualize_current =\
                self.create_action('Visualize Current Branch...')
        self.menu_visualize_all =\
                self.create_action('Visualize All Branches...')
        self.menu_browse_commits = self.create_action('Browse Commits...')
        self.menu_browse_branch =\
                self.create_action('Browse Current Branch...')
        self.menu_browse_other_branch =\
                self.create_action('Browse Other Branch...')
        self.menu_load_commitmsg_template =\
                self.create_action('Get Commit Message Template')
        self.menu_commit_compare_file =\
                self.create_action('Commits Touching File...')
        self.menu_help_about = self.create_action('About')
        self.menu_branch_diff = self.create_action('SHA-1...')
        self.menu_diff_expression = self.create_action('Expression...')
        self.menu_create_tag = self.create_action('Create Tag...')
        self.menu_create_branch = self.create_action('Create...')
        self.menu_delete_branch = self.create_action('Delete...')
        self.menu_checkout_branch = self.create_action('Checkout...')
        self.menu_rebase_branch = self.create_action('Rebase...')
        self.menu_branch_review = self.create_action('Review...')
        self.menu_classic = self.create_action('Cola Classic...')
        self.menu_dag = self.create_action('DAG...')

        # Create the application menu
        self.menubar = QtGui.QMenuBar(self)

        # File Menu
        self.file_menu = self.create_menu('&File', self.menubar)
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

        # Edit Menu
        self.edit_menu = self.create_menu('&Edit', self.menubar)
        self.edit_menu.addAction(self.menu_undo)
        self.edit_menu.addAction(self.menu_redo)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.menu_cut)
        self.edit_menu.addAction(self.menu_copy)
        self.edit_menu.addAction(self.menu_paste)
        self.edit_menu.addAction(self.menu_delete)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.menu_select_all)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.menu_options)
        # Add to menubar
        self.menubar.addAction(self.edit_menu.menuAction())

        # Commit Menu
        self.commit_menu = self.create_menu('Co&mmit', self.menubar)
        self.commit_menu.addAction(self.menu_stage_modified)
        self.commit_menu.addAction(self.menu_stage_untracked)
        self.commit_menu.addSeparator()
        self.commit_menu.addAction(self.menu_unstage_all)
        self.commit_menu.addAction(self.menu_unstage_selected)
        self.commit_menu.addSeparator()
        self.commit_menu.addAction(self.menu_browse_commits)
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

        # Search Menu
        self.search_menu = self.create_menu('&Search', self.menubar)
        self.search_menu.addAction(self.menu_search_date_range)
        self.search_menu.addAction(self.menu_search_grep)
        self.search_menu.addSeparator()
        # Search / More Menu
        self.menu_search_more = self.create_menu('More...', self.search_menu)
        self.menu_search_more.addAction(self.menu_search_author)
        self.menu_search_more.addAction(self.menu_search_path)
        self.menu_search_more.addAction(self.menu_search_message)
        self.menu_search_more.addSeparator()
        self.menu_search_more.addAction(self.menu_search_revision_range)
        self.menu_search_more.addAction(self.menu_search_revision)
        self.menu_search_more.addSeparator()
        self.menu_search_more.addAction(self.menu_search_diff)
        self.search_menu.addAction(self.menu_search_more.menuAction())
        # Add to menubar
        self.menubar.addAction(self.search_menu.menuAction())

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

        # Shortcuts
        self.menu_show_diffstat.setShortcut(tr('Ctrl+D'))
        self.menu_stage_modified.setShortcut(tr('Alt+A'))
        self.menu_stage_untracked.setShortcut(tr('Alt+U'))
        self.menu_export_patches.setShortcut(tr('Ctrl+E'))
        self.menu_cut.setShortcut(QtGui.QKeySequence.Cut)
        self.menu_copy.setShortcut(QtGui.QKeySequence.Copy)
        self.menu_paste.setShortcut(QtGui.QKeySequence.Paste)
        self.menu_select_all.setShortcut(QtGui.QKeySequence.SelectAll)
        self.menu_options.setShortcut(tr('Ctrl+O'))
        self.menu_delete.setShortcut(tr('Del'))
        self.menu_undo.setShortcut(tr('Ctrl+Z'))
        self.menu_redo.setShortcut(tr('Ctrl+Shift+Z'))
        self.menu_rescan.setShortcut(tr('Ctrl+R'))
        self.menu_cherry_pick.setShortcut(tr('Ctrl+P'))
        self.menu_quit.setShortcut(tr('Ctrl+Q'))
        self.menu_create_branch.setShortcut(tr('Ctrl+B'))
        self.menu_checkout_branch.setShortcut(tr('Alt+B'))
        self.menu_stash.setShortcut(tr('Alt+Shift+S'))
        self.menu_help_docs.setShortcut(tr('F1'))

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

    def create_action(self, title, local=False):
        """Create an action and set its title."""
        action = QtGui.QAction(self)
        action.setText(tr(title))
        if local and hasattr(Qt, 'WidgetWithChildrenShortcut'):
            action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        return action

    def closeEvent(self, event):
        """Save state in the settings manager."""
        if cola.model().remember_gui_settings():
            settings.SettingsManager.save_gui_state(self)
        self.close()
