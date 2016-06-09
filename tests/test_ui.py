import os

from qtpy import QtWidgets
from qtpy.uic import loadUi, _QComboBoxSubclass


def get_qapp(icon_path=None):
    """
    Helper function to return a QApplication instance
    """
    qapp = QtWidgets.QApplication.instance()
    if qapp is None:
        qapp = QtWidgets.QApplication([''])
    return qapp


def test_load_ui():
    """
    Make sure that the patched loadUi function behaves as expected
    """
    app = get_qapp()
    ui = loadUi(os.path.join(os.path.dirname(__file__), 'test.ui'))
    assert isinstance(ui.pushButton, QtWidgets.QPushButton)
    assert isinstance(ui.comboBox, _QComboBoxSubclass)
