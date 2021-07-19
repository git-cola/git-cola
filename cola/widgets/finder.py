"""File finder widgets"""
from __future__ import absolute_import, division, print_function, unicode_literals
import os
from functools import partial

from qtpy import QtCore
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from ..i18n import N_
from ..qtutils import get
from ..utils import Group
from .. import cmds
from .. import core
from .. import gitcmds
from .. import hotkeys
from .. import icons
from .. import utils
from .. import qtutils
from . import completion
from . import defs
from . import filetree
from . import standard
from . import text


def finder(context, paths=None):
    """Prompt and use 'git grep' to find the content."""
    parent = qtutils.active_window()
    widget = new_finder(context, paths=paths, parent=parent)
    widget.show()
    widget.raise_()
    return widget


def new_finder(context, paths=None, parent=None):
    """Create a finder widget"""
    widget = Finder(context, parent=parent)
    widget.search_for(paths or '')
    return widget


def add_wildcards(arg):
    """Add "*" around user input to generate ls-files pathspecs matches

    >>> '*x*' == \
        add_wildcards('x') == \
        add_wildcards('*x') == \
        add_wildcards('x*') == \
        add_wildcards('*x*')
    True

    """
    if not arg.startswith('*'):
        arg = '*' + arg
    if not arg.endswith('*'):
        arg = arg + '*'
    return arg


def show_help(context):
    """Show the help page"""
    help_text = N_(
        """
Keyboard Shortcuts
------------------
J, Down     = Move Down
K, Up       = Move Up
Enter       = Edit Selected Files
Spacebar    = Open File Using Default Application
Ctrl + L    = Focus Text Entry Field
?           = Show Help

The up and down arrows change focus between the text entry field
and the results.
"""
    )
    title = N_('Help - Find Files')
    return text.text_dialog(context, help_text, title)


class FindFilesThread(QtCore.QThread):
    """Finds files asynchronously"""

    result = Signal(object)

    def __init__(self, context, parent):
        QtCore.QThread.__init__(self, parent)
        self.context = context
        self.query = None

    def run(self):
        context = self.context
        query = self.query
        if query is None:
            args = []
        else:
            args = [add_wildcards(arg) for arg in utils.shell_split(query)]
        filenames = gitcmds.tracked_files(context, *args)
        if query == self.query:
            self.result.emit(filenames)
        else:
            self.run()


class Finder(standard.Dialog):
    """File Finder dialog"""

    def __init__(self, context, parent=None):
        standard.Dialog.__init__(self, parent)
        self.context = context
        self.setWindowTitle(N_('Find Files'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        label = os.path.basename(core.getcwd()) + '/'
        self.input_label = QtWidgets.QLabel(label)
        self.input_txt = completion.GitTrackedLineEdit(context, hint=N_('<path> ...'))

        self.tree = filetree.FileTree(parent=self)

        self.edit_button = qtutils.edit_button(default=True)
        self.edit_button.setShortcut(hotkeys.EDIT)

        name = cmds.OpenDefaultApp.name()
        icon = icons.default_app()
        self.open_default_button = qtutils.create_button(text=name, icon=icon)
        self.open_default_button.setShortcut(hotkeys.PRIMARY_ACTION)

        self.button_group = Group(self.edit_button, self.open_default_button)
        self.button_group.setEnabled(False)

        self.refresh_button = qtutils.refresh_button()
        self.refresh_button.setShortcut(hotkeys.REFRESH)

        self.help_button = qtutils.create_button(
            text=N_('Help'), tooltip=N_('Show help\nShortcut: ?'), icon=icons.question()
        )

        self.close_button = qtutils.close_button()

        self.input_layout = qtutils.hbox(
            defs.no_margin, defs.button_spacing, self.input_label, self.input_txt
        )

        self.bottom_layout = qtutils.hbox(
            defs.no_margin,
            defs.button_spacing,
            self.close_button,
            qtutils.STRETCH,
            self.help_button,
            self.refresh_button,
            self.open_default_button,
            self.edit_button,
        )

        self.main_layout = qtutils.vbox(
            defs.margin,
            defs.no_spacing,
            self.input_layout,
            self.tree,
            self.bottom_layout,
        )
        self.setLayout(self.main_layout)
        self.setFocusProxy(self.input_txt)

        thread = self.worker_thread = FindFilesThread(context, self)
        thread.result.connect(self.process_result, type=Qt.QueuedConnection)

        # pylint: disable=no-member
        self.input_txt.textChanged.connect(lambda s: self.search())
        self.input_txt.activated.connect(self.focus_tree)
        self.input_txt.down.connect(self.focus_tree)
        self.input_txt.enter.connect(self.focus_tree)

        item_selection_changed = self.tree_item_selection_changed
        self.tree.itemSelectionChanged.connect(item_selection_changed)
        self.tree.up.connect(self.focus_input)
        self.tree.space.connect(self.open_default)

        qtutils.add_action(
            self, 'Focus Input', self.focus_input, hotkeys.FOCUS, hotkeys.FINDER
        )

        self.show_help_action = qtutils.add_action(
            self, N_('Show Help'), partial(show_help, context), hotkeys.QUESTION
        )

        qtutils.connect_button(self.edit_button, self.edit)
        qtutils.connect_button(self.open_default_button, self.open_default)
        qtutils.connect_button(self.refresh_button, self.search)
        qtutils.connect_button(self.help_button, show_help)
        qtutils.connect_button(self.close_button, self.close)
        qtutils.add_close_action(self)

        self.init_size(parent=parent)

    def focus_tree(self):
        self.tree.setFocus()

    def focus_input(self):
        self.input_txt.setFocus()

    def search(self):
        self.button_group.setEnabled(False)
        self.refresh_button.setEnabled(False)
        query = get(self.input_txt)
        self.worker_thread.query = query
        self.worker_thread.start()

    def search_for(self, txt):
        self.input_txt.set_value(txt)
        self.focus_input()

    def process_result(self, filenames):
        self.tree.set_filenames(filenames, select=True)
        self.refresh_button.setEnabled(True)

    def edit(self):
        context = self.context
        paths = self.tree.selected_filenames()
        cmds.do(cmds.Edit, context, paths, background_editor=True)

    def open_default(self):
        context = self.context
        paths = self.tree.selected_filenames()
        cmds.do(cmds.OpenDefaultApp, context, paths)

    def tree_item_selection_changed(self):
        enabled = bool(self.tree.selected_item())
        self.button_group.setEnabled(enabled)
