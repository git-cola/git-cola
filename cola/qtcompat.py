from __future__ import division, absolute_import, unicode_literals

from cola import sipcompat
sipcompat.initialize()

from PyQt4 import QtGui
from PyQt4 import QtCore

from cola import hotkeys


def patch(obj, attr, value):
    if not hasattr(obj, attr):
        setattr(obj, attr, value)


def _set_contents_margins(self, *args):
    """Polyfill for older PyQt versions"""
    self.setMargin(max(args))


def _set_margin(self, x):
    self.setContentsMargins(x, x, x, x)


def install():
    patch(QtGui.QHBoxLayout, 'setContentsMargins', _set_contents_margins)
    patch(QtGui.QVBoxLayout, 'setContentsMargins', _set_contents_margins)

    patch(QtGui.QHBoxLayout, 'setMargin', _set_margin)
    patch(QtGui.QVBoxLayout, 'setMargin', _set_margin)

    patch(QtGui.QKeySequence, 'Preferences', hotkeys.PREFERENCES)
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
