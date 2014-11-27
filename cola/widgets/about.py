from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4.QtCore import Qt


from cola import core
from cola import resources
from cola import qtutils
from cola import version
from cola.i18n import N_
from cola.widgets import defs
from cola.widgets.text import MonoTextView

def launch_about_dialog():
    """Launches the Help -> About dialog"""
    view = AboutView(qtutils.active_window())
    view.set_version(version.version())
    view.show()


COPYRIGHT = """git-cola: The highly caffeinated git GUI v$VERSION

Copyright (C) 2007-2014, David Aguilar and contributors

This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License
version 2 as published by the Free Software Foundation.

This program is distributed in the hope that it will
be useful, but WITHOUT ANY WARRANTY; without even the
implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the
GNU General Public License along with this program.
If not, see http://www.gnu.org/licenses/.

"""

class AboutView(QtGui.QDialog):
    """Provides the git-cola 'About' dialog.
    """
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self, parent)

        self.setWindowTitle(N_('About git-cola'))
        self.setWindowModality(Qt.WindowModal)

        self.label = QtGui.QLabel()
        self.pixmap = QtGui.QPixmap('icons:logo-top.png')
        #self.label.setStyleSheet('QWidget {background: #000; }')
        self.label.setPixmap(self.pixmap)
        self.label.setAlignment(Qt.AlignRight | Qt.AlignTop)

        palette = self.label.palette()
        palette.setColor(QtGui.QPalette.Window, Qt.black)
        self.label.setAutoFillBackground(True)
        self.label.setPalette(palette)

        self.text = MonoTextView(self)
        self.text.setReadOnly(True)
        self.text.setPlainText(COPYRIGHT)

        self.close_button = QtGui.QPushButton()
        self.close_button.setText(N_('Close'))
        self.close_button.setDefault(True)

        self.button_layout = qtutils.hbox(defs.spacing, defs.margin,
                                          qtutils.STRETCH, self.close_button)

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing,
                                        self.label, self.text,
                                        self.button_layout)
        self.setLayout(self.main_layout)

        self.resize(666, 420)

        qtutils.connect_button(self.close_button, self.accept)

    def set_version(self, version):
        """Sets the version field in the 'about' dialog"""
        self.text.setPlainText(self.text.toPlainText().replace('$VERSION', version))


def show_shortcuts():
    try:
        from PyQt4 import QtWebKit
    except ImportError:
        # redhat disabled QtWebKit in their qt build but don't punish the
        # users
        qtutils.critical(N_('This PyQt4 does not include QtWebKit.\n'
                            'The keyboard shortcuts feature is unavailable.'))
        return

    try:
        html = show_shortcuts.html
    except AttributeError:
        hotkeys = resources.doc(N_('hotkeys.html'))
        html = show_shortcuts.html = core.read(hotkeys)

    try:
        widget = show_shortcuts.widget
    except AttributeError:
        parent = qtutils.active_window()
        widget = show_shortcuts.widget = QtGui.QDialog(parent)
        widget.setWindowModality(Qt.WindowModal)
        widget.setWindowTitle(N_('Shortcuts'))

        web = QtWebKit.QWebView(parent)
        web.setHtml(html)

        layout = qtutils.hbox(defs.no_margin, defs.spacing, web)
        widget.setLayout(layout)
        widget.resize(800, min(parent.height(), 600))

        qtutils.add_action(widget, N_('Close'), widget.accept,
                           Qt.Key_Question, Qt.Key_Enter, Qt.Key_Return)
    widget.show()
    return widget
