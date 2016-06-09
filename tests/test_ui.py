from qtpy import QtGui, QtWidgets
from qtpy.uic import loadUi


def get_qapp(icon_path=None):
    qapp = QtWidgets.QApplication.instance()
    if qapp is None:
        qapp = QtWidgets.QApplication([''])
    return qapp


def test_load_ui():
    app = get_qapp()
    ui = loadUi('test.ui')
    assert hasattr(ui, 'pushButton')
    assert hasattr(ui, 'comboBox')