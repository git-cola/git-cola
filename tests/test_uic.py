import os
import sys
import contextlib

import pytest

from qtpy import QtWidgets, PYSIDE
from qtpy.QtWidgets import QComboBox
from qtpy.uic import loadUi


QCOMBOBOX_SUBCLASS = """
from qtpy.QtWidgets import QComboBox
class _QComboBoxSubclass(QComboBox):
    pass
"""

@contextlib.contextmanager
def enabled_qcombobox_subclass(tmpdir):
    """
    Context manager that sets up a temporary module with a QComboBox subclass
    and then removes it once we are done.
    """

    with open(tmpdir.join('qcombobox_subclass.py').strpath, 'w') as f:
        f.write(QCOMBOBOX_SUBCLASS)

    sys.path.insert(0, tmpdir.strpath)

    yield

    sys.path.pop(0)


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


def test_load_ui_custom(tmpdir):
    """
    Test that we can load a .ui file with custom widgets
    """

    app = get_qapp()

    with enabled_qcombobox_subclass(tmpdir):
        from qcombobox_subclass import _QComboBoxSubclass
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
def test_load_ui_custom_auto(tmpdir):
    """
    Test that we can load a .ui file with custom widgets without having to
    explicitly specify a dictionary of custom widgets, even in the case of
    PySide.
    """

    app = get_qapp()

    with enabled_qcombobox_subclass(tmpdir):
        from qcombobox_subclass import _QComboBoxSubclass
        ui = loadUi(os.path.join(os.path.dirname(__file__), 'test_custom.ui'))

    assert isinstance(ui.pushButton, QtWidgets.QPushButton)
    assert isinstance(ui.comboBox, _QComboBoxSubclass)
