from PyQt4 import QtGui

from cola import version
from cola.gui.about import Ui_about

def launch_about_dialog(view):
    """Launches the Help -> About dialog"""
    view = AboutView(view)
    style = QtGui.QApplication.instance().styleSheet()
    if style:
        view.setStyleSheet(style)
    view.show()
    view.set_version(version.version())


class AboutView(Ui_about, QtGui.QDialog):
    """A custom dialog for displaying git-cola information
    """
    def __init__(self, parent):
        QtGui.QDialog.__init__(self, parent)
        Ui_about.__init__(self)
        self.setupUi(self)

    def set_version(self, version):
        """Sets the version field in the 'about' dialog"""
        self.spam.setText(self.spam.text().replace('$VERSION', version))
