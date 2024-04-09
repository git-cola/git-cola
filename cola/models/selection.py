"""Provides a selection model to handle selection."""
import collections

from qtpy import QtCore
from qtpy.QtCore import Signal

State = collections.namedtuple('State', 'staged unmerged modified untracked')


def create():
    """Create a SelectionModel"""
    return SelectionModel()


def pick(selection):
    """Choose the first list from stage, unmerged, modified, untracked"""
    if selection.staged:
        files = selection.staged
    elif selection.unmerged:
        files = selection.unmerged
    elif selection.modified:
        files = selection.modified
    elif selection.untracked:
        files = selection.untracked
    else:
        files = []
    return files


def union(selection):
    """Return the union of all selected items in a sorted list"""
    values = set(
        selection.staged + selection.unmerged + selection.modified + selection.untracked
    )
    return list(sorted(values))


def _filter(values, remove):
    """Filter a list in-place by removing items"""
    remove_set = set(remove)
    values_copy = list(values)
    last = len(values_copy) - 1
    for idx, value in enumerate(reversed(values)):
        if value not in remove_set:
            values.pop(last - idx)


class SelectionModel(QtCore.QObject):
    """Provides information about selected file paths."""

    selection_changed = Signal()

    # These properties wrap the individual selection items
    # to provide higher-level pseudo-selections.
    unstaged = property(lambda self: self.unmerged + self.modified + self.untracked)

    def __init__(self):
        super().__init__()
        self.staged = []
        self.unmerged = []
        self.modified = []
        self.untracked = []
        self.line_number = None

    def reset(self, emit=False):
        self.staged = []
        self.unmerged = []
        self.modified = []
        self.untracked = []
        self.line_number = None
        if emit:
            self.selection_changed.emit()

    def is_empty(self):
        return not (
            bool(self.staged or self.unmerged or self.modified or self.untracked)
        )

    def set_selection(self, s):
        """Set the new selection."""
        self.staged = s.staged
        self.unmerged = s.unmerged
        self.modified = s.modified
        self.untracked = s.untracked
        self.selection_changed.emit()

    def update(self, other):
        _filter(self.staged, other.staged)
        _filter(self.unmerged, other.unmerged)
        _filter(self.modified, other.modified)
        _filter(self.untracked, other.untracked)
        self.selection_changed.emit()

    def selection(self):
        return State(self.staged, self.unmerged, self.modified, self.untracked)

    def single_selection(self):
        """Scan across staged, modified, etc. and return a single item."""
        staged = None
        modified = None
        unmerged = None
        untracked = None
        if self.staged:
            staged = self.staged[0]
        elif self.modified:
            modified = self.modified[0]
        elif self.unmerged:
            unmerged = self.unmerged[0]
        elif self.untracked:
            untracked = self.untracked[0]
        return State(staged, unmerged, modified, untracked)

    def filename(self):
        """Return the currently selected filename"""
        paths = [path for path in self.single_selection() if path is not None]
        if paths:
            filename = paths[0]
        else:
            filename = None
        return filename

    def group(self):
        """A list of selected files in various states of being"""
        return pick(self.selection())

    def union(self):
        """Return the union of all selected items in a sorted list"""
        return union(self)
