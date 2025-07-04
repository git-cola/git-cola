"""The startup dialog is presented when no repositories can be found at startup"""

from qtpy.QtCore import Qt
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets

from ..i18n import N_
from ..models import prefs
from .. import cmds
from .. import core
from .. import display
from .. import guicmds
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import utils
from .. import version
from . import clone
from . import defs
from . import standard


ICON_MODE = 0
LIST_MODE = 1


class StartupDialog(standard.Dialog):
    """Provides a GUI to Open or Clone a git repository."""

    def __init__(self, context, parent=None):
        standard.Dialog.__init__(self, parent)
        self.context = context
        self.setWindowTitle(N_('git-cola'))

        # Top-most large icon
        self.logo_label = qtutils.pixmap_label(icons.cola(), defs.huge_icon)
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
            text=N_('Open Git Repository'), icon=icons.folder()
        )
        self.clone_button = qtutils.create_button(
            text=N_('Clone...'), icon=icons.cola()
        )
        self.close_button = qtutils.close_button()

        self.bookmarks_model = bookmarks_model = QtGui.QStandardItemModel()
        self.items = items = []

        item = QtGui.QStandardItem(N_('Browse...'))
        item.setEditable(False)
        item.setIcon(icons.open_directory())
        bookmarks_model.appendRow(item)

        # The tab bar allows choosing between Folder and List mode
        self.tab_bar = QtWidgets.QTabBar()
        self.tab_bar.setMovable(False)
        self.tab_bar.addTab(icons.directory(), N_('Folder'))
        self.tab_bar.addTab(icons.three_bars(), N_('List'))

        # Bookmarks/"Favorites" and Recent are lists of {name,path: str}
        normalize = display.normalize_path
        settings = context.settings
        all_repos = get_all_repos(self.context, settings)

        added = set()
        builder = BuildItem(self.context)
        default_view_mode = ICON_MODE
        for repo, is_bookmark in all_repos:
            path = normalize(repo['path'])
            name = normalize(repo['name'])
            if path in added:
                continue
            added.add(path)

            item = builder.get(path, name, default_view_mode, is_bookmark)
            bookmarks_model.appendRow(item)
            items.append(item)

        self.bookmarks = BookmarksListView(
            context,
            bookmarks_model,
            self.open_selected_bookmark,
            self.set_model,
        )

        self.tab_layout = qtutils.vbox(
            defs.no_margin, defs.no_spacing, self.tab_bar, self.bookmarks
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
        self.tab_bar.currentChanged.connect(self.tab_changed)

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
        if idx == ICON_MODE:
            mode = QtWidgets.QListView.IconMode
            icon_size = make_size(defs.medium_icon)
            grid_size = make_size(defs.large_icon)
            list_mode = 'folder'
            view_mode = ICON_MODE
            rename_enabled = True
        else:
            mode = QtWidgets.QListView.ListMode
            icon_size = make_size(defs.default_icon)
            grid_size = QtCore.QSize()
            list_mode = 'list'
            view_mode = LIST_MODE
            rename_enabled = False

        self.bookmarks.set_rename_enabled(rename_enabled)
        self.bookmarks.set_view_mode(view_mode)

        bookmarks.setViewMode(mode)
        bookmarks.setIconSize(icon_size)
        bookmarks.setGridSize(grid_size)

        new_items = []
        builder = BuildItem(self.context)
        for item in self.items:
            if isinstance(item, PromptWidgetItem):
                item = builder.get(item.path, item.name, view_mode, item.is_bookmark)
                new_items.append(item)

        self.set_model(new_items)

        if list_mode != self.list_mode:
            self.list_mode = list_mode
            self.context.cfg.set_user('cola.startupmode', list_mode)

    def resize_widget(self):
        width, height = qtutils.desktop_size()
        self.setGeometry(
            width // 4,
            height // 4,
            width // 2,
            height // 2,
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
                N_('Open Git Repository'), core.getcwd()
            )
        if self.repodir:
            self.accept()

    def clone_repo(self):
        context = self.context
        progress = standard.progress('', '', self)
        clone.clone_repo(context, True, progress, self.clone_repo_done, False)

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

    def open_selected_bookmark(self):
        selected = self.bookmarks.selectedIndexes()
        if selected:
            self.open_bookmark(selected[0])

    def open_bookmark(self, index):
        if index.row() == 0:
            self.open_repo()
        else:
            self.repodir = self.bookmarks_model.data(index, Qt.UserRole)
            if not self.repodir:
                return
            if not core.exists(self.repodir):
                self.handle_broken_repo(index)
                return
            self.accept()

    def handle_broken_repo(self, index):
        settings = self.context.settings
        all_repos = get_all_repos(self.context, settings)

        repodir = self.bookmarks_model.data(index, Qt.UserRole)
        repo = next(repo for repo, is_bookmark in all_repos if repo['path'] == repodir)
        title = N_('Repository Not Found')
        text = N_('%s could not be opened. Remove from bookmarks?') % repo['path']
        logo = icons.from_style(QtWidgets.QStyle.SP_MessageBoxWarning)
        if standard.question(title, text, N_('Remove'), logo=logo):
            self.context.settings.remove_bookmark(repo['path'], repo['name'])
            self.context.settings.remove_recent(repo['path'])
            self.context.settings.save()

            item = self.bookmarks_model.item(index.row())
            self.items.remove(item)
            self.bookmarks_model.removeRow(index.row())

    def get_selected_bookmark(self):
        selected = self.bookmarks.selectedIndexes()
        if selected and selected[0].row() != 0:
            return self.bookmarks_model.data(selected[0], Qt.UserRole)
        return None

    def set_model(self, items):
        bookmarks_model = self.bookmarks_model
        self.items = new_items = []
        bookmarks_model.clear()

        item = QtGui.QStandardItem(N_('Browse...'))
        item.setEditable(False)
        item.setIcon(icons.open_directory())
        bookmarks_model.appendRow(item)

        for item in items:
            bookmarks_model.appendRow(item)
            new_items.append(item)


def get_all_repos(context, settings):
    """Return a sorted list of bookmarks and recent repositories"""
    bookmarks = settings.bookmarks
    recent = settings.recent
    all_repos = [(repo, True) for repo in bookmarks] + [
        (repo, False) for repo in recent
    ]
    if prefs.sort_bookmarks(context):
        all_repos.sort(key=lambda details: details[0]['path'].lower())
    return all_repos


class BookmarksListView(QtWidgets.QListView):
    """
    List view class implementation of QWidgets.QListView for bookmarks and recent repos.
    Almost methods is comes from `cola/widgets/bookmarks.py`.
    """

    def __init__(self, context, model, open_selected_repo, set_model, parent=None):
        super().__init__(parent)

        self.current_mode = ICON_MODE
        self.context = context
        self.open_selected_repo = open_selected_repo
        self.set_model = set_model

        self.setEditTriggers(self.__class__.SelectedClicked)

        self.activated.connect(self.open_selected_repo)

        self.setModel(model)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setViewMode(QtWidgets.QListView.IconMode)
        self.setResizeMode(QtWidgets.QListView.Adjust)
        self.setGridSize(make_size(defs.large_icon))
        self.setIconSize(make_size(defs.medium_icon))
        self.setDragEnabled(False)
        self.setWordWrap(True)

        # Context Menu
        self.open_action = qtutils.add_action(
            self, N_('Open'), self.open_selected_repo, hotkeys.OPEN
        )

        self.accept_action = qtutils.add_action(
            self, N_('Accept'), self.accept_repo, *hotkeys.ACCEPT
        )

        self.open_new_action = qtutils.add_action(
            self, N_('Open in New Window'), self.open_new_repo, hotkeys.NEW
        )

        self.set_default_repo_action = qtutils.add_action(
            self, N_('Set Default Repository'), self.set_default_repo
        )

        self.clear_default_repo_action = qtutils.add_action(
            self, N_('Clear Default Repository'), self.clear_default_repo
        )

        self.rename_repo_action = qtutils.add_action(
            self, N_('Rename Repository'), self.rename_repo
        )

        self.open_default_action = qtutils.add_action(
            self, cmds.OpenDefaultApp.name(), self.open_default, hotkeys.PRIMARY_ACTION
        )

        self.launch_editor_action = qtutils.add_action(
            self, cmds.Edit.name(), self.launch_editor, hotkeys.EDIT
        )

        self.launch_terminal_action = qtutils.add_action(
            self, cmds.LaunchTerminal.name(), self.launch_terminal, hotkeys.TERMINAL
        )

        self.copy_action = qtutils.add_action(self, N_('Copy'), self.copy, hotkeys.COPY)

        self.delete_action = qtutils.add_action(self, N_('Delete'), self.delete_item)

        self.remove_missing_action = qtutils.add_action(
            self, N_('Prune Missing Entries'), self.remove_missing
        )
        self.remove_missing_action.setToolTip(
            N_('Remove stale entries for repositories that no longer exist')
        )

        self.model().itemChanged.connect(self.item_changed)

        self.action_group = utils.Group(
            self.open_action,
            self.open_new_action,
            self.copy_action,
            self.launch_editor_action,
            self.launch_terminal_action,
            self.open_default_action,
            self.rename_repo_action,
            self.delete_action,
        )
        self.action_group.setEnabled(True)
        self.set_default_repo_action.setEnabled(True)
        self.clear_default_repo_action.setEnabled(True)

    def set_rename_enabled(self, is_enabled):
        self.rename_repo_action.setEnabled(is_enabled)

    def set_view_mode(self, view_mode):
        self.current_mode = view_mode

    def selected_item(self):
        index = self.currentIndex()
        return self.model().itemFromIndex(index)

    def refresh(self):
        self.model().layoutChanged.emit()
        context = self.context
        settings = context.settings
        builder = BuildItem(context)
        normalize = display.normalize_path
        items = []
        added = set()

        all_repos = get_all_repos(self.context, settings)
        for repo, is_bookmark in all_repos:
            path = normalize(repo['path'])
            name = normalize(repo['name'])
            if path in added:
                continue
            added.add(path)

            item = builder.get(path, name, self.current_mode, is_bookmark)
            items.append(item)

        self.set_model(items)

    def contextMenuEvent(self, event):
        """Configures prompt's context menu."""
        item = self.selected_item()

        if isinstance(item, PromptWidgetItem):
            menu = qtutils.create_menu(N_('Actions'), self)
            menu.addAction(self.open_action)
            menu.addAction(self.open_new_action)
            menu.addAction(self.open_default_action)
            menu.addSeparator()
            menu.addAction(self.copy_action)
            menu.addAction(self.launch_editor_action)
            menu.addAction(self.launch_terminal_action)
            menu.addSeparator()
            if item and item.is_default:
                menu.addAction(self.clear_default_repo_action)
            else:
                menu.addAction(self.set_default_repo_action)
            menu.addAction(self.rename_repo_action)
            menu.addSeparator()
            menu.addAction(self.delete_action)
            menu.addAction(self.remove_missing_action)
            menu.exec_(self.mapToGlobal(event.pos()))

    def item_changed(self, item):
        self.rename_entry(item, item.text())

    def rename_entry(self, item, new_name):
        settings = self.context.settings
        if item.is_bookmark:
            rename = settings.rename_bookmark
        else:
            rename = settings.rename_recent

        if rename(item.path, item.name, new_name):
            settings.save()
            item.name = new_name
        else:
            item.setText(item.name)

    def apply_func(self, func, *args, **kwargs):
        item = self.selected_item()
        if item:
            func(item, *args, **kwargs)

    def copy(self):
        self.apply_func(lambda item: qtutils.set_clipboard(item.path))

    def open_default(self):
        context = self.context
        self.apply_func(lambda item: cmds.do(cmds.OpenDefaultApp, context, [item.path]))

    def set_default_repo(self):
        self.apply_func(self.set_default_item)

    def set_default_item(self, item):
        context = self.context
        cmds.do(cmds.SetDefaultRepo, context, item.path)
        self.refresh()

    def clear_default_repo(self):
        self.apply_func(self.clear_default_item)

    def clear_default_item(self, _item):
        context = self.context
        cmds.do(cmds.SetDefaultRepo, context, None)
        self.refresh()

    def rename_repo(self):
        index = self.currentIndex()
        self.edit(index)

    def accept_repo(self):
        self.apply_func(self.accept_item)

    def accept_item(self, _item):
        if qtutils.enum_value(self.state()) & qtutils.enum_value(self.EditingState):
            current_index = self.currentIndex()
            widget = self.indexWidget(current_index)
            if widget:
                self.commitData(widget)
            self.closePersistentEditor(current_index)
            self.refresh()
        else:
            self.open_selected_repo()

    def open_new_repo(self):
        context = self.context
        self.apply_func(lambda item: cmds.do(cmds.OpenNewRepo, context, item.path))

    def launch_editor(self):
        context = self.context
        self.apply_func(lambda item: cmds.do(cmds.Edit, context, [item.path]))

    def launch_terminal(self):
        context = self.context
        self.apply_func(lambda item: cmds.do(cmds.LaunchTerminal, context, item.path))

    def delete_item(self):
        """Remove the selected repo item

        If the item comes from bookmarks (item.is_bookmark) then delete the item
        from the Bookmarks list, otherwise delete it from the Recents list.
        """
        item = self.selected_item()
        if not item:
            return

        if item.is_bookmark:
            cmd = cmds.RemoveBookmark
        else:
            cmd = cmds.RemoveRecent
        context = self.context
        ok, _, _, _ = cmds.do(cmd, context, item.path, item.name, icon=icons.discard())
        if ok:
            self.refresh()

    def remove_missing(self):
        """Remove missing entries from the favorites/recent file list"""
        settings = self.context.settings
        settings.remove_missing_bookmarks()
        settings.remove_missing_recent()
        settings.save()
        self.refresh()


class BuildItem:
    def __init__(self, context):
        self.star_icon = icons.star()
        self.folder_icon = icons.folder()
        cfg = context.cfg
        self.default_repo = cfg.get('cola.defaultrepo')

    def get(self, path, name, mode, is_bookmark):
        is_default = self.default_repo == path
        if is_default:
            icon = self.star_icon
        else:
            icon = self.folder_icon
        return PromptWidgetItem(path, name, mode, icon, is_default, is_bookmark)


class PromptWidgetItem(QtGui.QStandardItem):
    def __init__(self, path, name, mode, icon, is_default, is_bookmark):
        QtGui.QStandardItem.__init__(self, icon, name)
        self.path = path
        self.name = name
        self.mode = mode
        self.is_default = is_default
        self.is_bookmark = is_bookmark
        editable = mode == ICON_MODE

        if self.mode == ICON_MODE:
            item_text = self.name
        else:
            item_text = self.path

        user_role = Qt.UserRole
        self.setEditable(editable)
        self.setData(path, user_role)
        self.setIcon(icon)
        self.setText(item_text)
        self.setToolTip(path)


def make_size(size):
    """Construct a QSize from a single value"""
    return QtCore.QSize(size, size)
