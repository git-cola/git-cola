"""Provides the git-cola startup dialog

The startup dialog is presented when no repositories can be
found at startup.

"""
from __future__ import division, absolute_import, unicode_literals

from qtpy.QtCore import Qt
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

from ..i18n import N_
from .. import core
from .. import display
from .. import guicmds
from .. import icons
from .. import qtutils
from .. import version
from . import clone
from . import defs
from . import standard


class StartupDialog(standard.Dialog):
    """Provides a GUI to Open or Clone a git repository."""

    def __init__(self, context, parent=None):
        standard.Dialog.__init__(self, parent)
        self.context = context
        self.setWindowTitle(N_('git-cola'))

        # Top-most large icon
        logo_pixmap = icons.cola().pixmap(defs.huge_icon, defs.huge_icon)

        self.logo_label = QtWidgets.QLabel()
        self.logo_label.setPixmap(logo_pixmap)
        self.logo_label.setAlignment(Qt.AlignCenter)

        self.logo_text_label = qtutils.label(text=version.cola_version())
        self.logo_text_label.setAlignment(Qt.AlignCenter)

        self.repodir = None
        if context.runtask:
            self.runtask = context.runtask
        else:
            self.runtask = context.runtask = qtutils.RunTask(parent=self)

        self.new_button = qtutils.create_button(text=N_('New...'), icon=icons.new())
        self.open_button = qtutils.create_button(
            text=N_('Open...'), icon=icons.folder()
        )
        self.clone_button = qtutils.create_button(
            text=N_('Clone...'), icon=icons.cola()
        )
        self.close_button = qtutils.close_button()

        self.bookmarks_model = QtGui.QStandardItemModel()

        item = QtGui.QStandardItem(N_('Open...'))
        item.setEditable(False)
        item.setIcon(icons.open_directory())
        self.bookmarks_model.appendRow(item)

        # The tab bar allows choosing between Folder and List mode
        self.tab_bar = QtWidgets.QTabBar()
        self.tab_bar.setMovable(False)
        self.tab_bar.addTab(icons.directory(), N_('Folder'))
        self.tab_bar.addTab(icons.file_text(), N_('List'))

        # Bookmarks/"Favorites" and Recent are lists of {name,path: str}
        settings = context.settings
        bookmarks = settings.bookmarks
        recent = settings.recent
        all_repos = bookmarks + recent

        directory_icon = icons.directory()
        user_role = Qt.UserRole
        paths = set([repo['path'] for repo in all_repos])
        short_paths = display.shorten_paths(paths)

        added = set()
        for repo in all_repos:
            path = repo['path']
            if path in added:
                continue
            added.add(path)

            name = repo['name']
            item = QtGui.QStandardItem(short_paths.get(path, name))
            item.setEditable(False)
            item.setData(path, user_role)
            item.setIcon(directory_icon)
            item.setToolTip(path)
            self.bookmarks_model.appendRow(item)

        selection_mode = QtWidgets.QAbstractItemView.SingleSelection
        self.bookmarks = bookmarks = QtWidgets.QListView()
        bookmarks.setSelectionMode(selection_mode)
        bookmarks.setModel(self.bookmarks_model)
        bookmarks.setViewMode(QtWidgets.QListView.IconMode)
        bookmarks.setResizeMode(QtWidgets.QListView.Adjust)
        bookmarks.setGridSize(make_size(defs.large_icon))
        bookmarks.setIconSize(make_size(defs.medium_icon))
        bookmarks.setDragEnabled(False)
        bookmarks.setWordWrap(True)

        self.tab_layout = qtutils.vbox(
            defs.no_margin,
            defs.no_spacing,
            self.tab_bar,
            self.bookmarks
        )

        self.logo_layout = qtutils.vbox(
            defs.no_margin,
            defs.spacing,
            self.logo_label,
            self.logo_text_label,
            defs.button_spacing,
            qtutils.STRETCH,
        )

        self.button_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.open_button,
            self.clone_button,
            self.new_button,
            qtutils.STRETCH,
            self.close_button,
        )

        self.main_layout = qtutils.grid(defs.margin, defs.spacing)
        self.main_layout.addItem(self.logo_layout, 1, 1)
        self.main_layout.addItem(self.tab_layout, 1, 2)
        self.main_layout.addItem(self.button_layout, 2, 1, columnSpan=2)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.open_button, self.open_repo)
        qtutils.connect_button(self.clone_button, self.clone_repo)
        qtutils.connect_button(self.new_button, self.new_repo)
        qtutils.connect_button(self.close_button, self.reject)

        # pylint: disable=no-member
        self.tab_bar.currentChanged.connect(self.tab_changed)
        self.bookmarks.activated.connect(self.open_bookmark)

        self.init_state(settings, self.resize_widget)
        self.setFocusProxy(self.bookmarks)
        self.bookmarks.setFocus()

        # Update the list mode
        list_mode = context.cfg.get('cola.startupmode', default='folder')
        self.list_mode = list_mode
        if list_mode == 'list':
            self.tab_bar.setCurrentIndex(1)

    def tab_changed(self, idx):
        bookmarks = self.bookmarks
        if idx == 0:
            bookmarks.setViewMode(QtWidgets.QListView.IconMode)
            bookmarks.setIconSize(make_size(defs.medium_icon))
            bookmarks.setGridSize(make_size(defs.large_icon))
            list_mode = 'folder'
        else:
            bookmarks.setViewMode(QtWidgets.QListView.ListMode)
            bookmarks.setIconSize(make_size(defs.default_icon))
            bookmarks.setGridSize(QtCore.QSize())
            list_mode = 'list'

        if list_mode != self.list_mode:
            self.list_mode = list_mode
            self.context.cfg.set_user('cola.startupmode', list_mode)

    def resize_widget(self):
        screen = QtWidgets.QApplication.instance().desktop()
        self.setGeometry(
            screen.width() // 4,
            screen.height() // 4,
            screen.width() // 2,
            screen.height() // 2,
        )

    def find_git_repo(self):
        """
        Return a path to a git repository

        This is the entry point for external callers.
        This method finds a git repository by allowing the
        user to browse to one on the filesystem or by creating
        a new one with git-clone.

        """
        self.show()
        self.raise_()
        if self.exec_() == QtWidgets.QDialog.Accepted:
            return self.repodir
        return None

    def open_repo(self):
        self.repodir = self.get_selected_bookmark()
        if not self.repodir:
            self.repodir = qtutils.opendir_dialog(
                N_('Open Git Repository...'), core.getcwd()
            )
        if self.repodir:
            self.accept()

    def clone_repo(self):
        context = self.context
        progress = standard.progress('', '', self)
        clone.clone_repo(
            context, self, True, progress, self.clone_repo_done, False
        )

    def clone_repo_done(self, task):
        if task.cmd and task.cmd.status == 0:
            self.repodir = task.destdir
            self.accept()
        else:
            clone.task_finished(task)

    def new_repo(self):
        context = self.context
        repodir = guicmds.new_repo(context)
        if repodir:
            self.repodir = repodir
            self.accept()

    def open_bookmark(self, index):
        if index.row() == 0:
            self.open_repo()
        else:
            self.repodir = self.bookmarks_model.data(index, Qt.UserRole)
            if self.repodir:
                self.accept()

    def get_selected_bookmark(self):
        selected = self.bookmarks.selectedIndexes()
        if selected and selected[0].row() != 0:
            return self.bookmarks_model.data(selected[0], Qt.UserRole)
        return None


def make_size(size):
    """Construct a QSize from a single value"""
    return QtCore.QSize(size, size)
