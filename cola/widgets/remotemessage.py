from __future__ import division, absolute_import, unicode_literals
import re

from qtpy.QtCore import Qt

from .. import qtutils
from ..i18n import N_
from . import defs
from . import standard


URL_REGEX = re.compile('https?://'           # Protocol
                       '([^/]+(:[^/]+)?@)?'  # Optional authentication
                       '[\\w.-]+'            # Domain name
                       '(:[0-9]+)?'          # Optional port
                       '(/[^\\s]*)?')        # Optional path


def to_link(url):
    return qtutils.link(url, url)


def format_raw(string, start, end, offset=0):
    """Replace a part of a string and transform it to a link"""
    chars = list(string)
    chars[start+offset:end+offset] = to_link(string[start+offset:end+offset])
    result = ''.join(chars)
    return result, offset + len(result) - len(string)


def format_links(string):
    """Transform all links into HTML links"""
    offset = 0
    for url_match in URL_REGEX.finditer(string):
        string, offset = format_raw(string, url_match.start(),
                                    url_match.end(), offset)
    return string


def show(context, message):
    """Display a window if the remote sent a message"""
    message_lines = message.split('\n')
    # Get lines starting with 'remote: '
    remote_lines = [line[8:] for line in message_lines
                    if line.startswith('remote: ')]
    if remote_lines:
        # Transform new lines to HTML '<br>'
        remote_message = '<br>'.join(remote_lines)
        view = RemoteMessage(context, format_links(remote_message),
                             parent=qtutils.active_window())
        view.show()


def with_context(context):
    """Helper function to pass to the `result` argument of RunTask.start"""
    def wrapper(raw_message):
        return show(context, raw_message[2])
    return wrapper


class RemoteMessage(standard.Dialog):
    """Provides a dialog to display remote messages"""

    def __init__(self, context, message, parent=None):
        standard.Dialog.__init__(self, parent=parent)
        self.context = context
        self.model = context.model

        self.setWindowTitle(N_('Remote message'))
        if parent is not None:
            self.setWindowModality(Qt.WindowModal)

        self.text = qtutils.textbrowser(text=message)
        # Set a monospace font, as some remote git messages include ASCII art
        self.text.setFont(qtutils.default_monospace_font())

        self.close_button = qtutils.close_button()
        self.close_button.setDefault(True)

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                        self.text,
                                        self.close_button)
        self.setLayout(self.main_layout)

        qtutils.connect_button(self.close_button, self.close)

        self.resize(defs.scale(600), defs.scale(400))
