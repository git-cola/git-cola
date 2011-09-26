from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import SIGNAL

from cola import version

def launch_about_dialog():
    """Launches the Help -> About dialog"""
    app = QtGui.QApplication.instance()
    view = AboutView(app.activeWindow())
    style = app.styleSheet()
    if style:
        view.setStyleSheet(style)
    view.show()
    view.set_version(version.version())


COPYRIGHT = """git-cola: A highly caffeinated git GUI v$VERSION

git-cola is a sweet, carbonated git GUI known for its
sugary flavour and caffeine-inspired features.


Copyright (C) 2009, 2010, 2011 David Aguilar and contributors

This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation, either
version 2 of the License, or (at your option)
any later version.

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
