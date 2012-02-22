from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL


class HintedTextWidgetEventFilter(QtCore.QObject):
    def __init__(self, parent):
        super(HintedTextWidgetEventFilter, self).__init__(parent)
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
        self._hint = unicode(self.tr(hint))
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
            return u''
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


class HintedTextEdit(QtGui.QTextEdit, HintedTextWidgetMixin):
    def __init__(self, hint, parent=None):
        QtGui.QTextEdit.__init__(self, parent)
        HintedTextWidgetMixin.__init__(self, hint)

        self.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.setAcceptRichText(False)

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
        rows = txt[:position].count('\n') + 1
        cols = cursor.columnNumber()
        self.emit(SIGNAL('cursorPosition(int,int)'), rows, cols)


class HintedLineEdit(QtGui.QLineEdit, HintedTextWidgetMixin):
    def __init__(self, hint, parent=None):
        QtGui.QLineEdit.__init__(self, parent)
        HintedTextWidgetMixin.__init__(self, hint)

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
