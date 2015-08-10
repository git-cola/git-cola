from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt, SIGNAL

from cola import qtutils
from cola.compat import ustr
from cola.i18n import N_
from cola.models import prefs
from cola.widgets import defs


def get_value_stripped(widget):
    return widget.as_unicode().strip()


class LineEdit(QtGui.QLineEdit):

    def __init__(self, parent=None, row=1, get_value=None):
        QtGui.QLineEdit.__init__(self, parent)
        self._row = row
        if get_value is None:
            get_value = get_value_stripped
        self._get_value = get_value
        self.cursor_position = LineEditCursorPosition(self, row)

    def value(self):
        return self._get_value(self)

    def set_value(self, value, block=False):
        if block:
            blocksig = self.blockSignals(True)
        pos = self.cursorPosition()
        self.setText(value)
        self.setCursorPosition(pos)
        if block:
            self.blockSignals(blocksig)

    def as_unicode(self):
        return ustr(self.text())

    def reset_cursor(self):
        self.setCursorPosition(0)


class LineEditCursorPosition(object):
    """Translate cursorPositionChanged(int,int) into cursorPosition(int,int)
    """
    def __init__(self, widget, row):
        self._widget = widget
        self._row = row
        # Translate cursorPositionChanged into cursorPosition
        widget.connect(widget, SIGNAL('cursorPositionChanged(int,int)'),
                       lambda old, new: self.emit())

    def emit(self):
        widget = self._widget
        row = self._row
        col = widget.cursorPosition()
        widget.emit(SIGNAL('cursorPosition(int,int)'), row, col)

    def reset(self):
        self._widget.setCursorPosition(0)


class TextEdit(QtGui.QTextEdit):

    def __init__(self, parent=None, get_value=None):
        QtGui.QTextEdit.__init__(self, parent)
        self.cursor_position = TextEditCursorPosition(self)
        if get_value is None:
            get_value = get_value_stripped
        self._get_value = get_value
        self._tabwidth = 8
        self.setMinimumSize(QtCore.QSize(1, 1))
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.setAcceptRichText(False)
        self.setCursorWidth(2)

    def as_unicode(self):
        return ustr(self.toPlainText())

    def value(self):
        return self._get_value(self)

    def set_value(self, value, block=False):
        if block:
            blocksig = self.blockSignals(True)
        cursor = self.textCursor()
        self.setPlainText(value)
        self.setTextCursor(cursor)
        if block:
            self.blockSignals(blocksig)

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

    def mousePressEvent(self, event):
        # Move the text cursor so that the right-click events operate
        # on the current position, not the last left-clicked position.
        if event.button() == Qt.RightButton:
            if not self.textCursor().hasSelection():
                self.setTextCursor(self.cursorForPosition(event.pos()))
        QtGui.QTextEdit.mousePressEvent(self, event)


class TextEditCursorPosition(object):

    def __init__(self, widget):
        self._widget = widget
        widget.connect(widget, SIGNAL('cursorPositionChanged()'), self.emit)

    def emit(self):
        widget = self._widget
        cursor = widget.textCursor()
        position = cursor.position()
        txt = widget.as_unicode()
        before = txt[:position]
        row = before.count('\n')
        line = before.split('\n')[row]
        col = cursor.columnNumber()
        col += line[:col].count('\t') * (widget.tabwidth() - 1)
        widget.emit(SIGNAL('cursorPosition(int,int)'), row+1, col)

    def reset(self):
        widget = self._widget
        cursor = widget.textCursor()
        cursor.setPosition(0)
        widget.setTextCursor(cursor)


def setup_mono_font(widget):
    widget.setFont(qtutils.diff_font())
    widget.set_tabwidth(prefs.tabwidth())


def setup_readonly_flags(widget):
    widget.setAcceptDrops(False)
    widget.setTabChangesFocus(True)
    widget.setUndoRedoEnabled(False)
    widget.setTextInteractionFlags(Qt.TextSelectableByKeyboard |
                                   Qt.TextSelectableByMouse)


class MonoTextEdit(TextEdit):

    def __init__(self, parent):
        TextEdit.__init__(self, parent)
        setup_mono_font(self)


class MonoTextView(MonoTextEdit):

    def __init__(self, parent):
        MonoTextEdit.__init__(self, parent)
        setup_readonly_flags(self)


def get_value_hinted(widget):
    text = get_value_stripped(widget)
    hint = widget.hint.value()
    if text == hint:
        return ''
    else:
        return text


class HintWidget(QtCore.QObject):
    """Extend a widget to provide hint messages"""

    def __init__(self, widget, hint):
        QtCore.QObject.__init__(self, widget)
        self._widget = widget
        self._hint = hint
        widget.installEventFilter(self)

        # Palette for normal text
        self.default_palette = QtGui.QPalette(widget.palette())

        # Palette used for the placeholder text
        self.hint_palette = pal = QtGui.QPalette(widget.palette())
        color = self.hint_palette.text().color()
        color.setAlpha(128)
        pal.setColor(QtGui.QPalette.Active, QtGui.QPalette.Text, color)
        pal.setColor(QtGui.QPalette.Inactive, QtGui.QPalette.Text, color)

    def widget(self):
        """Return the parent text widget"""
        return self._widget

    def active(self):
        """Return True when hint-mode is active"""
        return self.value() == get_value_stripped(self._widget)

    def value(self):
        """Return the current hint text"""
        return self._hint

    def set_value(self, hint):
        """Change the hint text"""
        # If hint-mode is currently active, re-activate it with the new text
        active = self.active()
        self._hint = hint
        if active or self.active():
            self.enable(True)

    def enable(self, hint):
        """Enable/disable hint-mode"""
        if hint:
            self._widget.set_value(self.value(), block=True)
            self._widget.cursor_position.reset()
        else:
            self._widget.clear()
        self._enable_hint_palette(hint)

    def refresh(self):
        """Update the palette to match the current mode"""
        self._enable_hint_palette(self.active())

    def _enable_hint_palette(self, hint):
        """Enable/disable the hint-mode palette"""
        if hint:
            self._widget.setPalette(self.hint_palette)
        else:
            self._widget.setPalette(self.default_palette)

    def eventFilter(self, obj, event):
        """Enable/disable hint-mode when focus changes"""
        etype = event.type()
        if etype == QtCore.QEvent.FocusIn:
            self._widget.hint.focus_in()
        elif etype == QtCore.QEvent.FocusOut:
            self._widget.hint.focus_out()
        return False

    def focus_in(self):
        """Disable hint-mode when focused"""
        widget = self.widget()
        if self.active():
            self.enable(False)
        widget.cursor_position.emit()

    def focus_out(self):
        """Re-enable hint-mode when losing focus"""
        widget = self.widget()
        if not bool(widget.value()):
            self.enable(True)


class HintedTextEdit(TextEdit):

    def __init__(self, hint, parent=None):
        TextEdit.__init__(self, parent=parent, get_value=get_value_hinted)
        self.hint = HintWidget(self, hint)
        setup_mono_font(self)
        # Refresh palettes when text changes
        self.connect(self, SIGNAL('textChanged()'), self.hint.refresh)


# The read-only variant.
class HintedTextView(HintedTextEdit):

    def __init__(self, hint, parent=None):
        HintedTextEdit.__init__(self, hint, parent=parent)
        setup_readonly_flags(self)


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
                           Qt.ShiftModifier + Qt.Key_Space)

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

    def move(self, direction, select=False, n=1):
        cursor = self.textCursor()
        if select:
            mode = QtGui.QTextCursor.KeepAnchor
        else:
            mode = QtGui.QTextCursor.MoveAnchor
        if cursor.movePosition(direction, mode, n):
            self.set_text_cursor(cursor)

    def page(self, offset):
        rect = self.cursorRect()
        x = rect.x()
        y = max(0, rect.y() + offset)
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


class HintedLineEdit(LineEdit):

    def __init__(self, hint='', parent=None):
        LineEdit.__init__(self, parent=parent, get_value=get_value_hinted)
        self.hint = HintWidget(self, hint)
        self.setFont(qtutils.diff_font())
        self.connect(self, SIGNAL('textChanged(QString)'),
                     lambda text: self.hint.refresh())


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
