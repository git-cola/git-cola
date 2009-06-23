# Copyright (c) 2008 David Aguilar
"""This module provides the Observable class"""

class Observable(object):
    """Handles subject/observer notifications."""
    def __init__(self):
        self.observers = []
        self.notification_enabled = True

    def add_observer(self, observer):
        """Adds an observer to this model"""
        if observer not in self.observers:
            self.observers.append(observer)

    def remove_observer(self, observer):
        """Removes an observer"""
        if observer in self.observers:
            self.observers.remove(observer)

    def notify_observers(self, *param):
        """Notifies observers about attribute changes"""
        if not self.notification_enabled:
            return
        for observer in self.observers:
            observer.notify(*param)
