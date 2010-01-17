from PyQt4 import QtGui

def create_button(text, layout=None):
    """Create a button, set its title, and add it to the parent."""
    button = QtGui.QPushButton()
    button.setText(QtGui.QApplication.instance().tr(text))
    if layout:
        layout.addWidget(button)
    return button


class QFlowLayoutWidget(QtGui.QWidget):

    _horizontal = QtGui.QBoxLayout.LeftToRight
    _vertical = QtGui.QBoxLayout.TopToBottom

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self._direction = self._vertical
        self.setLayout(QtGui.QBoxLayout(self._direction))
        self.layout().setSpacing(2)
        self.layout().setMargin(2)
        self.setContentsMargins(2, 2, 2, 2)

    def resizeEvent(self, event):
        size = event.size()
        if size.width() * .39 < size.height():
            dxn = self._vertical
        else:
            dxn = self._horizontal

        if dxn != self._direction:
            self._direction = dxn
            self.layout().setDirection(dxn)
            self.layout().update()
