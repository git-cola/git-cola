"""This module provides utility controllers.
"""

from cola import qtutils
from cola.views import ListView
from cola.views import ComboView
from cola.qobserver import QObserver


def choose_from_combo(title, parent, items):
    """Quickly choose an item from a list using a combo box"""
    return ComboView(parent,
                     title=title,
                     items=items).selected()


def choose_from_list(title, parent, items=[], dblclick=None):
    """Quickly choose an item from a list using a list widget"""
    return ListView(parent,
                    title=title,
                    items=items,
                    dblclick=dblclick).selected()
