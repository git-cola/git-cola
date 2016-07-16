from __future__ import division, absolute_import, unicode_literals

from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import hotkeys
from .. import qtutils
from ..i18n import N_
from ..models import prefs
from . import defs


def get_stripped(widget):
    return widget.get().strip()


class LineEdit(QtWidgets.QLineEdit):

    cursor_changed = Signal(int, int)

    def __init__(self, parent=None, row=1, get_value=None):
        QtWidgets.QLineEdit.__init__(self, parent)
        self._row = row
        if get_value is None:
            get_value = get_stripped
        self._get_value = get_value
        self.cursor_position = LineEditCursorPosition(self, row)

    def get(self):
        """Return the raw unicode value from Qt"""
        return self.text()

    def value(self):
        """Return the processed value, e.g. stripped"""
        return self._get_value(self)

    def set_value(self, value, block=False):
        if block:
            blocksig = self.blockSignals(True)
        pos = self.cursorPosition()
        self.setText(value)
        self.setCursorPosition(pos)
        if block:
            self.blockSignals(blocksig)

    def reset_cursor(self):
        self.setCursorPosition(0)


class LineEditCursorPosition(object):
    """Translate cursorPositionChanged(int,int) into cursorPosition(int,int)
    """
    def __init__(self, widget, row):
        self._widget = widget
        self._row = row
        # Translate cursorPositionChanged into cursor_changed(int, int)
        widget.cursorPositionChanged.connect(lambda old, new: self.emit())

    def emit(self):
        widget = self._widget
        row = self._row
        col = widget.cursorPosition()
        widget.cursor_changed.emit(row, col)

    def reset(self):
        self._widget.setCursorPosition(0)


class TextEdit(QtWidgets.QTextEdit):

    cursor_changed = Signal(int, int)
    leave = Signal()

    def __init__(self, parent=None, get_value=None):
        QtWidgets.QTextEdit.__init__(self, parent)
        self.cursor_position = TextEditCursorPosition(self)
        if get_value is None:
            get_value = get_stripped
        self._get_value = get_value
        self._tabwidth = 8
        self.setMinimumSize(QtCore.QSize(1, 1))
        self.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self.setAcceptRichText(False)
        self.setCursorWidth(defs.cursor_width)

    def get(self):
        """Return the raw unicode value from Qt"""
        return self.toPlainText()

    def value(self):
        """Return a safe value, e.g. a stripped value"""
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
            wrapmode = QtWidgets.QTextEdit.FixedPixelWidth
        else:
            wrapmode = QtWidgets.QTextEdit.NoWrap
        self.setLineWrapMode(wrapmode)

    def selected_line(self):
        cursor = self.textCursor()
        offset = cursor.position()
        contents = self.toPlainText()
        while (offset >= 1 and
                contents[offset-1] and
                contents[offset-1] != '\n'):
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
        QtWidgets.QTextEdit.mousePressEvent(self, event)


class TextEditCursorPosition(object):

    def __init__(self, widget):
        self._widget = widget
        widget.cursorPositionChanged.connect(self.emit)

    def emit(self):
        widget = self._widget
        cursor = widget.textCursor()
        position = cursor.position()
        txt = widget.get()
        before = txt[:position]
        row = before.count('\n')
        line = before.split('\n')[row]
        col = cursor.columnNumber()
        col += line[:col].count('\t') * (widget.tabwidth() - 1)
        widget.cursor_changed.emit(row+1, col)

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
    text = get_stripped(widget)
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
        self._is_error = False
        widget.installEventFilter(self)

        # Palette for normal text
        QPalette = QtGui.QPalette
        self.default_palette = QPalette(widget.palette())

        # Palette used for the placeholder text
        self.hint_palette = pal = QPalette(widget.palette())
        color = self.hint_palette.text().color()
        color.setAlpha(128)
        pal.setColor(QPalette.Active, QPalette.Text, color)
        pal.setColor(QPalette.Inactive, QPalette.Text, color)

        # Palette for error text
        self.error_palette = pal = QPalette(widget.palette())
        color = QtGui.QColor(Qt.red)
        color.setAlpha(200)
        pal.setColor(QPalette.Active, QPalette.Text, color)
        pal.setColor(QPalette.Inactive, QPalette.Text, color)

    def widget(self):
        """Return the parent text widget"""
        return self._widget

    def active(self):
        """Return True when hint-mode is active"""
        return self.value() == get_stripped(self._widget)

    def value(self):
        """Return the current hint text"""
        return self._hint

    def set_error(self, is_error):
        """Enable/disable error mode"""
        self._is_error = is_error
        self.refresh()

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
        self._update_palette(hint)

    def refresh(self):
        """Update the palette to match the current mode"""
        self._update_palette(self.active())

    def _update_palette(self, hint):
        """Update to palette for normal/error/hint mode"""
        if self._is_error:
            self._widget.setPalette(self.error_palette)
        else:
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
        self.textChanged.connect(self.hint.refresh)


# The read-only variant.
class HintedTextView(HintedTextEdit):

    def __init__(self, hint, parent=None):
        HintedTextEdit.__init__(self, hint, parent=parent)
        setup_readonly_flags(self)


# The vim-like read-only text view

class VimMixin(object):

    def __init__(self, widget):
        self.widget = widget
        self.Base = widget.Base
        # Common vim/unix-ish keyboard actions
        self.add_navigation('Up', hotkeys.MOVE_UP,
                            shift=hotkeys.MOVE_UP_SHIFT)
        self.add_navigation('Down', hotkeys.MOVE_DOWN,
                            shift=hotkeys.MOVE_DOWN_SHIFT)
        self.add_navigation('Left', hotkeys.MOVE_LEFT,
                            shift=hotkeys.MOVE_LEFT_SHIFT)
        self.add_navigation('Right', hotkeys.MOVE_RIGHT,
                            shift=hotkeys.MOVE_RIGHT_SHIFT)
        self.add_navigation('WordLeft', hotkeys.WORD_LEFT)
        self.add_navigation('WordRight', hotkeys.WORD_RIGHT)
        self.add_navigation('StartOfLine', hotkeys.START_OF_LINE)
        self.add_navigation('EndOfLine', hotkeys.END_OF_LINE)

        qtutils.add_action(widget, 'PageUp',
                           lambda: widget.page(-widget.height()//2),
                           hotkeys.SECONDARY_ACTION)

        qtutils.add_action(widget, 'PageDown',
                           lambda: widget.page(widget.height()//2),
                           hotkeys.PRIMARY_ACTION)

    def add_navigation(self, name, hotkey, shift=None):
        """Add a hotkey along with a shift-variant"""
        widget = self.widget
        direction = getattr(QtGui.QTextCursor, name)
        qtutils.add_action(widget, name,
                           lambda: self.move(direction), hotkey)
        if shift:
            qtutils.add_action(widget, 'Shift' + name,
                               lambda: self.move(direction, True), shift)

    def move(self, direction, select=False, n=1):
        widget = self.widget
        cursor = widget.textCursor()
        if select:
            mode = QtGui.QTextCursor.KeepAnchor
        else:
            mode = QtGui.QTextCursor.MoveAnchor
        if cursor.movePosition(direction, mode, n):
            self.set_text_cursor(cursor)

    def page(self, offset):
        widget = self.widget
        rect = widget.cursorRect()
        x = rect.x()
        y = rect.y() + offset
        new_cursor = widget.cursorForPosition(QtCore.QPoint(x, y))
        if new_cursor is not None:
            self.set_text_cursor(new_cursor)

    def set_text_cursor(self, cursor):
        widget = self.widget
        widget.setTextCursor(cursor)
        widget.ensureCursorVisible()
        widget.viewport().update()

    def keyPressEvent(self, event):
        """Custom keyboard behaviors

        The leave() signal is emitted when `Up` is pressed and we're already
        at the beginning of the text.  This allows the parent widget to
        orchestrate some higher-level interaction, such as giving focus to
        another widget.

        When in the  middle of the first line and `Up` is pressed, the cursor
        is moved to the beginning of the line.

        """
        widget = self.widget
        if event.key() == Qt.Key_Up:
            cursor = widget.textCursor()
            position = cursor.position()
            if position == 0:
                # The cursor is at the beginning of the line.
                # Emit a signal so that the parent can e.g. change focus.
                widget.leave.emit()
            elif widget.value()[:position].count('\n') == 0:
                # The cursor is in the middle of the first line of text.
                # We can't go up ~ jump to the beginning of the line.
                # Select the text if shift is pressed.
                if event.modifiers() & Qt.ShiftModifier:
                    mode = QtGui.QTextCursor.KeepAnchor
                else:
                    mode = QtGui.QTextCursor.MoveAnchor
                cursor.movePosition(QtGui.QTextCursor.StartOfLine, mode)
                widget.setTextCursor(cursor)

        return self.Base.keyPressEvent(widget, event)


class VimHintedTextView(HintedTextView):
    Base = HintedTextView
    Mixin = VimMixin

    def __init__(self, hint='', parent=None):
        super(VimHintedTextView, self).__init__(hint, parent=parent)
        self._mixin = self.Mixin(self)

    def move(self, direction, select=False, n=1):
        return self._mixin.page(direction, select=select, n=n)

    def page(self, offset):
        return self._mixin.page(offset)

    def keyPressEvent(self, event):
        return self._mixin.keyPressEvent(event)


class VimMonoTextView(MonoTextView):
    Base = MonoTextView
    Mixin = VimMixin

    def __init__(self, parent=None):
        MonoTextView.__init__(self, parent)
        self._mixin = self.Mixin(self)

    def move(self, direction, select=False, n=1):
        return self._mixin.page(direction, select=select, n=n)

    def page(self, offset):
        return self._mixin.page(offset)

    def keyPressEvent(self, event):
        return self._mixin.keyPressEvent(event)


class HintedLineEdit(LineEdit):

    def __init__(self, hint='', parent=None):
        LineEdit.__init__(self, parent=parent, get_value=get_value_hinted)
        self.hint = HintWidget(self, hint)
        self.setFont(qtutils.diff_font())
        self.textChanged.connect(lambda text: self.hint.refresh())


def text_dialog(text, title):
    """Show a wall of text in a dialog"""
    parent = qtutils.active_window()
    label = QtWidgets.QLabel(parent)
    label.setFont(qtutils.diff_font())
    label.setText(text)
    label.setTextInteractionFlags(Qt.NoTextInteraction)

    widget = QtWidgets.QDialog(parent)
    widget.setWindowModality(Qt.WindowModal)
    widget.setWindowTitle(title)

    layout = qtutils.hbox(defs.margin, defs.spacing, label)
    widget.setLayout(layout)

    qtutils.add_action(widget, N_('Close'), widget.accept,
                       Qt.Key_Question, Qt.Key_Enter, Qt.Key_Return)
    widget.show()
    return widget
