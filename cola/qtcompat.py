from __future__ import absolute_import, division, print_function, unicode_literals

from qtpy import PYQT4
from qtpy import QtCore
from qtpy import QtGui
from qtpy import QtWidgets
from qtpy.QtCore import Qt

from . import hotkeys


def patch(obj, attr, value):
    if not hasattr(obj, attr):
        setattr(obj, attr, value)


def install():
    patch(QtWidgets.QGraphicsItem, 'mapRectToScene', _map_rect_to_scene)
    patch(QtGui.QKeySequence, 'Preferences', hotkeys.PREFERENCES)


def add_search_path(prefix, path):
    if hasattr(QtCore.QDir, 'addSearchPath'):
        QtCore.QDir.addSearchPath(prefix, path)


def set_common_dock_options(window):
    if not hasattr(window, 'setDockOptions'):
        return
    nested = QtWidgets.QMainWindow.AllowNestedDocks
    tabbed = QtWidgets.QMainWindow.AllowTabbedDocks
    animated = QtWidgets.QMainWindow.AnimatedDocks
    window.setDockOptions(nested | tabbed | animated)


def _map_rect_to_scene(self, rect):
    """Only available in newer PyQt4 versions"""
    return self.sceneTransform().mapRect(rect)


def wheel_translation(event):
    """Return the Tx Ty translation delta for a pan"""
    if PYQT4:
        tx = event.delta()
        ty = 0.0
        if event.orientation() == Qt.Vertical:
            (tx, ty) = (ty, tx)
    else:
        angle = event.angleDelta()
        tx = angle.x()
        ty = angle.y()
    return (tx, ty)


def wheel_delta(event):
    """Return a single wheel delta"""
    if PYQT4:
        delta = event.delta()
    else:
        angle = event.angleDelta()
        x = angle.x()
        y = angle.y()
        if abs(x) > abs(y):
            delta = x
        else:
            delta = y
    return delta
