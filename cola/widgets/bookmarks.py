"""Provides widgets related to bookmarks"""
import os

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import cmds
from .. import core
from .. import git
from .. import hotkeys
from .. import icons
from .. import qtutils
from .. import utils
from ..i18n import N_
from ..interaction import Interaction
from ..models import prefs
from ..widgets import defs
from ..widgets import standard
from ..widgets import switcher


BOOKMARKS = 0
RECENT_REPOS = 1


def bookmark(context, parent):
    return BookmarksWidget(context, BOOKMARKS, parent=parent)


def recent(context, parent):
    return BookmarksWidget(context, RECENT_REPOS, parent=parent)


class BookmarksWidget(QtWidgets.QFrame):
    def __init__(self, context, style=BOOKMARKS, parent=None):
        QtWidgets.QFrame.__init__(self, parent)

        self.context = context
        self.style = style

        self.items = items = []
        self.model = model = QtGui.QStandardItemModel()

        settings = context.settings
        builder = BuildItem(context)
        # bookmarks
        if self.style == BOOKMARKS:
            entries = settings.bookmarks
        # recent items
        elif self.style == RECENT_REPOS:
            entries = settings.recent

        for entry in entries:
            item = builder.get(entry['path'], entry['name'])
            items.append(item)
            model.appendRow(item)

        place_holder = N_('Search repositories by name...')
        self.quick_switcher = switcher.switcher_outer_view(
            context, model, place_holder=place_holder
        )
        self.tree = BookmarksTreeView(
            context, style, self.set_items_to_models, parent=self
        )

        self.add_button = qtutils.create_action_button(
            tooltip=N_('Add'), icon=icons.add()
        )

        self.delete_button = qtutils.create_action_button(
            tooltip=N_('Delete'), icon=icons.remove()
        )

        self.open_button = qtutils.create_action_button(
            tooltip=N_('Open'), icon=icons.repo()
        )

        self.search_button = qtutils.create_action_button(
            tooltip=N_('Search'), icon=icons.search()
        )

        self.button_group = utils.Group(self.delete_button, self.open_button)
        self.button_group.setEnabled(False)

        self.setFocusProxy(self.tree)
        if style == BOOKMARKS:
            self.setToolTip(N_('Favorite repositories'))
        elif style == RECENT_REPOS:
            self.setToolTip(N_('Recent repositories'))
            self.add_button.hide()

        self.button_layout = qtutils.hbox(
            defs.no_margin,
            defs.spacing,
            self.search_button,
            self.open_button,
            self.add_button,
            self.delete_button,
        )

        self.main_layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.quick_switcher, self.tree
        )
        self.setLayout(self.main_layout)

        self.corner_widget = QtWidgets.QWidget(self)
        self.corner_widget.setLayout(self.button_layout)
        titlebar = parent.titleBarWidget()
        titlebar.add_corner_widget(self.corner_widget)

        qtutils.connect_button(self.add_button, self.tree.add_bookmark)
        qtutils.connect_button(self.delete_button, self.tree.delete_bookmark)
        qtutils.connect_button(self.open_button, self.tree.open_repo)
        qtutils.connect_button(self.search_button, self.toggle_switcher_input_field)

        QtCore.QTimer.singleShot(0, self.reload_bookmarks)

        self.tree.toggle_switcher.connect(self.enable_switcher_input_field)
        # moving key has pressed while focusing on input field
        self.quick_switcher.filter_input.switcher_selection_move.connect(
            self.tree.keyPressEvent
        )
        # escape key has pressed while focusing on input field
        self.quick_switcher.filter_input.switcher_escape.connect(
            self.close_switcher_input_field
        )
        # some key except moving key has pressed while focusing on list view
        self.tree.switcher_text.connect(self.switcher_text_inputted)

    def reload_bookmarks(self):
        # Called once after the GUI is initialized
        tree = self.tree
        tree.refresh()

        model = tree.model()

        model.dataChanged.connect(tree.item_changed)
        selection = tree.selectionModel()
        selection.selectionChanged.connect(tree.item_selection_changed)
        tree.doubleClicked.connect(tree.tree_double_clicked)

    def tree_item_selection_changed(self):
        enabled = bool(self.tree.selected_item())
        self.button_group.setEnabled(enabled)

    def connect_to(self, other):
        self.tree.default_changed.connect(other.tree.refresh)
        other.tree.default_changed.connect(self.tree.refresh)

    def set_items_to_models(self, items):
        model = self.model
        self.items.clear()
        model.clear()

        for item in items:
            self.items.append(item)
            model.appendRow(item)

        self.quick_switcher.proxy_model.setSourceModel(model)
        self.tree.setModel(self.quick_switcher.proxy_model)

    def toggle_switcher_input_field(self):
        visible = self.quick_switcher.filter_input.isVisible()
        self.enable_switcher_input_field(not visible)

    def close_switcher_input_field(self):
        self.enable_switcher_input_field(False)

    def enable_switcher_input_field(self, visible):
        filter_input = self.quick_switcher.filter_input

        filter_input.setVisible(visible)
        if not visible:
            filter_input.clear()

    def switcher_text_inputted(self, event):
        # default selection for first index
        first_proxy_idx = self.quick_switcher.proxy_model.index(0, 0)
        self.tree.setCurrentIndex(first_proxy_idx)

        self.quick_switcher.filter_input.keyPressEvent(event)

    # Qt overrides
    def setFont(self, font):
        """Forward setFont() to child widgets"""
        super().setFont(font)
        self.tree.setFont(font)


def disable_rename(_path, _name, _new_name):
    return False


class BookmarksTreeView(standard.TreeView):
    default_changed = Signal()
    toggle_switcher = Signal(bool)
    # this signal will be emitted when some key pressed while focusing on tree view
    switcher_text = Signal(QtGui.QKeyEvent)

    def __init__(self, context, style, set_model, parent=None):
        standard.TreeView.__init__(self, parent=parent)
        self.context = context
        self.style = style
        self.set_model = set_model

        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)

        # We make the items editable, but we don't want the double-click
        # behavior to trigger editing.  Make it behave like Mac OS X's Finder.
        self.setEditTriggers(self.__class__.SelectedClicked)

        self.open_action = qtutils.add_action(
            self, N_('Open'), self.open_repo, hotkeys.OPEN
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

        self.delete_action = qtutils.add_action(
            self, N_('Delete'), self.delete_bookmark
        )

        self.remove_missing_action = qtutils.add_action(
            self, N_('Prune Missing Entries'), self.remove_missing
        )
        self.remove_missing_action.setToolTip(
            N_('Remove stale entries for repositories that no longer exist')
        )

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
        self.action_group.setEnabled(False)
        self.set_default_repo_action.setEnabled(False)
        self.clear_default_repo_action.setEnabled(False)

        # Connections
        if style == RECENT_REPOS:
            context.model.worktree_changed.connect(
                self.refresh, type=Qt.QueuedConnection
            )

    def keyPressEvent(self, event):
        """
        This will be hooked while focusing on this list view.
        Set input field invisible when escape key pressed.
        Move selection when move key like tab, UP etc pressed.
        Or open input field and simply act like text input to it. This is when
        some character key pressed while focusing on tree view, NOT input field.
        """
        selection_moving_keys = switcher.moving_keys()
        pressed_key = event.key()

        if pressed_key == Qt.Key_Escape:
            self.toggle_switcher.emit(False)
        elif pressed_key in hotkeys.ACCEPT:
            self.accept_repo()
        elif pressed_key in selection_moving_keys:
            super().keyPressEvent(event)
        else:
            self.toggle_switcher.emit(True)
            self.switcher_text.emit(event)

    def refresh(self):
        context = self.context
        settings = context.settings
        builder = BuildItem(context)

        # bookmarks
        if self.style == BOOKMARKS:
            entries = settings.bookmarks
        # recent items
        elif self.style == RECENT_REPOS:
            entries = settings.recent

        items = [builder.get(entry['path'], entry['name']) for entry in entries]
        if self.style == BOOKMARKS and prefs.sort_bookmarks(context):
            items.sort(key=lambda x: x.name.lower())

        self.set_model(items)

    def contextMenuEvent(self, event):
        menu = qtutils.create_menu(N_('Actions'), self)
        menu.addAction(self.open_action)
        menu.addAction(self.open_new_action)
        menu.addAction(self.open_default_action)
        menu.addSeparator()
        menu.addAction(self.copy_action)
        menu.addAction(self.launch_editor_action)
        menu.addAction(self.launch_terminal_action)
        menu.addSeparator()
        item = self.selected_item()
        is_default = bool(item and item.is_default)
        if is_default:
            menu.addAction(self.clear_default_repo_action)
        else:
            menu.addAction(self.set_default_repo_action)
        menu.addAction(self.rename_repo_action)
        menu.addSeparator()
        menu.addAction(self.delete_action)
        menu.addAction(self.remove_missing_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def item_selection_changed(self, selected, _deselected):
        item_idx = selected.indexes()
        if item_idx:
            item = self.model().itemFromIndex(item_idx[0])
            enabled = bool(item)
            self.action_group.setEnabled(enabled)

            is_default = bool(item and item.is_default)
            self.set_default_repo_action.setEnabled(not is_default)
            self.clear_default_repo_action.setEnabled(is_default)

    def tree_double_clicked(self, _index):
        context = self.context
        item = self.selected_item()
        cmds.do(cmds.OpenRepo, context, item.path)
        self.toggle_switcher.emit(False)

    def selected_item(self):
        index = self.currentIndex()
        return self.model().itemFromIndex(index)

    def item_changed(self, _top_left, _bottom_right, _roles):
        item = self.selected_item()
        self.rename_entry(item, item.text())

    def rename_entry(self, item, new_name):
        settings = self.context.settings
        if self.style == BOOKMARKS:
            rename = settings.rename_bookmark
        elif self.style == RECENT_REPOS:
            rename = settings.rename_recent
        else:
            rename = disable_rename
        if rename(item.path, item.name, new_name):
            settings.save()
            item.name = new_name
        else:
            item.setText(item.name)
        self.toggle_switcher.emit(False)

    def apply_func(self, func, *args, **kwargs):
        item = self.selected_item()
        if item:
            func(item, *args, **kwargs)

    def copy(self):
        self.apply_func(lambda item: qtutils.set_clipboard(item.path))
        self.toggle_switcher.emit(False)

    def open_default(self):
        context = self.context
        self.apply_func(lambda item: cmds.do(cmds.OpenDefaultApp, context, [item.path]))
        self.toggle_switcher.emit(False)

    def set_default_repo(self):
        self.apply_func(self.set_default_item)
        self.toggle_switcher.emit(False)

    def set_default_item(self, item):
        context = self.context
        cmds.do(cmds.SetDefaultRepo, context, item.path)
        self.refresh()
        self.default_changed.emit()
        self.toggle_switcher.emit(False)

    def clear_default_repo(self):
        self.apply_func(self.clear_default_item)
        self.default_changed.emit()
        self.toggle_switcher.emit(False)

    def clear_default_item(self, _item):
        context = self.context
        cmds.do(cmds.SetDefaultRepo, context, None)
        self.refresh()
        self.toggle_switcher.emit(False)

    def rename_repo(self):
        index = self.currentIndex()
        self.edit(index)
        self.toggle_switcher.emit(False)

    def accept_repo(self):
        self.apply_func(self.accept_item)
        self.toggle_switcher.emit(False)

    def accept_item(self, _item):
        if self.state() & self.EditingState:
            current_index = self.currentIndex()
            widget = self.indexWidget(current_index)
            if widget:
                self.commitData(widget)
            self.closePersistentEditor(current_index)
            self.refresh()
        else:
            self.open_selected_repo()

    def open_repo(self):
        context = self.context
        self.apply_func(lambda item: cmds.do(cmds.OpenRepo, context, item.path))

    def open_selected_repo(self):
        item = self.selected_item()
        context = self.context
        cmds.do(cmds.OpenRepo, context, item.path)
        self.toggle_switcher.emit(False)

    def open_new_repo(self):
        context = self.context
        self.apply_func(lambda item: cmds.do(cmds.OpenNewRepo, context, item.path))
        self.toggle_switcher.emit(False)

    def launch_editor(self):
        context = self.context
        self.apply_func(lambda item: cmds.do(cmds.Edit, context, [item.path]))
        self.toggle_switcher.emit(False)

    def launch_terminal(self):
        context = self.context
        self.apply_func(lambda item: cmds.do(cmds.LaunchTerminal, context, item.path))
        self.toggle_switcher.emit(False)

    def add_bookmark(self):
        normpath = utils.expandpath(core.getcwd())
        name = os.path.basename(normpath)
        prompt = (
            (N_('Name'), name),
            (N_('Path'), core.getcwd()),
        )
        ok, values = qtutils.prompt_n(N_('Add Favorite'), prompt)
        if not ok:
            return
        name, path = values
        normpath = utils.expandpath(path)
        if git.is_git_worktree(normpath):
            settings = self.context.settings
            settings.load()
            settings.add_bookmark(normpath, name)
            settings.save()
            self.refresh()
        else:
            Interaction.critical(N_('Error'), N_('%s is not a Git repository.') % path)

    def delete_bookmark(self):
        """Removes a bookmark from the bookmarks list"""
        item = self.selected_item()
        context = self.context
        if not item:
            return
        if self.style == BOOKMARKS:
            cmd = cmds.RemoveBookmark
        elif self.style == RECENT_REPOS:
            cmd = cmds.RemoveRecent
        else:
            return
        ok, _, _, _ = cmds.do(cmd, context, item.path, item.name, icon=icons.discard())
        if ok:
            self.refresh()
        self.toggle_switcher.emit(False)

    def remove_missing(self):
        """Remove missing entries from the favorites/recent file list"""
        settings = self.context.settings
        if self.style == BOOKMARKS:
            settings.remove_missing_bookmarks()
        elif self.style == RECENT_REPOS:
            settings.remove_missing_recent()
        settings.save()
        self.refresh()


class BuildItem:
    def __init__(self, context):
        self.star_icon = icons.star()
        self.folder_icon = icons.folder()
        cfg = context.cfg
        self.default_repo = cfg.get('cola.defaultrepo')

    def get(self, path, name):
        is_default = self.default_repo == path
        if is_default:
            icon = self.star_icon
        else:
            icon = self.folder_icon
        return BookmarksTreeItem(path, name, icon, is_default)


class BookmarksTreeItem(switcher.SwitcherListItem):
    def __init__(self, path, name, icon, is_default):
        switcher.SwitcherListItem.__init__(self, name, icon=icon, name=name)

        self.path = path
        self.name = name
        self.is_default = is_default

        self.setIcon(icon)
        self.setText(name)
        self.setToolTip(path)
        self.setFlags(self.flags() | Qt.ItemIsEditable)
