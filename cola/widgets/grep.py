from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import utils
from cola import qtutils
from cola.cmds import do
from cola.git import git
from cola.i18n import N_
from cola.qtutils import diff_font
from cola.widgets import defs
from cola.widgets.standard import Dialog
from cola.widgets.text import VimHintedTextView, HintedLineEdit
from cola.compat import ustr


def grep():
    """Prompt and use 'git grep' to find the content."""
    widget = new_grep(parent=qtutils.active_window())
    widget.show()
    widget.raise_()
    return widget


def new_grep(text=None, parent=None):
    widget = Grep(parent=parent)
    if text:
        widget.search_for(text)
    return widget


def goto_grep(line):
    """Called when Search -> Grep's right-click 'goto' action."""
    filename, line_number, contents = line.split(':', 2)
    do(cmds.Edit, [filename], line_number=line_number)


class GrepThread(QtCore.QThread):

    def __init__(self, parent):
        QtCore.QThread.__init__(self, parent)
        self.query = None
        self.shell = False
        self.regexp_mode = '--basic-regexp'

    def run(self):
        if self.query is None:
            return
        query = self.query
        if self.shell:
            args = utils.shell_split(query)
        else:
            args = [query]
        status, out, err = git.grep(self.regexp_mode, n=True, *args)
        if query == self.query:
            self.emit(SIGNAL('result(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                      status, out, err)
        else:
            self.run()


class Grep(Dialog):

    def __init__(self, parent=None):
        Dialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowTitle(N_('Search'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.edit_action = qtutils.add_action(
                self, N_('Edit'), self.edit, cmds.Edit.SHORTCUT)
        self.edit_action.setEnabled(False)

        self.refresh_action = qtutils.add_action(
                self, N_('Refresh'), self.search, *cmds.Refresh.SHORTCUTS)
        self.refresh_action.setEnabled(False)

        self.input_label = QtGui.QLabel('git grep')
        self.input_label.setFont(diff_font())

        self.input_txt = HintedLineEdit(N_('command-line arguments'), self)
        self.input_txt.hint.enable(True)

        self.regexp_combo = combo = QtGui.QComboBox()
        combo.setToolTip(N_('Choose the "git grep" regular expression mode'))
        items = [N_('Basic Regexp'), N_('Extended Regexp'), N_('Fixed String')]
        combo.addItems(items)
        combo.setCurrentIndex(0)
        combo.setEditable(False)
        combo.setItemData(0,
                N_('Search using a POSIX basic regular expression'),
                Qt.ToolTipRole)
        combo.setItemData(1,
                N_('Search using a POSIX extended regular expression'),
                Qt.ToolTipRole)
        combo.setItemData(2,
                N_('Search for a fixed string'),
                Qt.ToolTipRole)
        combo.setItemData(0, '--basic-regexp', Qt.UserRole)
        combo.setItemData(1, '--extended-regexp', Qt.UserRole)
        combo.setItemData(2, '--fixed-strings', Qt.UserRole)

        self.result_txt = GrepTextView(N_('grep result...'), self)
        self.result_txt.hint.enable(True)

        self.edit_button = QtGui.QPushButton(N_('Edit'))
        self.edit_button.setIcon(qtutils.open_file_icon())
        self.edit_button.setEnabled(False)
        qtutils.button_action(self.edit_button, self.edit_action)

        self.refresh_button = QtGui.QPushButton(N_('Refresh'))
        self.refresh_button.setIcon(qtutils.reload_icon())
        self.refresh_button.setEnabled(False)
        qtutils.button_action(self.refresh_button, self.refresh_action)

        self.shell_checkbox = QtGui.QCheckBox(N_('Shell arguments'))
        self.shell_checkbox.setToolTip(
                N_('Parse arguments using a shell.\n'
                   'Queries with spaces will require "double quotes".'))
        self.shell_checkbox.setChecked(False)

        self.close_button = QtGui.QPushButton(N_('Close'))

        self.input_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                         self.input_label, self.input_txt,
                                         self.regexp_combo)

        self.bottom_layout = qtutils.hbox(defs.no_margin, defs.button_spacing,
                                          self.edit_button, self.refresh_button,
                                          self.shell_checkbox, qtutils.STRETCH,
                                          self.close_button)

        self.mainlayout = qtutils.vbox(defs.margin, defs.no_spacing,
                                       self.input_layout, self.result_txt,
                                       self.bottom_layout)
        self.setLayout(self.mainlayout)

        self.worker_thread = GrepThread(self)
        self.connect(self.worker_thread,
                     SIGNAL('result(PyQt_PyObject,PyQt_PyObject,PyQt_PyObject)'),
                     self.process_result, Qt.QueuedConnection)

        self.connect(self.input_txt, SIGNAL('textChanged(QString)'),
                     lambda s: self.search())

        self.connect(self.regexp_combo, SIGNAL('currentIndexChanged(int)'),
                     lambda x: self.search())

        self.connect(self.result_txt, SIGNAL('leave()'),
                     lambda: self.input_txt.setFocus())

        qtutils.add_action(self.input_txt, 'Focus Results', self.focus_results,
                           Qt.Key_Down, Qt.Key_Enter, Qt.Key_Return)
        qtutils.add_action(self, 'Focus Input', self.focus_input, 'Ctrl+L')

        qtutils.connect_toggle(self.shell_checkbox, lambda x: self.search())
        qtutils.connect_button(self.close_button, self.close)
        qtutils.add_close_action(self)

        if not self.restore_state():
            width, height = qtutils.default_size(parent, 666, 420)
            self.resize(width, height)

    def focus_input(self):
        self.input_txt.setFocus()
        self.input_txt.selectAll()

    def focus_results(self):
        self.result_txt.setFocus()

    def done(self, exit_code):
        self.save_state()
        return Dialog.done(self, exit_code)

    def regexp_mode(self):
        idx = self.regexp_combo.currentIndex()
        data = self.regexp_combo.itemData(idx, Qt.UserRole).toPyObject()
        return ustr(data)

    def search(self):
        self.edit_action.setEnabled(False)
        self.edit_button.setEnabled(False)
        self.refresh_action.setEnabled(False)
        self.refresh_button.setEnabled(False)
        query = self.input_txt.value()
        if len(query) < 2:
            self.result_txt.set_value('')
            return
        self.worker_thread.query = query
        self.worker_thread.shell = self.shell_checkbox.isChecked()
        self.worker_thread.regexp_mode = self.regexp_mode()
        self.worker_thread.start()

    def search_for(self, txt):
        self.input_txt.set_value(txt)

    def text_scroll(self):
        scrollbar = self.result_txt.verticalScrollBar()
        if scrollbar:
            return scrollbar.value()
        return None

    def set_text_scroll(self, scroll):
        scrollbar = self.result_txt.verticalScrollBar()
        if scrollbar and scroll is not None:
            scrollbar.setValue(scroll)

    def text_offset(self):
        return self.result_txt.textCursor().position()

    def set_text_offset(self, offset):
        cursor = self.result_txt.textCursor()
        cursor.setPosition(offset)
        self.result_txt.setTextCursor(cursor)

    def process_result(self, status, out, err):

        if status == 0:
            value = out + err
        elif out + err:
            value = 'git grep: ' + out + err
        else:
            value = ''

        # save scrollbar and text cursor
        scroll = self.text_scroll()
        offset = min(len(value), self.text_offset())

        self.result_txt.set_value(value)
        # restore
        self.set_text_scroll(scroll)
        self.set_text_offset(offset)

        enabled = status == 0
        self.edit_action.setEnabled(enabled)
        self.edit_button.setEnabled(enabled)
        self.refresh_button.setEnabled(True)
        self.refresh_action.setEnabled(True)

    def edit(self):
        goto_grep(self.result_txt.selected_line()),


class GrepTextView(VimHintedTextView):

    def __init__(self, hint, parent):
        VimHintedTextView.__init__(self, hint=hint, parent=parent)

        self.goto_action = qtutils.add_action(self, 'Launch Editor', self.edit)
        self.goto_action.setShortcut(cmds.Edit.SHORTCUT)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu(event.pos())
        menu.addSeparator()
        menu.addAction(self.goto_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def edit(self):
        goto_grep(self.selected_line())
