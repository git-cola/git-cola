from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import QtWebKit
from PyQt4.QtCore import SIGNAL


from cola import qtutils
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
    html = """
<html>
<head>
<style type="text/css">

body {
    font-family: Helvetica, Ubuntu, sans;
    background-color: #303030;
    color: #fff;
}

table.center {
    width: 50%;
    float: left;
    padding-bottom: 20px;
}

td {
    vertical-align: top;
}

td.title {
    color: #ff6;
    font-weight: bold;
}

td.shortcut {
    font-family: Ubuntu Mono, Monaco, monospace;
    color: #ff6;
    text-align: right;
    font-size: 0.8em;
}

span.title {
    font-size: 1.3em;
    font-weight: bold;
}

</style>
</head>

<body>
<span class="title">Keyboard shortcuts</span>
<hr />

<!-- Main actions -->
<table class="center">
<tr>
    <td width="33%">&nbsp;</td>
    <td>&nbsp;</td>
    <td class="title">Main actions</td>
</tr>
<tr>
    <td class="shortcut">Ctrl + s</td>
    <td>:</td>
    <td>Stage/unstage selected files</td>
</tr>
<tr>
    <td class="shortcut">Alt + a</td>
    <td>:</td>
    <td>Stage all modified files</td>
</tr>
<tr>
    <td class="shortcut">Alt + u</td>
    <td>:</td>
    <td>Stage all untracked files</td>
</tr>
<tr>
    <td class="shortcut">Ctrl + b</td>
    <td>:</td>
    <td>Create branch</td>
</tr>
<tr>
    <td class="shortcut">Alt + b</td>
    <td>:</td>
    <td>Checkout branch</td>
</tr>
<tr>
    <td class="shortcut">Alt + d</td>
    <td>:</td>
    <td>Show diffstat</td>
</tr>
<tr>
    <td class="shortcut">Ctrl + e</td>
    <td>:</td>
    <td>Export patches</td>
</tr>
<tr>
    <td class="shortcut">Ctrl + p</td>
    <td>:</td>
    <td>Cherry pick</td>
</tr>
<tr>
    <td class="shortcut">Ctrl + r</td>
    <td>:</td>
    <td>Rescan / refresh repository status</td>
</tr>
<tr>
    <td class="shortcut">Shift + Alt + s</td>
    <td>:</td>
    <td>Stash</td>
</tr>
<tr>
    <td class="shortcut">?</td>
    <td>:</td>
    <td>Toggle keyboard shortcuts window</td>
</tr>
</table>

<!-- Diff Viewer -->
<table class="center">
<tr>
    <td width="33%">&nbsp;</td>
    <td>&nbsp;</td>
    <td class="title">Diff viewer</td>
</tr>
<tr>
    <td class="shortcut">s</td>
    <td>:</td>
    <td>Stage/unstage selected text or
        stage/unstage the patch diff section (hunk) beneath
        the text cursor when nothing is selected
    </td>
</tr>
<tr>
    <td class="shortcut">h</td>
    <td>:</td>
    <td>Stage/unstage the patch diff section (hunk) beneath
        the text cursor
    </td>
</tr>
<tr>
    <td class="shortcut">Ctrl + a</td>
    <td>:</td>
    <td>Select All</td>
</tr>
<tr>
    <td class="shortcut">Ctrl + c</td>
    <td>:</td>
    <td>Copy</td>
</tr>
</table>

<!-- Tree navigation -->
<table class="center">
<tr>
    <td width="33%">&nbsp;</td>
    <td>&nbsp;</td>
    <td class="title">Tree navigation</td>
</tr>
<tr>
    <td class="shortcut">h</td>
    <td>:</td>
    <td>Move to parent/collapse</td>
</tr>
<tr>
    <td class="shortcut">j</td>
    <td>:</td>
    <td>Move down</td>
</tr>
<tr>
    <td class="shortcut">k</td>
    <td>:</td>
    <td>Move up</td>
</tr>
<tr>
    <td class="shortcut">l</td>
    <td>:</td>
    <td>Expand directory</td>
</tr>
</table>

<!-- Classic actions -->
<table class="center">
<tr>
    <td width="33%">&nbsp;</td>
    <td>&nbsp;</td>
    <td class="title">Classic actions</td>
</tr>
<tr>
    <td class="shortcut">Ctrl + e</td>
    <td>:</td>
    <td>Launch editor</td>
</tr>
<tr>
    <td class="shortcut">Ctrl + s</td>
    <td>:</td>
    <td>Stage selected</td>
</tr>
<tr>
    <td class="shortcut">Ctrl + u</td>
    <td>:</td>
    <td>Unstage selected</td>
</tr>
<tr>
    <td class="shortcut">Shift + Ctrl + h</td>
    <td>:</td>
    <td>View history</td>
</tr>
<tr>
    <td class="shortcut">Ctrl + d</td>
    <td>:</td>
    <td>View diff using `git difftool`</td>
</tr>
<tr>
    <td class="shortcut">Shift + Ctrl + d</td>
    <td>:</td>
    <td>View diff against predecessor</td>
</tr>
<tr>
    <td class="shortcut">Ctrl + z</td>
    <td>:</td>
    <td>Revert uncommitted changes</td>
</tr>
</table>
</body>
"""
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
