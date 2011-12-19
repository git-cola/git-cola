# Copyright (c) 2008 David Aguilar
"""This module provides the Observable class"""

from cola.compat import set

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
        for message, observers in self.observers.items():
            if observer in observers:
                observers.remove(observer)

    def notify_observers(self, message, *args, **opts):
        """Pythonic signals and slots."""
        if not self.notification_enabled:
            return
        observers = self.observers.get(message, ())
        for method in observers:
            method(*args, **opts)
