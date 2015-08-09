from __future__ import division, absolute_import, unicode_literals
import os

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import gitcmds
from cola import utils
from cola import qtutils
from cola.i18n import N_
from cola.widgets import completion
from cola.widgets import defs
from cola.widgets import filetree
from cola.widgets import standard
from cola.widgets import text


def finder(paths=None):
    """Prompt and use 'git grep' to find the content."""
    widget = new_finder(paths=paths, parent=qtutils.active_window())
    widget.show()
    widget.raise_()
    return widget


def new_finder(paths=None, parent=None):
    widget = Finder(parent=parent)
    widget.search_for(paths or '')
    return widget


def add_wildcards(arg):
    if not arg.startswith('*'):
        arg = '*' + arg
    if not arg.endswith('*'):
        arg = arg + '*'
    return arg


def show_help():
    help_text = N_("""
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
""")
    title = N_('Help - Find Files')
    return text.text_dialog(help_text, title)


class FindFilesThread(QtCore.QThread):

    def __init__(self, parent):
        QtCore.QThread.__init__(self, parent)
        self.query = None

    def run(self):
        query = self.query
        if query is None:
            args = []
        else:
            args = [add_wildcards(arg) for arg in utils.shell_split(query)]
        filenames = gitcmds.tracked_files(*args)
        if query == self.query:
            self.emit(SIGNAL('result(PyQt_PyObject)'), filenames)
        else:
            self.run()


class Finder(standard.Dialog):

    def __init__(self, parent=None):
        standard.Dialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowTitle(N_('Find Files'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.input_label = QtGui.QLabel(os.path.basename(core.getcwd()) + '/')
        self.input_txt = completion.GitTrackedLineEdit(hint=N_('<path> ...'))
        self.input_txt.hint.enable(True)

        self.tree = filetree.FileTree(parent=self)

        self.edit_button = QtGui.QPushButton(N_('Edit'))
        self.edit_button.setIcon(qtutils.open_file_icon())
        self.edit_button.setEnabled(False)
        self.edit_button.setShortcut(cmds.Edit.SHORTCUT)

        self.open_default_button = QtGui.QPushButton(cmds.OpenDefaultApp.name())
        self.open_default_button.setIcon(qtutils.open_file_icon())
        self.open_default_button.setEnabled(False)
        self.open_default_button.setShortcut(cmds.OpenDefaultApp.SHORTCUT)

        self.refresh_button = QtGui.QPushButton(N_('Refresh'))
        self.refresh_button.setIcon(qtutils.reload_icon())
        self.refresh_button.setShortcut(QtGui.QKeySequence.Refresh)

        self.help_button = qtutils.create_button(
                text=N_('Help'),
                tooltip=N_('Show help\nShortcut: ?'),
                icon=qtutils.help_icon())

        self.close_button = QtGui.QPushButton(N_('Close'))

        self.input_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                         self.input_label, self.input_txt)

        self.bottom_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                          self.edit_button,
                                          self.open_default_button,
                                          self.refresh_button,
                                          self.help_button,
                                          qtutils.STRETCH,
                                          self.close_button)

        self.main_layout = qtutils.vbox(defs.margin, defs.no_spacing,
                                       self.input_layout,
                                       self.tree,
                                       self.bottom_layout)
        self.setLayout(self.main_layout)
        self.setFocusProxy(self.input_txt)

        self.worker_thread = FindFilesThread(self)
        self.connect(self.worker_thread, SIGNAL('result(PyQt_PyObject)'),
                     self.process_result, Qt.QueuedConnection)

        self.connect(self.input_txt, SIGNAL('textChanged(QString)'),
                     lambda s: self.search())
        self.connect(self.input_txt, SIGNAL('activated()'), self.focus_tree)
        self.connect(self.input_txt, SIGNAL('down()'), self.focus_tree)
        self.connect(self.input_txt, SIGNAL('enter()'), self.focus_tree)
        self.connect(self.input_txt, SIGNAL('return()'), self.focus_tree)

        self.connect(self.tree, SIGNAL('itemSelectionChanged()'),
                     self.tree_item_selection_changed)
        self.connect(self.tree, SIGNAL('up()'), self.focus_input)
        self.connect(self.tree, SIGNAL('space()'), self.open_default)

        qtutils.add_action(self, 'Focus Input', self.focus_input,
                           'Ctrl+L', 'Ctrl+T')

        self.show_help_action = qtutils.add_action(self,
                N_('Show Help'), show_help, Qt.Key_Question)

        qtutils.connect_button(self.edit_button, self.edit)
        qtutils.connect_button(self.open_default_button, self.open_default)
        qtutils.connect_button(self.refresh_button, self.search)
        qtutils.connect_button(self.help_button, show_help)
        qtutils.connect_button(self.close_button, self.close)
        qtutils.add_close_action(self)

        if not self.restore_state():
            width, height = qtutils.default_size(parent, 666, 420)
            self.resize(width, height)

    def focus_tree(self):
        self.tree.setFocus()

    def focus_input(self):
        self.input_txt.setFocus()

    def done(self, exit_code):
        self.save_state()
        return standard.Dialog.done(self, exit_code)

    def search(self):
        self.edit_button.setEnabled(False)
        self.open_default_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        query = self.input_txt.value()
        self.worker_thread.query = query
        self.worker_thread.start()

    def search_for(self, txt):
        self.input_txt.set_value(txt)
        self.focus_input()

    def process_result(self, filenames):
        self.tree.set_filenames(filenames, select=True)
        self.refresh_button.setEnabled(True)

    def edit(self):
        paths = self.tree.selected_filenames()
        cmds.do(cmds.Edit, paths)

    def open_default(self):
        paths = self.tree.selected_filenames()
        cmds.do(cmds.OpenDefaultApp, paths)

    def tree_item_selection_changed(self):
        enabled = bool(self.tree.selected_item())
        self.edit_button.setEnabled(enabled)
        self.open_default_button.setEnabled(enabled)
