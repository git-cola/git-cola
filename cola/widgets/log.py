from __future__ import division

import time

from PyQt4 import QtGui

from cola.i18n import N_
from cola.widgets.text import MonoTextView


class LogWidget(QtGui.QWidget):
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

    def log_status(self, status, out, err=None):
        msg = out
        if err:
            msg += '\n' + err
        if status != 0:
            msg += '\n'
            msg += N_('exit code %s') % status
        self.log(msg)

    def log(self, msg):
        if not msg:
            return
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        text = self.output_text
        cursor.insertText(time.asctime() + '\n')
        for line in msg.splitlines():
            cursor.insertText(line + '\n')
        cursor.insertText('\n')
        cursor.movePosition(cursor.End)
        text.setTextCursor(cursor)
