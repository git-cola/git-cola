import os


def test_qt_api():
    """
    If QT_API is specified, we check that the correct Qt wrapper was used
    """

    from qtpy import QtCore, QtGui, QtWidgets, QtWebEngineWidgets

    QT_API = os.environ.get('QT_API', None)

    if QT_API == 'pyside':
        import PySide
        assert QtCore.QEvent is PySide.QtCore.QEvent
        assert QtGui.QPainter is PySide.QtGui.QPainter
        assert QtWidgets.QWidget is PySide.QtGui.QWidget
        assert QtWebEngineWidgets.QWebEnginePage is PySide.QtWebKit.QWebPage
    elif QT_API in ('pyqt', 'pyqt4'):
        import PyQt4
        assert QtCore.QEvent is PyQt4.QtCore.QEvent
        assert QtGui.QPainter is PyQt4.QtGui.QPainter
        assert QtWidgets.QWidget is PyQt4.QtGui.QWidget
        assert QtWebEngineWidgets.QWebEnginePage is PyQt4.QtWebKit.QWebPage
    elif QT_API == 'pyqt5':
        import PyQt5
        assert QtCore.QEvent is PyQt5.QtCore.QEvent
        assert QtGui.QPainter is PyQt5.QtGui.QPainter
        assert QtWidgets.QWidget is PyQt5.QtWidgets.QWidget
        assert QtWebEngineWidgets.QWebEnginePage is PyQt5.QtWebEngineWidgets.QWebEnginePage
    else:
        pass
