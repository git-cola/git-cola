from PyQt4 import QtGui


from cola import i18n


def create_button(text, layout=None):
    """Create a button, set its title, and add it to the parent."""
    button = QtGui.QPushButton()
    button.setText(i18n.gettext(text))
    if layout:
        layout.addWidget(button)
    return button
