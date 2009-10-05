"""This module provides utility controllers.
"""
from PyQt4 import QtGui

from cola import qtutils
from cola.views import itemlist
from cola.views import combo
from cola.qobserver import QObserver


def choose_from_combo(title, items):
    """Quickly choose an item from a list using a combo box"""
    parent = QtGui.QApplication.instance().activeWindow()
    return combo.ComboView(parent,
                           title=title,
                           items=items).selected()


def choose_from_list(title, items=None, dblclick=None):
    """Quickly choose an item from a list using a list widget"""
    parent = QtGui.QApplication.instance().activeWindow()
    return itemlist.ListView(parent,
                             title=title,
                             items=items,
                             dblclick=dblclick).selected()
