#!/usr/bin/env python
# Copyright (c) 2008 David Aguilar
from pprint import pformat

class Observer(object):
    """
    Observers receive notify(*attributes) messages from their
    subjects whenever new data arrives.  This notify() message signifies
    that an observer should update its internal state/view.
    """

    def __init__(self, model):
        self.model = model
        self.model.add_observer(self)
        self.__debug = False

    def __del__(self):
        self.model.remove_observer(self)

    def set_debug(self, enabled):
        self.__debug = enabled

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
        """This method handles updating of the observer/UI.
        This must be implemented in each concrete observer class."""

        msg = 'Concrete Observers must override subject_changed().'
        raise NotImplementedError, msg
