"""Provides a selection model to handle selection."""

from cola.models.observable import ObservableModel

_selection_model = None
def selection_model():
    """Provides access to a static SelectionModel instance."""
    global _selection_model
    if _selection_model:
        return _selection_model
    _selection_model = SelectionModel()
    return _selection_model


def selection():
    """Return the current selection."""
    model = selection_model()
    return (model.staged, model.modified, model.unmerged, model.untracked)


def single_selection():
    """Scan across staged, modified, etc. and return a single item."""
    staged, modified, unmerged, untracked = selection()
    s = None
    m = None
    um = None
    ut = None
    if staged:
        s = staged[0]
    elif modified:
        m = modified[0]
    elif unmerged:
        um = unmerged[0]
    elif untracked:
        ut = untracked[0]
    return s, m, um, ut


def filename():
    s, m, um, ut = single_selection()
    if s:
        return s
    if m:
        return m
    if um:
        return um
    if ut:
        return ut
    return None


class SelectionModel(ObservableModel):
    """Provides information about selected file paths."""
    # Notification message sent out when selection changes
    message_selection_changed = 'selection_changed'

    # These properties wrap the individual selection items
    # to provide higher-level pseudo-selections.
    unstaged = property(lambda self: self.modified +
                                     self.unmerged +
                                     self.untracked)

    all = property(lambda self: self.staged +
                                self.modified +
                                self.unmerged +
                                self.untracked)

    def __init__(self):
        ObservableModel.__init__(self)
        self.staged = []
        self.modified = []
        self.unmerged = []
        self.untracked = []

    def set_selection(self, staged, modified, unmerged, untracked):
        """Set the new selection."""
        self.set_staged(staged)
        self.set_modified(modified)
        self.set_unmerged(unmerged)
        self.set_untracked(untracked)
        self.notify_message_observers(self.message_selection_changed)
