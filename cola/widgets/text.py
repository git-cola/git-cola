"""Text widgets"""
from __future__ import division, absolute_import, unicode_literals
import math

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



class BaseTextEditExtension(QtCore.QObject):

    def __init__(self, widget, get_value, readonly):
        QtCore.QObject.__init__(self, widget)
        self.widget = widget
        self.cursor_position = TextEditCursorPosition(widget, self)
        if get_value is None:
            get_value = get_stripped
        self._get_value = get_value
        self._tabwidth = 8
        self._readonly = readonly
        self._init_flags()
        self.init()

    def _init_flags(self):
        widget = self.widget
        widget.setMinimumSize(QtCore.QSize(1, 1))
        widget.setWordWrapMode(QtGui.QTextOption.WordWrap)
        widget.setLineWrapMode(widget.NoWrap)
        widget.setCursorWidth(defs.cursor_width)
        if self._readonly:
            widget.setReadOnly(True)
            widget.setAcceptDrops(False)
            widget.setTabChangesFocus(True)
            widget.setUndoRedoEnabled(False)
            widget.setTextInteractionFlags(Qt.TextSelectableByKeyboard |
                                           Qt.TextSelectableByMouse)

    def get(self):
        """Return the raw unicode value from Qt"""
        return self.widget.toPlainText()

    def value(self):
        """Return a safe value, e.g. a stripped value"""
        return self._get_value(self.widget)

    def set_value(self, value, block=False):
        if block:
            blocksig = self.widget.blockSignals(True)

        # Save cursor position
        cursor = self.widget.textCursor()
        position = cursor.position()
        # Update text
        self.widget.setPlainText(value)
        # Restore cursor
        cursor = self.widget.textCursor()
        cursor.setPosition(min(position, cursor.position()))
        self.widget.setTextCursor(cursor)

        if block:
            self.widget.blockSignals(blocksig)

    def tabwidth(self):
        return self._tabwidth

    def set_tabwidth(self, width):
        self._tabwidth = width
        font = self.widget.font()
        fm = QtGui.QFontMetrics(font)
        pixels = fm.width('M' * width)
        self.widget.setTabStopWidth(pixels)

    def selected_line(self):
        contents = self.value()
        cursor = self.widget.textCursor()
        offset = min(cursor.position(), len(contents)-1)
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

    def mouse_press_event(self, event):
        # Move the text cursor so that the right-click events operate
        # on the current position, not the last left-clicked position.
        widget = self.widget
        if event.button() == Qt.RightButton:
            if not widget.textCursor().hasSelection():
                cursor = widget.cursorForPosition(event.pos())
                widget.setTextCursor(widget.cursorForPosition(event.pos()))

    # For extension by sub-classes

    def init(self):
        """Called during init for class-specific settings"""
        pass

    def set_textwidth(self, width):
        """Set the text width"""
        pass

    def set_linebreak(self, brk):
        """Enable word wrapping"""
        pass


class PlainTextEditExtension(BaseTextEditExtension):

    def set_linebreak(self, brk):
        if brk:
            wrapmode = QtWidgets.QPlainTextEdit.WidgetWidth
        else:
            wrapmode = QtWidgets.QPlainTextEdit.NoWrap
        self.widget.setLineWrapMode(wrapmode)


class PlainTextEdit(QtWidgets.QPlainTextEdit):

    cursor_changed = Signal(int, int)
    leave = Signal()

    def __init__(self, parent=None, get_value=None, readonly=False):
        QtWidgets.QPlainTextEdit.__init__(self, parent)
        self.ext = PlainTextEditExtension(self, get_value, readonly)
        self.cursor_position = self.ext.cursor_position

    def get(self):
        """Return the raw unicode value from Qt"""
        return self.ext.get()

    def value(self):
        """Return a safe value, e.g. a stripped value"""
        return self.ext.value()

    def set_value(self, value, block=False):
        self.ext.set_value(value, block=block)

    def selected_line(self):
        return self.ext.selected_line()

    def set_tabwidth(self, width):
        self.ext.set_tabwidth(width)

    def set_textwidth(self, width):
        self.ext.set_textwidth(width)

    def set_linebreak(self, brk):
        self.ext.set_linebreak(brk)

    def mousePressEvent(self, event):
        self.ext.mouse_press_event(event)
        super(PlainTextEdit, self).mousePressEvent(event)

    def wheelEvent(self, event):
        """Disable control+wheelscroll text resizing"""
        if event.modifiers() & Qt.ControlModifier:
            event.ignore()
            return
        return super(PlainTextEdit, self).wheelEvent(event)


class TextEditExtension(BaseTextEditExtension):

    def init(self):
        widget = self.widget
        widget.setAcceptRichText(False)

    def set_linebreak(self, brk):
        if brk:
            wrapmode = QtWidgets.QTextEdit.FixedColumnWidth
        else:
            wrapmode = QtWidgets.QTextEdit.NoWrap
        self.widget.setLineWrapMode(wrapmode)

    def set_textwidth(self, width):
        self.widget.setLineWrapColumnOrWidth(width)



class TextEdit(QtWidgets.QTextEdit):

    cursor_changed = Signal(int, int)
    leave = Signal()

    def __init__(self, parent=None, get_value=None, readonly=False):
        QtWidgets.QTextEdit.__init__(self, parent)
        self.ext = TextEditExtension(self, get_value, readonly)
        self.cursor_position = self.ext.cursor_position

    def get(self):
        """Return the raw unicode value from Qt"""
        return self.ext.get()

    def value(self):
        """Return a safe value, e.g. a stripped value"""
        return self.ext.value()

    def set_value(self, value, block=False):
        self.ext.set_value(value, block=block)

    def selected_line(self):
        return self.ext.selected_line()

    def set_tabwidth(self, width):
        self.ext.set_tabwidth(width)

    def set_textwidth(self, width):
        self.ext.set_textwidth(width)

    def set_linebreak(self, brk):
        self.ext.set_linebreak(brk)

    def mousePressEvent(self, event):
        self.ext.mouse_press_event(event)
        super(TextEdit, self).mousePressEvent(event)

    def wheelEvent(self, event):
        """Disable control+wheelscroll text resizing"""
        if event.modifiers() & Qt.ControlModifier:
            event.ignore()
            return
        return super(TextEdit, self).wheelEvent(event)


class TextEditCursorPosition(object):

    def __init__(self, widget, ext):
        self._widget = widget
        self._ext = ext
        widget.cursorPositionChanged.connect(self.emit)

    def emit(self):
        widget = self._widget
        ext = self._ext
        cursor = widget.textCursor()
        position = cursor.position()
        txt = widget.get()
        before = txt[:position]
        row = before.count('\n')
        line = before.split('\n')[row]
        col = cursor.columnNumber()
        col += line[:col].count('\t') * (ext.tabwidth() - 1)
        widget.cursor_changed.emit(row+1, col)

    def reset(self):
        widget = self._widget
        cursor = widget.textCursor()
        cursor.setPosition(0)
        widget.setTextCursor(cursor)


def setup_mono_font(widget):
    widget.setFont(qtutils.diff_font())
    widget.set_tabwidth(prefs.tabwidth())


class MonoTextEdit(PlainTextEdit):

    def __init__(self, parent=None, readonly=False):
        PlainTextEdit.__init__(self, parent=parent, readonly=readonly)
        setup_mono_font(self)


def get_value_hinted(widget):
    text = get_stripped(widget)
    hint = widget.hint.value()
    if text == hint:
        return ''
    else:
        return text


class HintWidget(QtCore.QObject):
    """Extend a widget to provide hint messages

    This primarily exists because setPlaceholderText() is only available
    in Qt5, so this class provides consistent behavior across versions.

    """

    def __init__(self, widget, hint):
        QtCore.QObject.__init__(self, widget)
        self._widget = widget
        self._hint = hint
        self._is_error = False

        self.modern = modern = hasattr(widget, 'setPlaceholderText')
        if modern:
            widget.setPlaceholderText(hint)

        # Palette for normal text
        QPalette = QtGui.QPalette
        palette = widget.palette()

        hint_color = palette.color(QPalette.Disabled, QPalette.Text)
        error_bg_color = QtGui.QColor(Qt.red).darker()
        error_fg_color = QtGui.QColor(Qt.white)

        hint_rgb = qtutils.rgb_css(hint_color)
        error_bg_rgb = qtutils.rgb_css(error_bg_color)
        error_fg_rgb = qtutils.rgb_css(error_fg_color)

        env = dict(name=widget.__class__.__name__,
                   error_fg_rgb=error_fg_rgb,
                   error_bg_rgb=error_bg_rgb,
                   hint_rgb=hint_rgb)

        self._default_style = ''

        self._hint_style = """
            %(name)s {
                color: %(hint_rgb)s;
            }
        """ % env

        self._error_style = """
            %(name)s {
                color: %(error_fg_rgb)s;
                background-color: %(error_bg_rgb)s;
            }
        """ % env

        if not modern:
            widget.installEventFilter(self)
            self.enable(True)

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
        if self.modern:
            self._hint = hint
            self._widget.setPlaceholderText(hint)
        else:
            # If hint-mode is currently active, re-activate it
            active = self.active()
            self._hint = hint
            if active or self.active():
                self.enable(True)

    def enable(self, enable):
        """Enable/disable hint-mode"""
        if not self.modern:
            if enable and self._hint:
                self._widget.set_value(self._hint, block=True)
                self._widget.cursor_position.reset()
            else:
                self._widget.clear()
        self._update_palette(enable)

    def refresh(self):
        """Update the palette to match the current mode"""
        self._update_palette(self.active())

    def _update_palette(self, hint):
        """Update to palette for normal/error/hint mode"""
        if self._is_error:
            style = self._error_style
        elif not self.modern and hint:
            style = self._hint_style
        else:
            style = self._default_style
        self._widget.setStyleSheet(style)

    def eventFilter(self, obj, event):
        """Enable/disable hint-mode when focus changes"""
        etype = event.type()
        if etype == QtCore.QEvent.FocusIn:
            self.focus_in()
        elif etype == QtCore.QEvent.FocusOut:
            self.focus_out()
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
        if not widget.value():
            self.enable(True)


class HintedPlainTextEdit(PlainTextEdit):
    """A hinted plain text edit"""

    def __init__(self, hint, parent=None, readonly=False):
        PlainTextEdit.__init__(self, parent=parent,
                               get_value=get_value_hinted,
                               readonly=readonly)
        self.hint = HintWidget(self, hint)
        setup_mono_font(self)
        # Refresh palettes when text changes
        self.textChanged.connect(self.hint.refresh)

    def set_value(self, value, block=False):
        """Set the widget text or enable hint mode when empty"""
        if value or self.hint.modern:
            PlainTextEdit.set_value(self, value, block=block)
        else:
            self.hint.enable(True)


class HintedTextEdit(TextEdit):
    """A hinted text edit"""

    def __init__(self, hint, parent=None, readonly=False):
        TextEdit.__init__(self, parent=parent,
                          get_value=get_value_hinted, readonly=readonly)
        self.hint = HintWidget(self, hint)
        setup_mono_font(self)
        # Refresh palettes when text changes
        self.textChanged.connect(self.hint.refresh)

    def set_value(self, value, block=False):
        """Set the widget text or enable hint mode when empty"""
        if value or self.hint.modern:
            TextEdit.set_value(self, value, block=block)
        else:
            self.hint.enable(True)


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


class VimHintedPlainTextEdit(HintedPlainTextEdit):
    """HintedPlainTextEdit with vim hotkeys

    This can only be used in read-only mode.

    """
    Base = HintedPlainTextEdit
    Mixin = VimMixin

    def __init__(self, hint, parent=None):
        HintedPlainTextEdit.__init__(self, hint, parent=parent, readonly=True)
        self._mixin = self.Mixin(self)

    def move(self, direction, select=False, n=1):
        return self._mixin.page(direction, select=select, n=n)

    def page(self, offset):
        return self._mixin.page(offset)

    def keyPressEvent(self, event):
        return self._mixin.keyPressEvent(event)


class VimTextEdit(MonoTextEdit):
    """Text viewer with vim-like hotkeys

    This can only be used in read-only mode.

    """
    Base = MonoTextEdit
    Mixin = VimMixin

    def __init__(self, parent=None):
        MonoTextEdit.__init__(self, parent=None, readonly=True)
        self._mixin = self.Mixin(self)

    def move(self, direction, select=False, n=1):
        return self._mixin.page(direction, select=select, n=n)

    def page(self, offset):
        return self._mixin.page(offset)

    def keyPressEvent(self, event):
        return self._mixin.keyPressEvent(event)


class HintedLineEdit(LineEdit):

    def __init__(self, hint, parent=None):
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


class VimTextBrowser(VimTextEdit):
    """Text viewer with line number annotations"""

    def __init__(self, parent=None, readonly=False):
        VimTextEdit.__init__(self, parent=parent)
        self.numbers = LineNumbers(self)

    def resizeEvent(self, event):
        super(VimTextBrowser, self).resizeEvent(event)
        self.numbers.refresh_size()


class TextDecorator(QtWidgets.QWidget):
    """Common functionality for providing line numbers in text widgets"""

    def __init__(self, parent):
        QtWidgets.QWidget.__init__(self, parent)
        self.editor = parent

        parent.blockCountChanged.connect(lambda x: self._refresh_viewport())
        parent.cursorPositionChanged.connect(self.refresh)
        parent.updateRequest.connect(self._refresh_rect)

    def refresh(self):
        """Refresh the numbers display"""
        rect = self.editor.viewport().rect()
        self._refresh_rect(rect, 0)

    def _refresh_rect(self, rect, dy):
        if dy:
            self.scroll(0, dy)
        else:
            self.update(0, rect.y(), self.width(), rect.height())

        if rect.contains(self.editor.viewport().rect()):
            self._refresh_viewport()

    def _refresh_viewport(self):
        self.editor.setViewportMargins(self.width_hint(), 0, 0, 0)

    def refresh_size(self):
        rect = self.editor.contentsRect()
        geom = QtCore.QRect(rect.left(), rect.top(),
                            self.width_hint(), rect.height())
        self.setGeometry(geom)

    def sizeHint(self):
        return QtCore.QSize(self.width_hint(), 0)


class LineNumbers(TextDecorator):
    """Provide line numbers for QPlainTextEdit widgets"""

    def __init__(self, parent):
        TextDecorator.__init__(self, parent)
        self.highlight_line = -1

    def width_hint(self):
        document = self.editor.document()
        digits = int(math.log(max(1, document.blockCount()), 10))
        return defs.margin + self.fontMetrics().width('0') * (digits + 2)

    def set_highlighted(self, line_number):
        """Set the line to highlight"""
        self.highlight_line = line_number

    def paintEvent(self, event):
        """Paint the line number"""
        QPalette = QtGui.QPalette
        painter = QtGui.QPainter(self)
        palette = self.palette()

        painter.fillRect(event.rect(), palette.color(QPalette.Base))

        editor = self.editor
        content_offset = editor.contentOffset()
        block = editor.firstVisibleBlock()
        current_block_number = max(0, self.editor.textCursor().blockNumber())
        width = self.width()
        event_rect_bottom = event.rect().bottom()

        highlight = palette.color(QPalette.Highlight)
        window = palette.color(QPalette.Window)
        disabled = palette.color(QPalette.Disabled, QPalette.Text)
        painter.setPen(disabled)

        while block.isValid():
            block_geom = editor.blockBoundingGeometry(block)
            block_top = block_geom.translated(content_offset).top()
            if not block.isVisible() or block_top >= event_rect_bottom:
                break

            rect = block_geom.translated(content_offset).toRect()
            block_number = block.blockNumber();
            if block_number == self.highlight_line:
                painter.fillRect(rect.x(), rect.y(),
                                 width, rect.height(), highlight)
            elif block_number == current_block_number:
                painter.fillRect(rect.x(), rect.y(),
                                 width, rect.height(), window)

            number = '%s' % (block_number + 1)
            painter.drawText(rect.x(), rect.y(),
                             self.width() - (defs.margin * 2),
                             rect.height(),
                             Qt.AlignRight | Qt.AlignVCenter,
                             number)
            block = block.next()  # pylint: disable=next-method-called
