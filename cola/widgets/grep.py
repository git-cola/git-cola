from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL

from cola import core
from cola import guicmds
from cola import utils
from cola import qtutils
from cola.git import git
from cola.prefs import diff_font
from cola.widgets import defs
from cola.widgets.standard import Dialog
from cola.widgets.text import HintedTextView, HintedLineEdit


class GrepThread(QtCore.QThread):
    def __init__(self, parent):
        QtCore.QThread.__init__(self, parent)
        self.txt = None
        self.shell = False

    def run(self):
        if self.txt is None:
            return
        query = self.txt

        if self.shell:
            args = utils.shell_split(query)
        else:
            args = [query]
        status, out = git.grep(with_status=True, with_stderr=True,
                               n=True, *args)
        if query == self.txt:
            self.emit(SIGNAL('result'), status, core.decode(out))
        else:
            self.run()


class Grep(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent)
        self.setAttribute(Qt.WA_MacMetalStyle)
        self.setWindowModality(Qt.WindowModal)

        self.input_label = QtGui.QLabel('git grep')
        self.input_label.setFont(diff_font())

        hint = 'command-line arguments'
        self.input_txt = GrepLineEdit(hint, self)
        self.input_txt.enable_hint(True)

        hint = 'grep result...'
        self.result_txt = GrepTextView(hint, self)
        self.result_txt.enable_hint(True)

        self.edit_button = QtGui.QPushButton(self.tr('Edit'))
        self.edit_button.setIcon(qtutils.open_file_icon())
        self.edit_button.setEnabled(False)
        self.edit_button.setShortcut(defs.editor_shortcut)

        self.shell_checkbox = QtGui.QCheckBox(self.tr('Shell arguments'))
        self.shell_checkbox.setToolTip(
                'Parse arguments using a shell.\n'
                'Queries with spaces will require "double quotes".')
        self.shell_checkbox.setChecked(False)

        self.close_button = QtGui.QPushButton(self.tr('Close'))

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

        self.bottom_layout.addWidget(self.edit_button)
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
                     self.input_txt_changed)

        self.connect(self.input_txt, SIGNAL('returnPressed()'),
                     lambda: self.result_txt.setFocus())

        qtutils.connect_button(self.edit_button, self.edit)
        qtutils.connect_button(self.close_button, self.close)
        qtutils.add_close_action(self)

        if not qtutils.apply_state(self):
            self.resize(666, 420)

    def done(self, exit_code):
        qtutils.save_state(self)
        return Dialog.done(self, exit_code)

    def input_txt_changed(self, txt):
        has_query = len(unicode(txt)) > 1
        if has_query:
            self.search()

    def search(self):
        self.edit_button.setEnabled(False)

        self.grep_thread.txt = self.input_txt.as_unicode()
        self.grep_thread.shell = self.shell_checkbox.isChecked()
        self.grep_thread.start()

    def search_for(self, txt):
        self.input_txt.set_value(txt)
        self.run()

    def process_result(self, status, out):
        self.result_txt.set_value(out)
        self.edit_button.setEnabled(status == 0)

    def edit(self):
        guicmds.goto_grep(self.result_txt.selected_line()),


class GrepLineEdit(HintedLineEdit):
    def __init__(self, hint, parent):
        HintedLineEdit.__init__(self, hint, parent)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.emit(SIGNAL('returnPressed()'))
        else:
            HintedLineEdit.keyPressEvent(self, event)


class GrepTextView(HintedTextView):
    def __init__(self, hint, parent):
        HintedTextView.__init__(self, hint, parent)
        self.goto_action = qtutils.add_action(
                self, 'Launch Editor',
                lambda: guicmds.goto_grep(self.selected_line()))
        self.goto_action.setShortcut(defs.editor_shortcut)

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


def run_grep(txt=None, parent=None):
    widget = Grep(parent)
    if txt is not None:
        widget.search_for(txt)
    return widget
