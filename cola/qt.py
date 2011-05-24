from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4.QtCore import Qt

from cola import i18n


def create_button(text, layout=None, tooltip=None, icon=None):
    """Create a button, set its title, and add it to the parent."""
    button = QtGui.QPushButton()
    button.setText(i18n.gettext(text))
    if icon:
        button.setIcon(icon)
    if layout is not None:
        layout.addWidget(button)
    return button


def create_toolbutton(parent, text=None, layout=None, tooltip=None, icon=None):
    button = QtGui.QToolButton(parent)
    button.setAutoRaise(True)
    button.setAutoFillBackground(True)
    if icon:
        button.setIcon(icon)
    if text:
        button.setText(i18n.gettext(text))
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    if tooltip:
        button.setToolTip(i18n.gettext(tooltip))
    if layout is not None:
        layout.addWidget(button)
    return button


class QFlowLayoutWidget(QtGui.QWidget):

    _horizontal = QtGui.QBoxLayout.LeftToRight
    _vertical = QtGui.QBoxLayout.TopToBottom

    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self._direction = self._vertical
        self._layout = layout = QtGui.QBoxLayout(self._direction)
        layout.setSpacing(2)
        layout.setMargin(2)
        self.setLayout(layout)
        self.setContentsMargins(2, 2, 2, 2)
        policy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,
                                   QtGui.QSizePolicy.Minimum)
        self.setSizePolicy(policy)
        self.setMinimumSize(QtCore.QSize(1, 1))

    def resizeEvent(self, event):
        size = event.size()
        if size.width() * 0.8 < size.height():
            dxn = self._vertical
        else:
            dxn = self._horizontal

        if dxn != self._direction:
            self._direction = dxn
            self.layout().setDirection(dxn)
