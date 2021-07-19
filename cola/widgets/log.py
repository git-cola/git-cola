from __future__ import absolute_import, division, print_function, unicode_literals
import time

from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import core
from .. import qtutils
from ..i18n import N_
from . import defs
from .text import VimTextEdit


class LogWidget(QtWidgets.QFrame):
    """A simple dialog to display command logs."""

    channel = Signal(object)

    def __init__(self, context, parent=None, output=None):
        QtWidgets.QFrame.__init__(self, parent)

        self.output_text = VimTextEdit(context, parent=self)
        self.highlighter = LogSyntaxHighlighter(self.output_text.document())
        if output:
            self.set_output(output)
        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing, self.output_text)
        self.setLayout(self.main_layout)
        self.channel.connect(self.append, type=Qt.QueuedConnection)

    def clear(self):
        self.output_text.clear()

    def set_output(self, output):
        self.output_text.set_value(output)

    def log_status(self, status, out, err=None):
        msg = []
        if out:
            msg.append(out)
        if err:
            msg.append(err)
        if status:
            msg.append(N_('exit code %s') % status)
        self.log('\n'.join(msg))

    def append(self, msg):
        """Append to the end of the log message"""
        if not msg:
            return
        msg = core.decode(msg)
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        text = self.output_text
        # NOTE: the ':  ' colon-SP-SP suffix is for the syntax highlighter
        prefix = core.decode(time.strftime('%Y-%m-%d %H:%M:%S:  '))  # ISO-8601
        for line in msg.split('\n'):
            cursor.insertText(prefix + line + '\n')
        cursor.movePosition(cursor.End)
        text.setTextCursor(cursor)

    def log(self, msg):
        """Add output to the log window"""
        # Funnel through a Qt queued to allow thread-safe logging from
        # asynchronous QRunnables, filesystem notification, etc.
        self.channel.emit(msg)


class LogSyntaxHighlighter(QtGui.QSyntaxHighlighter):
    """Implements the log syntax highlighting"""

    def __init__(self, doc):
        QtGui.QSyntaxHighlighter.__init__(self, doc)
        palette = QtGui.QPalette()
        QPalette = QtGui.QPalette
        self.disabled_color = palette.color(QPalette.Disabled, QPalette.Text)

    def highlightBlock(self, text):
        end = text.find(':  ')
        if end > 0:
            self.setFormat(0, end + 1, self.disabled_color)
