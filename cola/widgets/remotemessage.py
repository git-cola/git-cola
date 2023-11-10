from qtpy.QtCore import Qt

from .. import qtutils
from ..i18n import N_
from . import defs
from . import standard
from . import text


def show(context, message):
    """Display a window if the remote sent a message"""
    if message:
        view = RemoteMessage(context, message, parent=context.view)
        view.show()
        view.exec_()


def from_context(context):
    """Return a closure for the `result` callback from RunTask.start()"""

    def show_result(result):
        """Display the asynchronous "result" when remote tasks complete"""
        _, out, err = result
        output = '\n\n'.join((x for x in (out, err) if x))
        if output:
            message = N_('Right-click links to open:') + '\n\n' + output
        else:
            message = output

        return show(context, message)

    return show_result


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
