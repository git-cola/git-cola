"""Provides a selection model to handle selection."""
from __future__ import division, absolute_import, unicode_literals

import collections

from cola.observable import Observable
from cola.decorators import memoize

State = collections.namedtuple('State', 'staged unmerged modified untracked')


@memoize
def selection_model():
    """Provides access to a static SelectionModel instance."""
    return SelectionModel()


def selection():
    """Return the current selection."""
    return selection_model().selection()


def single_selection():
    """Scan across staged, modified, etc. and return a single item."""
    return selection_model().single_selection()


def selected_group():
    return selection_model().group()


def filename():
    return selection_model().filename()


def pick(s):
    if s.staged:
        files = s.staged
    elif s.unmerged:
        files = s.unmerged
    elif s.modified:
        files = s.modified
    elif s.untracked:
        files = s.untracked
    else:
        files = []
    return files


def union(s):
    """Return the union of all selected items in a sorted list"""
    return list(sorted(set(s.staged + s.unmerged + s.modified + s.untracked)))


def _filter(a, b):
    b_set = set(b)
    a_copy = list(a)
    last = len(a_copy) - 1
    for idx, i in enumerate(reversed(a)):
        if i not in b_set:
            a.pop(last - idx)


class SelectionModel(Observable):
    """Provides information about selected file paths."""
    # Notification message sent out when selection changes
    message_selection_changed = 'selection_changed'

    # These properties wrap the individual selection items
    # to provide higher-level pseudo-selections.
    unstaged = property(lambda self: self.unmerged +
                                     self.modified +
                                     self.untracked)

    def __init__(self):
        Observable.__init__(self)
        self.staged = []
        self.unmerged = []
        self.modified = []
        self.untracked = []

    def reset(self):
        self.staged = []
        self.unmerged = []
        self.modified = []
        self.untracked = []

    def is_empty(self):
        return not(bool(self.staged or self.unmerged or
                        self.modified or self.untracked))

    def set_selection(self, s):
        """Set the new selection."""
        self.staged = s.staged
        self.unmerged = s.unmerged
        self.modified = s.modified
        self.untracked = s.untracked
        self.notify_observers(self.message_selection_changed)

    def update(self, other):
        _filter(self.staged, other.staged)
        _filter(self.unmerged, other.unmerged)
        _filter(self.modified, other.modified)
        _filter(self.untracked, other.untracked)
        self.notify_observers(self.message_selection_changed)

    def selection(self):
        return State(self.staged, self.unmerged,
                     self.modified, self.untracked)

    def single_selection(self):
        st = None
        m = None
        um = None
        ut = None
        if self.staged:
            st = self.staged[0]
        elif self.modified:
            m = self.modified[0]
        elif self.unmerged:
            um = self.unmerged[0]
        elif self.untracked:
            ut = self.untracked[0]
        return State(st, um, m, ut)

    def filename(self):
        paths = [p for p in self.single_selection() if p is not None]
        if paths:
            return paths[0]
        else:
            return None

    def group(self):
        """A list of selected files in various states of being"""
        return pick(self.selection())
