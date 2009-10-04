"""Provides the ListView dialog."""

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola.views import standard


class ListView(standard.StandardDialog):
    def __init__(self, parent=None, title="", items=None, dblclick=None):
        standard.StandardDialog.__init__(self, parent=parent)

        self.setWindowTitle(title)

        self.resize(523, 299)
        self._main_layt = QtGui.QVBoxLayout(self)

        # Exposed
        self.items_widget = QtGui.QListWidget(self)
        self._main_layt.addWidget(self.items_widget)

        # Exposed
        self.button_box = QtGui.QDialogButtonBox(self)
        self.button_box.setOrientation(QtCore.Qt.Horizontal)
        self.button_box.setStandardButtons(QtGui.QDialogButtonBox.Ok |
                                           QtGui.QDialogButtonBox.Cancel)
        self._main_layt.addWidget(self.button_box)

        if items:
            self.items_widget.addItems(items)

        self.setTabOrder(self.items_widget, self.button_box)
        self.connect(self.button_box, SIGNAL('accepted()'), self.accept)
        self.connect(self.button_box, SIGNAL('rejected()'), self.reject)
        if dblclick:
            self.connect(self.items_widget,
                         SIGNAL('itemDoubleClicked(QListWidgetItem*)'),
                         dblclick)

    def idx(self):
        return self.items_widget.currentRow()

    def value(self):
        item = self.items_widget.currentItem()
        if not item:
            return None
        return str(item.text())

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
    items = ListView()
    items.show()
    sys.exit(app.exec_())
