"""Provides the git-cola startup dialog

The startup dialog is presented when no repositories can be
found at startup.

"""
from __future__ import division, absolute_import, unicode_literals

from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from .. import core
from .. import guicmds
from .. import icons
from .. import qtutils
from ..i18n import N_
from ..settings import Settings
from ..version import version
from . import defs
from . import standard


class StartupDialog(standard.Dialog):
    """Provides a GUI to Open or Clone a git repository."""

    def __init__(self, parent=None, settings=None):
        standard.Dialog.__init__(self, parent, save_settings=True)
        self.setWindowTitle(N_('git-cola'))

        # Top-most large icon
        logo_pixmap = icons.cola().pixmap(defs.huge_icon, defs.huge_icon)

        self.logo_label = QtWidgets.QLabel()
        self.logo_label.setPixmap(logo_pixmap)
        self.logo_label.setAlignment(Qt.AlignCenter)

        self.logo_text_label = QtWidgets.QLabel()
        self.logo_text_label.setText('git cola v%s' % version())
        self.logo_text_label.setAlignment(Qt.AlignCenter)
        self.logo_text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.repodir = None
        self.runtask = qtutils.RunTask(parent=self)

        self.new_button = qtutils.create_button(text=N_('New...'),
                                                icon=icons.new())
        self.open_button = qtutils.create_button(text=N_('Open...'),
                                                 icon=icons.repo())
        self.clone_button = qtutils.create_button(text=N_('Clone...'),
                                                  icon=icons.cola())
        self.close_button = qtutils.close_button()

        if settings is None:
            settings = Settings()
        settings.load()
        self.settings = settings

        self.bookmarks_label = QtWidgets.QLabel(N_('Select Repository...'))
        self.bookmarks_label.setAlignment(Qt.AlignCenter)

        self.bookmarks_model = QtGui.QStandardItemModel()

        item = QtGui.QStandardItem(N_('Select manually...'))
        item.setEditable(False)
        self.bookmarks_model.appendRow(item)

        added = set()

        # Bookmarks/"Favorites" is a dict list and Recent is a string list
        bookmarks = [i['path'] for i in settings.bookmarks]
        all_repos = bookmarks + settings.recent

        for repo in all_repos:
            if repo in added:
                continue
            added.add(repo)
            item = QtGui.QStandardItem(repo)
            item.setEditable(False)
            self.bookmarks_model.appendRow(item)

        selection_mode = QtWidgets.QAbstractItemView.SingleSelection

        self.bookmarks = QtWidgets.QListView()
        self.bookmarks.setSelectionMode(selection_mode)
        self.bookmarks.setAlternatingRowColors(True)
        self.bookmarks.setModel(self.bookmarks_model)

        self.logo_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                        self.logo_label,
                                        self.logo_text_label,
                                        defs.button_spacing,
                                        qtutils.STRETCH)

        self.button_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                          self.open_button, self.clone_button,
                                          self.new_button, qtutils.STRETCH,
                                          self.close_button)

        self.center_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                          self.logo_layout, self.bookmarks)

        self.main_layout = qtutils.vbox(defs.margin, defs.spacing,
                                        self.bookmarks_label,
                                        self.center_layout,
                                        self.button_layout)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.open_button, self.open_repo)
        qtutils.connect_button(self.clone_button, self.clone_repo)
        qtutils.connect_button(self.new_button, self.new_repo)
        qtutils.connect_button(self.close_button, self.reject)

        self.bookmarks.activated.connect(self.open_bookmark)

        self.init_state(settings, self.resize_widget)

    def resize_widget(self):
        screen = QtWidgets.QApplication.instance().desktop()
        self.setGeometry(screen.width() // 4, screen.height() // 4,
                         screen.width() // 2, screen.height() // 2)

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
            self.repodir = qtutils.opendir_dialog(N_('Open Git Repository...'),
                                                  core.getcwd())
        if self.repodir:
            self.accept()

    def clone_repo(self):
        progress = standard.ProgressDialog('', '', self)
        guicmds.clone_repo(self, self.runtask, progress,
                           self.clone_repo_done, False)

    def clone_repo_done(self, task):
        if task.cmd and task.cmd.ok:
            self.repodir = task.destdir
            self.accept()
        else:
            guicmds.report_clone_repo_errors(task)

    def new_repo(self):
        repodir = guicmds.new_repo()
        if repodir:
            self.repodir = repodir
            self.accept()

    def open_bookmark(self, index):
        if(index.row() == 0):
            self.open_repo()
        else:
            self.repodir = self.bookmarks_model.data(index)
            if self.repodir:
                self.accept()

    def get_selected_bookmark(self):
        selected = self.bookmarks.selectedIndexes()
        if(len(selected) > 0 and selected[0].row() != 0):
            return self.bookmarks_model.data(selected[0])
        return None
