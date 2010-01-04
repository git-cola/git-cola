# Copyright (c) 2008 David Aguilar
"""This module provides the Observable class"""

import types
from cola.compat import set

class Observable(object):
    """Handles subject/observer notifications."""
    def __init__(self):
        self.observers = set()
        self.message_observers = {}
        self.notification_enabled = True

    def add_observer(self, observer):
        """Adds an observer to this model"""
        self.observers.add(observer)

    def add_message_observer(self, message, observer):
        """Add an observer for a specific message."""
        observers = self.message_observers.setdefault(message, set())
        observers.add(observer)

    def remove_observer(self, observer):
        """Remove an observer."""
        if observer in self.observers:
            self.observers.remove(observer)
        for message, observers in self.message_observers.items():
            if observer in observers:
                observers.remove(observer)

    def notify_observers(self, *param):
        """Notifies observers about attribute changes"""
        if not self.notification_enabled:
            return
        for observer in self.observers:
            observer.notify(*param)

    def notify_message_observers(self, message, *args, **opts):
        """Pythonic signals and slots."""
        if not self.notification_enabled:
            return
        observers = self.message_observers.get(message, ())
        for method in observers:
            method(*args, **opts)
