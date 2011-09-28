from PyQt4 import QtGui
from PyQt4 import QtCore

def install():
    if not hasattr(QtGui.QHBoxLayout, 'setContentsMargins'):
        QtGui.QHBoxLayout.setContentsMargins = lambda *args: True

    if not hasattr(QtGui.QVBoxLayout, 'setContentsMargins'):
        QtGui.QVBoxLayout.setContentsMargins = lambda *args: True

    if not hasattr(QtGui.QKeySequence, 'Preferences'):
        QtGui.QKeySequence.Preferences = 'Ctrl+O'


def add_search_path(prefix, path):
    if hasattr(QtCore.QDir, 'addSearchPath'):
        QtCore.QDir.addSearchPath(prefix, path)

def set_common_dock_options(window):
    if not hasattr(window, 'setDockOptions'):
        return
    nested = QtGui.QMainWindow.AllowNestedDocks
    tabbed = QtGui.QMainWindow.AllowTabbedDocks
    animated = QtGui.QMainWindow.AnimatedDocks
    window.setDockOptions(nested | tabbed | animated)
