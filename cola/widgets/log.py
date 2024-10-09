import time

from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt
from qtpy.QtCore import Signal

from .. import core
from .. import qtutils
from ..i18n import N_
from . import defs
from . import text
from . import standard


class LogWidget(QtWidgets.QFrame):
    """A simple dialog to display command logs."""

    channel = Signal(object)

    def __init__(self, context, parent=None, output=None, display_usage=True):
        QtWidgets.QFrame.__init__(self, parent)

        self.output_text = text.VimTextEdit(context, parent=self)
        self.highlighter = LogSyntaxHighlighter(self.output_text.document())
        if output:
            self.set_output(output)
        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing, self.output_text)
        self.setLayout(self.main_layout)
        self.setFocusProxy(self.output_text)
        self.channel.connect(self.append, type=Qt.QueuedConnection)
        clear_action = qtutils.add_action(self, N_('Clear'), self.output_text.clear)
        self.output_text.menu_actions.append(clear_action)
        if display_usage:
            self._display_usage()

    def _display_usage(self):
        """Show the default usage message"""
        self.log(N_('Right-click links to open:'))
        self.log('  Documentation: https://git-cola.readthedocs.io/en/latest/')
        self.log(
            '  Keyboard Shortcuts: '
            'https://git-cola.gitlab.io/share/doc/git-cola/hotkeys.html\n'
        )

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
        cursor.movePosition(QtGui.QTextCursor.End)
        text_widget = self.output_text
        # NOTE: the ':  ' colon-SP-SP suffix is for the syntax highlighter
        prefix = core.decode(time.strftime('%Y-%m-%d %H:%M:%S:  '))  # ISO-8601
        for line in msg.split('\n'):
            cursor.insertText(prefix + line + '\n')
        cursor.movePosition(QtGui.QTextCursor.End)
        text_widget.setTextCursor(cursor)

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

    def highlightBlock(self, block_text):
        end = block_text.find(':  ')
        if end > 0:
            self.setFormat(0, end + 1, self.disabled_color)


class RemoteMessage(standard.Dialog):
    """Provides a dialog to display remote messages"""

    def __init__(self, context, message, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.context = context
        self.model = context.model

        self.setWindowTitle(N_('Remote Messages'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.text = text.VimTextEdit(context, parent=self)
        self.text.set_value(message)
        # Set a monospace font, as some remote git messages include ASCII art
        self.text.setFont(qtutils.default_monospace_font())

        self.close_button = qtutils.close_button()
        self.close_button.setDefault(True)

        self.bottom_layout = qtutils.hbox(
            defs.no_margin, defs.button_spacing, qtutils.STRETCH, self.close_button
        )

        self.main_layout = qtutils.vbox(
            defs.no_margin, defs.spacing, self.text, self.bottom_layout
        )
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.close_button, self.close)

        self.resize(defs.scale(720), defs.scale(400))


def show_remote_messages(parent, context):
    """Return a closure for the `result` callback from RunTask.start()"""

    def show_remote_messages_callback(result):
        """Display the asynchronous "result" when remote tasks complete"""
        _, out, err = result
        output = '\n\n'.join(x for x in (out, err) if x)
        if output:
            message = N_('Right-click links to open:') + '\n\n' + output
        else:
            message = output

        # Display a window if the remote sent a message
        if message:
            view = RemoteMessage(context, message, parent=parent)
            view.show()
            view.exec_()

    return show_remote_messages_callback
