from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt, SIGNAL

from cola.models.prefs import tabwidth
from cola.qtutils import diff_font


class MonoTextEdit(QtGui.QTextEdit):

    def __init__(self, parent):
        QtGui.QTextEdit.__init__(self, parent)
        self._tabwidth = 8
        self.setMinimumSize(QtCore.QSize(1, 1))
        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.setAcceptRichText(False)
        self.setFont(diff_font())
        self.set_tabwidth(tabwidth())
        self.setCursorWidth(2)

    def tabwidth(self):
        return self._tabwidth

    def set_tabwidth(self, width):
        self._tabwidth = width
        font = self.font()
        fm = QtGui.QFontMetrics(font)
        pixels = fm.width('m' * width)
        self.setTabStopWidth(pixels)

    def set_textwidth(self, width):
        font = self.font()
        fm = QtGui.QFontMetrics(font)
        pixels = fm.width('m' * (width + 2))
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
        contents = unicode(self.toPlainText())
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
            self.widget.emit_position()
            if self.widget.is_hint():
                self.widget.enable_hint(False)

        elif event.type() == QtCore.QEvent.FocusOut:
            if not bool(self.widget.value()):
                self.widget.enable_hint(True)

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

    def emit_position(self):
        pass

    def reset_cursor(self):
        pass

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

    def strip(self):
        return self.as_unicode().strip()

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


class HintedTextEditMixin(HintedTextWidgetMixin):

    def __init__(self, hint):
        HintedTextWidgetMixin.__init__(self, hint)
        self.connect(self, SIGNAL('cursorPositionChanged()'),
                     self.emit_position)

    def as_unicode(self):
        return unicode(self.toPlainText())

    def set_value(self, value):
        self.setPlainText(value)
        self.refresh_palette()

    def emit_position(self):
        cursor = self.textCursor()
        position = cursor.position()
        txt = self.as_unicode()
        before = txt[:position]
        row = before.count('\n')
        line = before.split('\n')[row]
        col = cursor.columnNumber()
        if hasattr(self, 'tabwidth'):
            col += line[:col].count('\t') * (self.tabwidth() - 1)
        self.emit(SIGNAL('cursorPosition(int,int)'), row+1, col)


class HintedTextEdit(MonoTextEdit, HintedTextEditMixin):

    def __init__(self, hint, parent=None):
        MonoTextEdit.__init__(self, parent)
        HintedTextEditMixin.__init__(self, hint)


# The read-only variant.
class HintedTextView(MonoTextView, HintedTextEditMixin):

    def __init__(self, hint, parent=None):
        MonoTextView.__init__(self, parent)
        HintedTextEditMixin.__init__(self, hint)


class HintedLineEdit(QtGui.QLineEdit, HintedTextWidgetMixin):

    def __init__(self, hint, parent=None):
        QtGui.QLineEdit.__init__(self, parent)
        HintedTextWidgetMixin.__init__(self, hint)

        self.setFont(diff_font())
        self.connect(self,
                     SIGNAL('cursorPositionChanged(int,int)'),
                     lambda x, y: self.emit_position())

    def emit_position(self):
        cols = self.cursorPosition()
        self.emit(SIGNAL('cursorPosition(int,int)'), 1, cols)

    def set_value(self, value):
        self.setText(value)
        self.refresh_palette()

    def as_unicode(self):
        return unicode(self.text())

    def reset_cursor(self):
        self.setCursorPosition(0)
