from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola.views import standard


class ComboDialog(standard.Dialog):
    """A dialog for choosing branches."""

    def __init__(self, parent=None, title='', items=None):
        standard.Dialog.__init__(self, parent=parent)

        self.setWindowTitle(title)
        self.resize(400, 73)
        self._main_layt = QtGui.QVBoxLayout(self)

        # Exposed
        self.items_widget = QtGui.QComboBox(self)
        self.items_widget.setEditable(True)

        self._main_layt.addWidget(self.items_widget)

        self.button_box = QtGui.QDialogButtonBox(self)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtGui.QDialogButtonBox.Ok |
                                           QtGui.QDialogButtonBox.Cancel)

        self._main_layt.addWidget(self.button_box)
        self.setTabOrder(self.items_widget, self.button_box)

        if items:
            self.items_widget.addItems(items)

        self.connect(self.button_box, SIGNAL('accepted()'), self.accept)
        self.connect(self.button_box, SIGNAL('rejected()'), self.reject)

    def idx(self):
        return self.items_widget.currentIndex()

    def value(self):
        return unicode(self.items_widget.currentText())

    def selected(self):
        """Present the dialog and return the chosen item."""
        geom = QtGui.QApplication.instance().desktop().screenGeometry()
        width = geom.width()
        height = geom.height()
        if self.parent():
            x = self.parent().x() + self.parent().width()/2 - self.width()/2
            y = self.parent().y() + self.parent().height()/3 - self.height()/2
            self.move(x, y)
        self.show()
        if self.exec_() == QtGui.QDialog.Accepted:
            return self.value()
        else:
            return None


if __name__ == "__main__":
    import sys
    app = QtGui.QApplication(sys.argv)
    combo = ComboDialog()
    combo.show()
    sys.exit(app.exec_())

