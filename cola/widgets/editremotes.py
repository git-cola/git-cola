import operator

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..git import STDOUT
from ..i18n import N_
from ..qtutils import get
from .. import cmds
from .. import core
from .. import gitcmds
from .. import icons
from .. import qtutils
from .. import utils
from . import completion
from . import defs
from . import standard
from . import text


def editor(context, run=True):
    """Launch a RemoteEditor instance"""
    view = RemoteEditor(context, parent=qtutils.active_window())
    if run:
        view.show()
        view.exec_()
    return view


class RemoteEditor(standard.Dialog):
    """Edit remotes associated with the current repository"""

    def __init__(self, context, parent=None):
        standard.Dialog.__init__(self, parent)
        self.setWindowTitle(N_('Edit Remotes'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.context = context
        self.current_name = ''
        self.current_url = ''

        self.remote_list = []
        self.remotes = QtWidgets.QListWidget()
        self.remotes.setToolTip(N_('Remote git repositories - double-click to rename'))

        self.editor = RemoteWidget(context, self)

        self.save_button = qtutils.create_button(
            text=N_('Save'), icon=icons.save(), default=True
        )

        self.reset_button = qtutils.create_button(
            text=N_('Reset'), icon=icons.discard()
        )

        tooltip = N_(
            'Add and remove remote repositories using the \n'
            'Add(+) and Delete(-) buttons on the left-hand side.\n'
            '\n'
            'Remotes can be renamed by selecting one from the list\n'
            'and pressing "enter", or by double-clicking.'
        )
        hint = N_('Edit remotes by selecting them from the list')
        self.default_hint = hint
        self.info = text.VimHintedPlainTextEdit(context, hint, parent=self)
        self.info.setToolTip(tooltip)

        text_width, text_height = qtutils.text_size(self.info.font(), 'M')
        width = text_width * 42
        height = text_height * 13
        self.info.setMinimumWidth(width)
        self.info.setMinimumHeight(height)
        self.info_thread = RemoteInfoThread(context, self)

        icon = icons.add()
        tooltip = N_('Add new remote git repository')
        self.add_button = qtutils.create_toolbutton(icon=icon, tooltip=tooltip)

        self.refresh_button = qtutils.create_toolbutton(
            icon=icons.sync(), tooltip=N_('Refresh')
        )
        self.delete_button = qtutils.create_toolbutton(
            icon=icons.remove(), tooltip=N_('Delete remote')
        )
        self.close_button = qtutils.close_button()

        self._edit_button_layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.save_button, self.reset_button
        )

        self._edit_layout = qtutils.hbox(
            defs.no_margin, defs.spacing, self.editor, self._edit_button_layout
        )

        self._display_layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self._edit_layout, self.info
        )
        self._display_widget = QtWidgets.QWidget(self)
        self._display_widget.setLayout(self._display_layout)

        self._left_buttons_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.add_button,
            self.refresh_button,
            self.delete_button,
            qtutils.STRETCH,
        )
        self._left_layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self._left_buttons_layout, self.remotes
        )
        self._left_widget = QtWidgets.QWidget(self)
        self._left_widget.setLayout(self._left_layout)

        self._top_layout = qtutils.splitter(
            Qt.Horizontal, self._left_widget, self._display_widget
        )
        width = self._top_layout.width()
        self._top_layout.setSizes([width // 4, width * 3 // 4])

        self._button_layout = qtutils.hbox(
            defs.margin,
            defs.spacing,
            qtutils.STRETCH,
            self.close_button,
        )
        self._layout = qtutils.vbox(
            defs.margin, defs.spacing, self._top_layout, self._button_layout
        )
        self.setLayout(self._layout)

        qtutils.connect_button(self.add_button, self.add)
        qtutils.connect_button(self.delete_button, self.delete)
        qtutils.connect_button(self.refresh_button, self.refresh)
        qtutils.connect_button(self.close_button, self.accept)
        qtutils.connect_button(self.save_button, self.save)
        qtutils.connect_button(self.reset_button, self.reset)
        qtutils.add_close_action(self)

        thread = self.info_thread
        thread.result.connect(self.set_info, type=Qt.QueuedConnection)

        self.editor.remote_name.returnPressed.connect(self.save)
        self.editor.remote_url.returnPressed.connect(self.save)
        self.editor.valid.connect(self.editor_validated)

        self.remotes.itemChanged.connect(self.remote_item_renamed)
        self.remotes.itemSelectionChanged.connect(self.selection_changed)

        self.disable_editor()
        self.init_state(None, self.resize_widget, parent)
        self.remotes.setFocus(Qt.OtherFocusReason)
        self.refresh()

    def reset(self):
        """Reset the editor back to the last-saved configuration"""
        focus = self.focusWidget()
        if self.current_name:
            self.activate_remote(self.current_name, gather_info=False)
        restore_focus(focus)

    @property
    def changed(self):
        """Has the editor changed any values?"""
        url = self.editor.url
        name = self.editor.name
        return url != self.current_url or name != self.current_name

    def save(self):
        """Save edited settings to Git's configuration"""
        if not self.changed:
            return
        context = self.context
        name = self.editor.name
        url = self.editor.url
        old_url = self.current_url
        old_name = self.current_name

        name_changed = name and name != old_name
        url_changed = url and url != old_url

        focus = self.focusWidget()
        name_ok = False
        url_ok = False

        # Run the corresponding commands
        if name_changed and url_changed:
            name_ok, url_ok = cmds.do(cmds.RemoteEdit, context, old_name, name, url)
        elif name_changed:
            result = cmds.do(cmds.RemoteRename, context, old_name, name)
            name_ok = result[0]
        elif url_changed:
            result = cmds.do(cmds.RemoteSetURL, context, name, url)
            url_ok = result[0]

        # Update state if the URL change succeeded
        gather = False
        if url_changed and url_ok:
            self.current_url = url
            gather = True

        # A name change requires a refresh
        if name_changed and name_ok:
            self.current_name = name

            self.refresh(select=False)
            remotes = utils.Sequence(self.remote_list)
            idx = remotes.index(name)
            self.select_remote(idx)
            gather = False  # already done by select_remote()

        if name_changed or url_changed:
            valid = self.editor.validate()
            self.editor_validated(valid)

        restore_focus(focus)
        if gather:
            self.gather_info()

    def editor_validated(self, valid):
        """Update widgets when fields are edited and validated"""
        changed = self.changed
        self.reset_button.setEnabled(changed)
        self.save_button.setEnabled(changed and valid)

    def disable_editor(self):
        """Disable the editor"""
        self.save_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        self.editor.setEnabled(False)
        self.editor.name = ''
        self.editor.url = ''
        self.info.hint.set_value(self.default_hint)
        self.info.set_value('')

    def resize_widget(self, parent):
        """Set the initial size of the widget"""
        width, height = qtutils.default_size(parent, 720, 445)
        self.resize(width, height)

    def set_info(self, info):
        """Update the info display widget with remote details"""
        self.info.hint.set_value(self.default_hint)
        self.info.set_value(info)

    def select_remote(self, index):
        """Select a remote by index"""
        if index >= 0:
            item = self.remotes.item(index)
            if item:
                item.setSelected(True)

    def refresh(self, select=True):
        """Refresh the list of remotes to match the Git configuration"""
        git = self.context.git
        remotes = git.remote()[STDOUT].splitlines()
        # Ignore notifications from self.remotes while mutating.
        with qtutils.BlockSignals(self.remotes):
            self.remotes.clear()
            self.remotes.addItems(remotes)
            self.remote_list = remotes

            for idx in range(len(remotes)):
                item = self.remotes.item(idx)
                item.setFlags(item.flags() | Qt.ItemIsEditable)

        if select:
            if not self.current_name and remotes:
                # Nothing is selected; select the first item
                self.select_remote(0)
            elif self.current_name and remotes:
                # Reselect the previously selected item
                remote_seq = utils.Sequence(remotes)
                idx = remote_seq.index(self.current_name)
                if idx >= 0:
                    item = self.remotes.item(idx)
                    if item:
                        item.setSelected(True)

    def add(self):
        """Add a new remote"""
        ok, name = add_remote(self.context, self)
        if ok:
            self.refresh(select=False)
            try:
                idx = self.remote_list.index(name)
            except ValueError:
                return
            self.select_remote(idx)

    def delete(self):
        """Delete the current remote"""
        remote = qtutils.selected_item(self.remotes, self.remote_list)
        if not remote:
            return
        cmds.do(cmds.RemoteRemove, self.context, remote)
        self.update_editor(name='', url='', enable=False)
        self.refresh(select=True)

    def remote_item_renamed(self, item):
        """Update the editor when the remote name is edited from the remotes list"""
        idx = self.remotes.row(item)
        if idx < 0:
            return
        if idx >= len(self.remote_list):
            return
        old_name = self.remote_list[idx]
        new_name = item.text()
        if new_name == old_name:
            return
        if not new_name:
            item.setText(old_name)
            return
        context = self.context
        ok, status, _, _ = cmds.do(cmds.RemoteRename, context, old_name, new_name)
        if ok and status == 0:
            self.remote_list[idx] = new_name
            self.activate_remote(new_name)
        else:
            item.setText(old_name)

    def selection_changed(self):
        """Edit remotes when the remote list selection is changed"""
        remote = qtutils.selected_item(self.remotes, self.remote_list)
        if not remote:
            self.disable_editor()
            return
        self.activate_remote(remote)

    def activate_remote(self, name, gather_info=True):
        """Activate the specified remote"""
        url = gitcmds.remote_url(self.context, name)
        self.update_editor(name=name, url=url)
        if gather_info:
            self.gather_info()

    def update_editor(self, name=None, url=None, enable=True):
        """Update the editor and enable it for editing"""
        # These fields must be updated in this exact order otherwise
        # the editor will be seen as edited, which causes the Reset button
        # to re-enable itself via the valid() -> editor_validated() signal chain.
        if name is not None:
            self.current_name = name
            self.editor.name = name
        if url is not None:
            self.current_url = url
            self.editor.url = url

        self.editor.setEnabled(enable)

    def gather_info(self):
        """Display details about the remote"""
        name = self.current_name
        self.info.hint.set_value(N_('Gathering info for "%s"...') % name)
        self.info.set_value('')
        self.info_thread.remote = name
        self.info_thread.start()


def add_remote(context, parent, name='', url='', readonly_url=False):
    """Bring up the "Add Remote" dialog"""
    widget = AddRemoteDialog(context, parent, readonly_url=readonly_url)
    if name:
        widget.name = name
    if url:
        widget.url = url
    if widget.run():
        cmds.do(cmds.RemoteAdd, context, widget.name, widget.url)
        result = True
    else:
        result = False
    return (result, widget.name)


def restore_focus(focus):
    if focus:
        focus.setFocus(Qt.OtherFocusReason)
        if hasattr(focus, 'selectAll'):
            focus.selectAll()


class RemoteInfoThread(QtCore.QThread):
    """Gathers information about a remote for display in the info widget"""

    result = Signal(object)

    def __init__(self, context, parent):
        QtCore.QThread.__init__(self, parent)
        self.context = context
        self.remote = None

    def run(self):
        """Run the thread to gather information"""
        remote = self.remote
        if remote is None:
            return
        git = self.context.git
        _, out, err = git.remote('show', '-n', remote, _readonly=True)
        self.result.emit(out + err)


class AddRemoteDialog(QtWidgets.QDialog):
    """A simple dialog for adding remotes"""

    def __init__(self, context, parent, readonly_url=False):
        super().__init__(parent)
        self.context = context
        if parent:
            self.setWindowModality(Qt.WindowModal)

        self.context = context
        self.widget = RemoteWidget(context, self, readonly_url=readonly_url)
        self.add_button = qtutils.create_button(
            text=N_('Add Remote'), icon=icons.ok(), enabled=False
        )
        self.close_button = qtutils.close_button()

        self._button_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            qtutils.STRETCH,
            self.close_button,
            self.add_button,
        )

        self._layout = qtutils.vbox(
            defs.margin, defs.spacing, self.widget, self._button_layout
        )
        self.setLayout(self._layout)

        self.widget.valid.connect(self.add_button.setEnabled)
        qtutils.connect_button(self.add_button, self.accept)
        qtutils.connect_button(self.close_button, self.reject)

    def set_name(self, value):
        self.widget.name = value

    def set_url(self, value):
        self.widget.url = value

    name = property(operator.attrgetter('widget.name'), set_name)
    url = property(operator.attrgetter('widget.url'), set_url)

    def run(self):
        self.show()
        self.raise_()
        return self.exec_() == QtWidgets.QDialog.Accepted


def lineedit(context, hint):
    """Create a HintedLineEdit with a preset minimum width"""
    widget = text.HintedLineEdit(context, hint)
    width = qtutils.text_width(widget.font(), 'M')
    widget.setMinimumWidth(width * 32)
    return widget


class RemoteWidget(QtWidgets.QWidget):
    name = property(
        lambda self: get(self.remote_name),
        lambda self, value: self.remote_name.set_value(value),
    )
    url = property(
        lambda self: get(self.remote_url),
        lambda self, value: self.remote_url.set_value(value),
    )
    valid = Signal(bool)

    def __init__(self, context, parent, readonly_url=False):
        super().__init__(parent)
        self.setWindowModality(Qt.WindowModal)
        self.context = context
        self.setWindowTitle(N_('Add remote'))
        self.remote_name = lineedit(context, N_('Name for the new remote'))
        self.remote_url = lineedit(context, N_('https://git.example.com/user/repo.git'))
        self.open_button = qtutils.create_button(
            text=N_('Browse...'), icon=icons.folder(), tooltip=N_('Select repository')
        )

        self.url_layout = qtutils.hbox(
            defs.no_margin, defs.spacing, self.remote_url, self.open_button
        )

        validate_remote = completion.RemoteValidator(self.remote_name)
        self.remote_name.setValidator(validate_remote)

        self._form = qtutils.form(
            defs.margin,
            defs.spacing,
            (N_('Name'), self.remote_name),
            (N_('URL'), self.url_layout),
        )
        self._layout = qtutils.vbox(defs.margin, defs.spacing, self._form)
        self.setLayout(self._layout)

        self.remote_name.textChanged.connect(self.validate)
        self.remote_url.textChanged.connect(self.validate)
        qtutils.connect_button(self.open_button, self.open_repo)

        if readonly_url:
            self.remote_url.setReadOnly(True)
            self.open_button.setEnabled(False)

    def validate(self, _text_or_index=''):
        """Validate the current inputs"""
        name = self.name
        url = self.url
        self.valid.emit(bool(name) and bool(url))

    def open_repo(self):
        """Set the URL from a repository on disk"""
        git = self.context.git
        repo = qtutils.opendir_dialog(N_('Open Git Repository'), core.getcwd())
        if repo and git.is_git_repository(repo):
            self.url = repo
