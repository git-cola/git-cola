# Copyright (c) 2008 David Aguilar
"""This module provides the Observable class"""

import types

class Observable(object):
    """Handles subject/observer notifications."""
    def __init__(self):
        self.observers = set()
        self.message_observers = {}
        self.notification_enabled = True
        self.register_messages()

    def register_messages(self, messages=None):
        """
        Automatically register all class-scope message names.

        There are two rules at play here:

        1. Message names must be defined at class scope. e.g.:

            class Foo(object):
                message_foo = 'foo'

        2. Message name variables must begin with the string 'message_'

        Providing a 'messages' dict avoids this built-in behavior but
        does not guarantee that the messages names are registered for
        clones or unserialized objects.

        """
        if messages:
            self.message_observers.update(messages)
        else:
            for k, v in self.__class__.__dict__.iteritems():
                if k.startswith('message_') and type(v) in types.StringTypes:
                    self.message_observers[v] = set()

    def add_observer(self, observer):
        """Adds an observer to this model"""
        self.observers.add(observer)

    def add_message_observer(self, message, observer):
        """Add an observer for a specific message."""
        observers = self.message_observers.setdefault(message, set())
        observers.add(observer)

    def remove_observer(self, observer):
        """Removes an observer"""
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

    def notify_message_observers(self, message, **opts):
        """Notifies message observers."""
        if not self.notification_enabled:
            return
        if message not in self.message_observers:
            raise ValueError('%s is not a valid message name.' % message)
        observers = self.message_observers[message]
        for method in observers:
            method(self, message, **opts)
