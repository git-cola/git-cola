import time

from PyQt4 import QtGui

from cola import core
from cola.views.syntax import LogSyntaxHighlighter


class LogView(QtGui.QWidget):
    """A simple dialog to display command logs."""
    def __init__(self, parent=None, output=None):
        QtGui.QWidget.__init__(self, parent)

        self._layout = QtGui.QVBoxLayout(self)
        self._layout.setContentsMargins(3, 3, 3, 3)

        self.output_text = QtGui.QTextEdit(self)
        self.output_text.setAcceptDrops(False)
        self.output_text.setTabChangesFocus(True)
        self.output_text.setUndoRedoEnabled(False)
        self.output_text.setReadOnly(True)
        self.output_text.setAcceptRichText(False)
        self._layout.addWidget(self.output_text)
        if output:
            self.set_output(output)
        self.syntax = LogSyntaxHighlighter(self.output_text.document())

    def clear(self):
        self.output_text.clear()

    def set_output(self, output):
        self.output_text.setText(output)

    def log(self, status, output):
        if not output:
            return
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        text = self.output_text
        cursor.insertText(time.asctime() + '\n')
        for line in unicode(core.decode(output)).splitlines():
            cursor.insertText(line + '\n')
        cursor.insertText('\n')
        cursor.movePosition(cursor.End)
        text.setTextCursor(cursor)
