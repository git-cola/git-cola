from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL


from cola import resources
from cola import qtutils
from cola import utils
from cola import version

def launch_about_dialog():
    """Launches the Help -> About dialog"""
    view = AboutView(qtutils.active_window())
    view.show()
    view.set_version(version.version())


COPYRIGHT = """git-cola: The highly caffeinated git GUI v$VERSION

git-cola is a sweet, carbonated git GUI known for its
sugary flavor and caffeine-inspired features.


Copyright (C) 2007-2012, David Aguilar and contributors

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

        self.setWindowTitle('About git-cola')
        self.setStyleSheet('QWidget { background-color: white; color: #666; }')

        self.setMinimumSize(QtCore.QSize(280, 420))
        self.setMaximumSize(QtCore.QSize(280, 420))

        self.ham = QtGui.QLabel(self)
        self.ham.setGeometry(QtCore.QRect(0, -10, 291, 121))
        self.ham.setPixmap(QtGui.QPixmap('images:logo-cola.png'))

        self.spam = QtGui.QLabel(self)
        self.spam.setGeometry(QtCore.QRect(10, 110, 261, 261))

        font = QtGui.QFont()
        font.setFamily('Sans Serif')
        font.setPointSize(5)
        self.spam.setFont(font)

        self.spam.setTextFormat(QtCore.Qt.LogText)
        self.spam.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.spam.setWordWrap(True)
        self.spam.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.spam.setText(COPYRIGHT)

        self.kthx = QtGui.QPushButton(self)
        self.kthx.setGeometry(QtCore.QRect(60, 380, 160, 24))
        self.kthx.setText('kthx bye')
        self.kthx.setDefault(True)

        self.connect(self.kthx, SIGNAL('clicked()'), self.accept)

    def set_version(self, version):
        """Sets the version field in the 'about' dialog"""
        self.spam.setText(self.spam.text().replace('$VERSION', version))


def show_shortcuts():
    try:
        from PyQt4 import QtWebKit
    except ImportError:
        # redhat disabled QtWebKit in their qt build but don't punish the
        # users
        qtutils.critical('This PyQt4 does not include QtWebKit.\n'
                         'The keyboard shortcuts feature is unavailable.')
        return

    try:
        html = show_shortcuts.html
    except AttributeError:
        hotkeys = resources.doc('hotkeys.html')
        html = show_shortcuts.html = utils.slurp(hotkeys)

    try:
        widget = show_shortcuts.widget
    except AttributeError:
        parent = qtutils.active_window()
        widget = show_shortcuts.widget = QtGui.QDialog(parent)
        widget.setWindowModality(QtCore.Qt.WindowModal)
        widget.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)

        web = QtWebKit.QWebView(parent)
        web.setHtml(html)

        layout = QtGui.QHBoxLayout()
        layout.setMargin(0)
        layout.setSpacing(0)
        layout.addWidget(web)

        widget.setLayout(layout)
        widget.resize(800, min(parent.height(), 600))

        qtutils.add_action(widget, 'Close', widget.accept,
                           QtCore.Qt.Key_Question,
                           QtCore.Qt.Key_Enter,
                           QtCore.Qt.Key_Return)
    widget.show()
    return widget
