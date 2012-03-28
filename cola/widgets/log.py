import time

from PyQt4 import QtGui

from cola import core
from cola.widgets.text import MonoTextView


class LogView(QtGui.QWidget):
    """A simple dialog to display command logs."""
    def __init__(self, parent=None, output=None):
        QtGui.QWidget.__init__(self, parent)

        self._layout = QtGui.QVBoxLayout(self)
        self._layout.setMargin(0)

        self.output_text = MonoTextView(self)
        self._layout.addWidget(self.output_text)
        if output:
            self.set_output(output)

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
