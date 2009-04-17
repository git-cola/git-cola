# Copyright (c) 2008 David Aguilar
"""This module provides the Observable class"""

class Observable(object):
    """Handles subject/observer notifications."""
    def __init__(self):
        self._observers = []
        self._notify = True

    def get_observers(self):
        """Returns the observer list"""
        return self._observers

    def set_observers(self, observers):
        """Sets the observer list"""
        self._observers = observers

    def get_notify(self):
        """Returns True if notification is enabled"""
        return self._notify

    def set_notify(self, notify=True):
        """Sets the notification state (bool)"""
        self._notify = notify

    def add_observer(self, observer):
        """Adds an observer to this model"""
        if observer not in self._observers:
            self._observers.append(observer)

    def remove_observer(self, observer):
        """Removes an observer"""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify_observers(self, *param):
        """Notifies observers about attribute changes"""
        if not self._notify:
            return
        for observer in self._observers:
            observer.notify(*param)
