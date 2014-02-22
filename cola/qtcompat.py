from __future__ import division, absolute_import

from PyQt4 import QtGui
from PyQt4 import QtCore

def install():
    if not hasattr(QtGui.QHBoxLayout, 'setContentsMargins'):
        QtGui.QHBoxLayout.setContentsMargins = lambda *args: True

    if not hasattr(QtGui.QVBoxLayout, 'setContentsMargins'):
        QtGui.QVBoxLayout.setContentsMargins = lambda *args: True

    if not hasattr(QtGui.QKeySequence, 'Preferences'):
        QtGui.QKeySequence.Preferences = 'Ctrl+O'

    if not hasattr(QtGui.QGraphicsItem, 'mapRectToScene'):
        QtGui.QGraphicsItem.mapRectToScene = _map_rect_to_scene

    if not hasattr(QtCore.QCoreApplication, 'setStyleSheet'):
        QtCore.QCoreApplication.setStyleSheet = lambda *args: None


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


def _map_rect_to_scene(self, rect):
    """Only available in newer PyQt4 versions"""
    return self.sceneTransform().mapRect(rect)
