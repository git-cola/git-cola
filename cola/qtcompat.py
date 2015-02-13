from __future__ import division, absolute_import, unicode_literals

from PyQt4 import QtGui
from PyQt4 import QtCore


def patch(obj, attr, value):
    if not hasattr(obj, attr):
        setattr(obj, attr, value)


def install():
    set_contents_margins = lambda self, *args: self.setMargin(max(args))
    patch(QtGui.QHBoxLayout, 'setContentsMargins', set_contents_margins)
    patch(QtGui.QVBoxLayout, 'setContentsMargins', set_contents_margins)

    set_margin = lambda self, x: self.setContentsMargins(x, x, x, x)
    patch(QtGui.QHBoxLayout, 'setMargin', set_margin)
    patch(QtGui.QVBoxLayout, 'setMargin', set_margin)

    patch(QtGui.QKeySequence, 'Preferences', 'Ctrl+,')
    patch(QtGui.QGraphicsItem, 'mapRectToScene', _map_rect_to_scene)


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
