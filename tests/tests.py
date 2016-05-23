import os

os.environ['QT_API'] = os.environ['USE_QT_API'].lower()

from qtpy import QtCore, QtGui, QtWidgets, QtWebEngineWidgets

print('Qt version:{0!s}'.format(QtCore.__version__))
print(QtCore.QEvent)
print(QtGui.QPainter)
print(QtWidgets.QWidget)
print(QtWebEngineWidgets.QWebEnginePage)
