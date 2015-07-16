from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt, SIGNAL

from cola import qtutils
from cola.compat import ustr
from cola.i18n import N_
from cola.models import prefs
from cola.widgets import defs


class BasicLineEdit(QtGui.QLineEdit):

    def __init__(self, parent=None, row=1):
        QtGui.QLineEdit.__init__(self, parent)
        self._row = row
        self.connect(self, SIGNAL('cursorPositionChanged(int,int)'),
                     lambda old, new: self.emit_position())

    def set_value(self, value):
        self.setText(value)

    def as_unicode(self):
        return ustr(self.text())

    def strip(self):
        return self.as_unicode().strip()

    def value(self):
        return self.strip()

    def reset_cursor(self):
        self.setCursorPosition(0)

    def emit_position(self):
        row = self._row
        col = self.cursorPosition()
        self.emit(SIGNAL('cursorPosition(int,int)'), row, col)


class BasicTextEdit(QtGui.QTextEdit):

    def __init__(self, parent=None):
        QtGui.QTextEdit.__init__(self, parent)
        self._tabwidth = 8
        self.setMinimumSize(QtCore.QSize(1, 1))
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.setAcceptRichText(False)
        self.setCursorWidth(2)

        self.connect(self, SIGNAL('cursorPositionChanged()'),
                     self.emit_position)

    def as_unicode(self):
        return ustr(self.toPlainText())

    def strip(self):
        return self.as_unicode().strip()

    def value(self):
        return self.strip()

    def set_value(self, value):
        self.setPlainText(value)

    def reset_cursor(self):
        cursor = self.textCursor()
        cursor.setPosition(0)
        self.setTextCursor(cursor)

    def tabwidth(self):
        return self._tabwidth

    def set_tabwidth(self, width):
        self._tabwidth = width
        font = self.font()
        fm = QtGui.QFontMetrics(font)
        pixels = fm.width('M' * width)
        self.setTabStopWidth(pixels)

    def set_textwidth(self, width):
        font = self.font()
        fm = QtGui.QFontMetrics(font)
        pixels = fm.width('M' * (width + 1)) + 1
        self.setLineWrapColumnOrWidth(pixels)

    def set_linebreak(self, brk):
        if brk:
            wrapmode = QtGui.QTextEdit.FixedPixelWidth
        else:
            wrapmode = QtGui.QTextEdit.NoWrap
        self.setLineWrapMode(wrapmode)

    def selected_line(self):
        cursor = self.textCursor()
        offset = cursor.position()
        contents = ustr(self.toPlainText())
        while (offset >= 1
                and contents[offset-1]
                and contents[offset-1] != '\n'):
            offset -= 1
        data = contents[offset:]
        if '\n' in data:
            line, rest = data.split('\n', 1)
        else:
            line = data
        return line

    def emit_position(self):
        cursor = self.textCursor()
        position = cursor.position()
        txt = self.as_unicode()
        before = txt[:position]
        row = before.count('\n')
        line = before.split('\n')[row]
        col = cursor.columnNumber()
        col += line[:col].count('\t') * (self.tabwidth() - 1)
        self.emit(SIGNAL('cursorPosition(int,int)'), row+1, col)

    def mousePressEvent(self, event):
        # Move the text cursor so that the right-click events operate
        # on the current position, not the last left-clicked position.
        if event.button() == Qt.RightButton:
            if not self.textCursor().hasSelection():
                self.setTextCursor(self.cursorForPosition(event.pos()))
        QtGui.QTextEdit.mousePressEvent(self, event)


class MonoTextEdit(BasicTextEdit):

    def __init__(self, parent):
        BasicTextEdit.__init__(self, parent)
        self.setFont(qtutils.diff_font())
        self.set_tabwidth(prefs.tabwidth())


class MonoTextView(MonoTextEdit):

    def __init__(self, parent):
        MonoTextEdit.__init__(self, parent)
        self.setAcceptDrops(False)
        self.setTabChangesFocus(True)
        self.setUndoRedoEnabled(False)
        self.setTextInteractionFlags(Qt.TextSelectableByKeyboard |
                                     Qt.TextSelectableByMouse)


class HintedTextWidgetEventFilter(QtCore.QObject):

    def __init__(self, parent):
        QtCore.QObject.__init__(self, parent)
        self.widget = parent

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.FocusIn:
            widget = self.widget
            widget.emit_position()
            if widget.is_hint():
                widget.enable_hint(False)

        elif event.type() == QtCore.QEvent.FocusOut:
            widget = self.widget
            if not bool(widget.value()):
                widget.enable_hint(True)

        return False


class HintedTextWidgetMixin(object):

    def __init__(self, hint):
        self._hint = hint
        self._event_filter = HintedTextWidgetEventFilter(self)
        self.installEventFilter(self._event_filter)

        # Palette for normal text
        self.default_palette = QtGui.QPalette(self.palette())

        # Palette used for the placeholder text
        self.hint_palette = pal = QtGui.QPalette(self.palette())
        color = self.hint_palette.text().color()
        color.setAlpha(128)
        pal.setColor(QtGui.QPalette.Active, QtGui.QPalette.Text, color)
        pal.setColor(QtGui.QPalette.Inactive, QtGui.QPalette.Text, color)

    def set_hint(self, hint):
        is_hint = self.is_hint()
        self._hint = hint
        if is_hint:
            self.enable_hint(True)

    def hint(self):
        return self._hint

    def is_hint(self):
        return self.strip() == self._hint

    def value(self):
        text = self.strip()
        if text == self._hint:
            return ''
        else:
            return text

    def enable_hint(self, hint):
        blocksignals = self.blockSignals(True)
        if hint:
            self.set_value(self.hint())
        else:
            self.clear()
        self.reset_cursor()
        self.blockSignals(blocksignals)
        self.enable_hint_palette(hint)

    def enable_hint_palette(self, hint):
        if hint:
            self.setPalette(self.hint_palette)
        else:
            self.setPalette(self.default_palette)

    def refresh_palette(self):
        self.enable_hint_palette(self.is_hint())


class HintedTextEdit(MonoTextEdit, HintedTextWidgetMixin):

    def __init__(self, hint, parent=None):
        MonoTextEdit.__init__(self, parent)
        HintedTextWidgetMixin.__init__(self, hint)
        # Refresh palettes when text changes
        self.connect(self, SIGNAL('textChanged()'), self.refresh_palette)


# The read-only variant.
class HintedTextView(MonoTextView, HintedTextWidgetMixin):

    def __init__(self, hint, parent=None):
        MonoTextView.__init__(self, parent)
        HintedTextWidgetMixin.__init__(self, hint)


# The vim-like read-only text view

class VimMixin(object):

    def __init__(self, base):
        self._base = base
        # Common vim/unix-ish keyboard actions
        self.add_navigation('Up', Qt.Key_K, shift=True)
        self.add_navigation('Down', Qt.Key_J, shift=True)
        self.add_navigation('Left', Qt.Key_H, shift=True)
        self.add_navigation('Right', Qt.Key_L, shift=True)
        self.add_navigation('WordLeft', Qt.Key_B)
        self.add_navigation('WordRight', Qt.Key_W)
        self.add_navigation('StartOfLine', Qt.Key_0)
        self.add_navigation('EndOfLine', Qt.Key_Dollar)

        qtutils.add_action(self, 'PageUp',
                           lambda: self.page(-self.height()//2),
                           Qt.ShiftModifier + Qt.Key_Shift)

        qtutils.add_action(self, 'PageDown',
                           lambda: self.page(self.height()//2),
                           Qt.Key_Space)

    def add_navigation(self, name, hotkey, shift=False):
        """Add a hotkey along with a shift-variant"""
        direction = getattr(QtGui.QTextCursor, name)
        qtutils.add_action(self, name,
                           lambda: self.move(direction), hotkey)
        if shift:
            qtutils.add_action(self, 'Shift'+name,
                               lambda: self.move(direction, True),
                               Qt.ShiftModifier+hotkey)

    def move(self, direction, select=False):
        cursor = self.textCursor()
        if select:
            mode = QtGui.QTextCursor.KeepAnchor
        else:
            mode = QtGui.QTextCursor.MoveAnchor
        if cursor.movePosition(direction, mode):
            self.set_text_cursor(cursor)

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

    def keyPressEvent(self, event):
        """Custom keyboard behaviors

        The leave() signal is emitted when `Up` is pressed and we're already
        at the beginning of the text.  This allows the parent widget to
        orchestrate some higher-level interaction, such as giving focus to
        another widget.

        When in the  middle of the first line and `Up` is pressed, the cursor
        is moved to the beginning of the line.

        """
        if event.key() == Qt.Key_Up:
            cursor = self.textCursor()
            position = cursor.position()
            if position == 0:
                # The cursor is at the beginning of the line.
                # Emit a signal so that the parent can e.g. change focus.
                self.emit(SIGNAL('leave()'))
            elif self.value()[:position].count('\n') == 0:
                # The cursor is in the middle of the first line of text.
                # We can't go up ~ jump to the beginning of the line.
                # Select the text if shift is pressed.
                if event.modifiers() & Qt.ShiftModifier:
                    mode = QtGui.QTextCursor.KeepAnchor
                else:
                    mode = QtGui.QTextCursor.MoveAnchor
                cursor.movePosition(QtGui.QTextCursor.StartOfLine, mode)
                self.setTextCursor(cursor)

        return self._base.keyPressEvent(self, event)


class VimHintedTextView(VimMixin, HintedTextView):

    def __init__(self, hint='', parent=None):
        HintedTextView.__init__(self, hint, parent=parent)
        VimMixin.__init__(self, HintedTextView)


class VimMonoTextView(VimMixin, MonoTextView):

    def __init__(self, parent=None):
        MonoTextView.__init__(self, parent)
        VimMixin.__init__(self, MonoTextView)


class HintedLineEdit(HintedTextWidgetMixin, BasicLineEdit):

    def __init__(self, hint='', parent=None):
        BasicLineEdit.__init__(self, parent)
        HintedTextWidgetMixin.__init__(self, hint)

        self.setFont(qtutils.diff_font())
        self.connect(self, SIGNAL('textChanged(QString)'),
                     lambda text: self.refresh_palette())


def text_dialog(text, title):
    """Show a wall of text in a dialog"""
    parent = qtutils.active_window()
    label = QtGui.QLabel(parent)
    label.setFont(qtutils.diff_font())
    label.setText(text)
    label.setTextInteractionFlags(Qt.NoTextInteraction)

    widget = QtGui.QDialog(parent)
    widget.setWindowModality(Qt.WindowModal)
    widget.setWindowTitle(title)

    layout = qtutils.hbox(defs.margin, defs.spacing, label)
    widget.setLayout(layout)

    qtutils.add_action(widget, N_('Close'), widget.accept,
                       Qt.Key_Question, Qt.Key_Enter, Qt.Key_Return)
    widget.show()
    return widget
