# Copyright (c) 2008 David Aguilar
"""This module provides the Observer design pattern.
"""

class Observer(object):
    """Implements the Observer pattern for a single subject"""

    def __init__(self, model):
        self.model = model
        self.model.add_observer(self)

    def __del__(self):
        self.model.remove_observer(self)

    def notify(self, *attributes):
        """Called by the model to notify Observers about changes."""
        # We can be notified about multiple attribute changes at once
        model = self.model
        for attr in attributes:
            notify = model.get_notify()
            model.set_notify(False) # NOTIFY OFF

            value = model.get_param(attr)
            self.subject_changed(attr, value)

            model.set_notify(notify) # NOTIFY ON

    def subject_changed(self, attr, value):
        """
        Updates the observer/view

        This must be implemented by concrete observers class.
        """

        msg = 'Concrete Observers must override subject_changed().'
        raise NotImplementedError(msg)
