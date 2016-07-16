from __future__ import division, absolute_import, unicode_literals
import time

from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import qtutils
from ..i18n import N_
from . import defs
from .text import MonoTextView


class LogWidget(QtWidgets.QWidget):
    """A simple dialog to display command logs."""
    channel = Signal(object)

    def __init__(self, parent=None, output=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.output_text = MonoTextView(self)
        if output:
            self.set_output(output)
        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                        self.output_text)
        self.setLayout(self.main_layout)
        self.channel.connect(self.log, type=Qt.QueuedConnection)

    def clear(self):
        self.output_text.clear()

    def set_output(self, output):
        self.output_text.setText(output)

    def log_status(self, status, out, err=None):
        msg = []
        if out:
            msg.append(out)
        if err:
            msg.append(err)
        if status:
            msg.append(N_('exit code %s') % status)
        self.log('\n'.join(msg))

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

    def safe_log(self, msg):
        """A version of the log() method that can be called from other
        threads."""
        self.channel.emit(msg)
