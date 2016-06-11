import os

import pytest

from qtpy import QtWidgets, PYSIDE
from qtpy.QtWidgets import QComboBox
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
    Make sure that the patched loadUi function behaves as expected with a
    simple .ui file.
    """
    app = get_qapp()
    ui = loadUi(os.path.join(os.path.dirname(__file__), 'test.ui'))
    assert isinstance(ui.pushButton, QtWidgets.QPushButton)
    assert isinstance(ui.comboBox, QComboBox)


def test_load_ui_custom():
    """
    Test that we can load a .ui file with custom widgets
    """
    app = get_qapp()
    if PYSIDE:
        customWidgets = {'_QComboBoxSubclass': _QComboBoxSubclass}
        ui = loadUi(os.path.join(os.path.dirname(__file__), 'test_custom.ui'),
                    customWidgets=customWidgets)
    else:
        ui = loadUi(os.path.join(os.path.dirname(__file__), 'test_custom.ui'))
    assert isinstance(ui.pushButton, QtWidgets.QPushButton)
    assert isinstance(ui.comboBox, _QComboBoxSubclass)


@pytest.mark.xfail(PYSIDE, reason='The PySide loadUi wrapper does not yet '
                                  'support determining custom widgets '
                                  'automatically')
def test_load_ui_custom_auto():
    """
    Test that we can load a .ui file with custom widgets without having to
    explicitly specify a dictionary of custom widgets, even in the case of
    PySide.
    """
    app = get_qapp()
    ui = loadUi(os.path.join(os.path.dirname(__file__), 'test_custom.ui'))
    assert isinstance(ui.pushButton, QtWidgets.QPushButton)
    assert isinstance(ui.comboBox, _QComboBoxSubclass)
