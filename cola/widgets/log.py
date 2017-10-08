from __future__ import division, absolute_import, unicode_literals
import time

from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import qtutils
from ..i18n import N_
from . import defs
from .text import VimTextEdit


class LogWidget(QtWidgets.QWidget):
    """A simple dialog to display command logs."""
    channel = Signal(object)

    def __init__(self, parent=None, output=None):
        QtWidgets.QWidget.__init__(self, parent)

        self.output_text = VimTextEdit(parent=self)
        self.highlighter = LogSyntaxHighlighter(self.output_text.document())
        if output:
            self.set_output(output)
        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                        self.output_text)
        self.setLayout(self.main_layout)
        self.channel.connect(self.log, type=Qt.QueuedConnection)

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

    def log(self, msg):
        if not msg:
            return
        cursor = self.output_text.textCursor()
        cursor.movePosition(cursor.End)
        text = self.output_text
        # NOTE: the ':  ' colon-SP-SP suffix in used by the syntax highlighter
        prefix = time.strftime('%I:%M %p %Ss %Y-%m-%d:  ')
        for line in msg.splitlines():
            cursor.insertText(prefix + line + '\n')
        cursor.movePosition(cursor.End)
        text.setTextCursor(cursor)

    def safe_log(self, msg):
        """A version of the log() method that can be called from other
        threads."""
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
