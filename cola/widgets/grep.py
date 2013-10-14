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
from cola.widgets.text import HintedTextView, HintedLineEdit


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
            self.emit(SIGNAL('result'), status, out, err)
        else:
            self.run()


class Grep(Dialog):

    def __init__(self, parent):
        Dialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowModality(Qt.WindowModal)
        self.setWindowTitle(N_('Search'))

        self.input_label = QtGui.QLabel('git grep')
        self.input_label.setFont(diff_font())

        self.input_txt = HintedLineEdit(N_('command-line arguments'), self)
        self.input_txt.enable_hint(True)

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
        self.result_txt.enable_hint(True)

        self.edit_button = QtGui.QPushButton(N_('Edit'))
        self.edit_button.setIcon(qtutils.open_file_icon())
        self.edit_button.setEnabled(False)
        self.edit_button.setShortcut(cmds.Edit.SHORTCUT)

        self.refresh_button = QtGui.QPushButton(N_('Refresh'))
        self.refresh_button.setIcon(qtutils.reload_icon())
        self.refresh_button.setShortcut(QtGui.QKeySequence.Refresh)

        self.shell_checkbox = QtGui.QCheckBox(N_('Shell arguments'))
        self.shell_checkbox.setToolTip(
                N_('Parse arguments using a shell.\n'
                   'Queries with spaces will require "double quotes".'))
        self.shell_checkbox.setChecked(False)

        self.close_button = QtGui.QPushButton(N_('Close'))

        self.input_layout = QtGui.QHBoxLayout()
        self.input_layout.setMargin(0)
        self.input_layout.setSpacing(defs.button_spacing)

        self.bottom_layout = QtGui.QHBoxLayout()
        self.bottom_layout.setMargin(0)
        self.bottom_layout.setSpacing(defs.button_spacing)

        self.mainlayout = QtGui.QVBoxLayout()
        self.mainlayout.setMargin(defs.margin)
        self.mainlayout.setSpacing(defs.spacing)

        self.input_layout.addWidget(self.input_label)
        self.input_layout.addWidget(self.input_txt)
        self.input_layout.addWidget(self.regexp_combo)

        self.bottom_layout.addWidget(self.edit_button)
        self.bottom_layout.addWidget(self.refresh_button)
        self.bottom_layout.addWidget(self.shell_checkbox)
        self.bottom_layout.addStretch()
        self.bottom_layout.addWidget(self.close_button)

        self.mainlayout.addLayout(self.input_layout)
        self.mainlayout.addWidget(self.result_txt)
        self.mainlayout.addLayout(self.bottom_layout)
        self.setLayout(self.mainlayout)

        self.grep_thread = GrepThread(self)

        self.connect(self.grep_thread, SIGNAL('result'),
                     self.process_result)

        self.connect(self.input_txt, SIGNAL('textChanged(QString)'),
                     lambda s: self.search())

        self.connect(self.regexp_combo, SIGNAL('currentIndexChanged(int)'),
                     lambda x: self.search())

        self.connect(self.result_txt, SIGNAL('leave()'),
                     lambda: self.input_txt.setFocus())

        qtutils.add_action(self.input_txt, 'FocusResults',
                           lambda: self.result_txt.setFocus(),
                           Qt.Key_Down, Qt.Key_Enter, Qt.Key_Return)
        qtutils.add_action(self, 'FocusSearch',
                           lambda: self.input_txt.setFocus(),
                           'Ctrl+l')
        qtutils.connect_button(self.edit_button, self.edit)
        qtutils.connect_button(self.refresh_button, self.search)
        qtutils.connect_toggle(self.shell_checkbox, lambda x: self.search())
        qtutils.connect_button(self.close_button, self.close)
        qtutils.add_close_action(self)

        if not qtutils.apply_state(self):
            self.resize(666, 420)

    def done(self, exit_code):
        qtutils.save_state(self)
        return Dialog.done(self, exit_code)

    def regexp_mode(self):
        idx = self.regexp_combo.currentIndex()
        data = self.regexp_combo.itemData(idx, Qt.UserRole).toPyObject()
        return unicode(data)

    def search(self):
        self.edit_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        query = self.input_txt.value()
        if len(query) < 2:
            self.result_txt.set_value('')
            return
        self.grep_thread.query = query
        self.grep_thread.shell = self.shell_checkbox.isChecked()
        self.grep_thread.regexp_mode = self.regexp_mode()
        self.grep_thread.start()

    def search_for(self, txt):
        self.input_txt.set_value(txt)
        self.search()

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

        self.edit_button.setEnabled(status == 0)
        self.refresh_button.setEnabled(status == 0)

    def edit(self):
        goto_grep(self.result_txt.selected_line()),


class GrepTextView(HintedTextView):

    def __init__(self, hint, parent):
        HintedTextView.__init__(self, hint, parent)
        self.goto_action = qtutils.add_action(self, 'Launch Editor', self.edit)
        self.goto_action.setShortcut(cmds.Edit.SHORTCUT)

        qtutils.add_action(self, 'Up',
                lambda: self.move(QtGui.QTextCursor.Up),
                Qt.Key_K)

        qtutils.add_action(self, 'Down',
                lambda: self.move(QtGui.QTextCursor.Down),
                Qt.Key_J)

        qtutils.add_action(self, 'Left',
                lambda: self.move(QtGui.QTextCursor.Left),
                Qt.Key_H)

        qtutils.add_action(self, 'Right',
                lambda: self.move(QtGui.QTextCursor.Right),
                Qt.Key_L)

        qtutils.add_action(self, 'StartOfLine',
                lambda: self.move(QtGui.QTextCursor.StartOfLine),
                Qt.Key_0)

        qtutils.add_action(self, 'EndOfLine',
                lambda: self.move(QtGui.QTextCursor.EndOfLine),
                Qt.Key_Dollar)

        qtutils.add_action(self, 'WordLeft',
                lambda: self.move(QtGui.QTextCursor.WordLeft),
                Qt.Key_B)

        qtutils.add_action(self, 'WordRight',
                lambda: self.move(QtGui.QTextCursor.WordRight),
                Qt.Key_W)

        qtutils.add_action(self, 'PageUp',
                lambda: self.page(-self.height()/2),
                'Shift+Space')

        qtutils.add_action(self, 'PageDown',
                lambda: self.page(self.height()/2),
                Qt.Key_Space)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu(event.pos())
        menu.addSeparator()
        menu.addAction(self.goto_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def edit(self):
        goto_grep(self.selected_line())

    def page(self, offset):
        rect = self.cursorRect()
        x = rect.x()
        y = rect.y() + offset
        new_cursor = self.cursorForPosition(QtCore.QPoint(x, y))
        if new_cursor is not None:
            self.set_text_cursor(new_cursor)

    def set_text_cursor(self, cursor):
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        self.viewport().update()

    def move(self, direction):
        cursor = self.textCursor()
        if cursor.movePosition(direction):
            self.set_text_cursor(cursor)

    def paintEvent(self, event):
        HintedTextView.paintEvent(self, event)
        if self.hasFocus():
            # Qt doesn't redraw the cursor when using movePosition().
            # So.. draw our own cursor.
            rect = self.cursorRect()
            painter = QtGui.QPainter(self.viewport())
            painter.fillRect(rect, Qt.SolidPattern)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            cursor = self.textCursor()
            position = cursor.position()
            if position == 0 and not cursor.hasSelection():
                # The cursor is at the beginning of the line.
                # If we have selection then simply reset the cursor.
                # Otherwise, emit a signal so that the parent can
                # change focus.
                self.emit(SIGNAL('leave()'))
        return HintedTextView.keyPressEvent(self, event)


def goto_grep(line):
    """Called when Search -> Grep's right-click 'goto' action."""
    filename, line_number, contents = line.split(':', 2)
    do(cmds.Edit, [filename], line_number=line_number)


def run_grep(text=None, parent=None):
    widget = Grep(parent)
    if text:
        widget.search_for(text)
    return widget
