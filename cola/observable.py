"""The Observable class for decoupled notifications"""
from __future__ import absolute_import, division, print_function, unicode_literals


class Observable(object):
    """Handles subject/observer notifications."""

    def __init__(self):
        self.notification_enabled = True
        self.observers = {}

    def add_observer(self, message, observer):
        """Add an observer for a specific message."""
        observers = self.observers.setdefault(message, set())
        observers.add(observer)

    def remove_observer(self, observer):
        """Remove an observer."""
        for _, observers in self.observers.items():
            if observer in observers:
                observers.remove(observer)

    def notify_observers(self, message, *args, **opts):
        """Pythonic signals and slots."""
        if not self.notification_enabled:
            return
        # observers can remove themselves during their callback so grab a copy
        observers = set(self.observers.get(message, set()))
        for method in observers:
            method(*args, **opts)
