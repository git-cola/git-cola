from cola.model import Model
from cola.observable import Observable

class ObservableModel(Model, Observable):
    """Combines serialization from Model with the Observer pattern"""
    def __init__(self):
        Model.__init__(self)
        Observable.__init__(self)

    def save(self, path):
        """Saves state to a file.  Overrides the base method

        Hides internal observable attributes when serializing.
        """
        notify, observers = self._remove_internals()
        Model.save(self, path)
        self._restore_internals(notify, observers)

    def clone(self):
        """Override Model.clone() to handle observers"""
        # Go in and out of jsonpickle to create a clone
        notify, observers = self._remove_internals()
        clone = Model.clone(self)
        self._restore_internals(notify, observers)
        clone.set_observers([])
        clone.set_notify(True)
        return clone

    def set_param(self, param, value, notify=True, check_params=False):
        """Override Model.set_param() to handle notification"""
        Model.set_param(self, param, value, check_params=check_params)
        # Perform notifications
        if notify:
            self.notify_observers(param)

    def _remove_internals(self):
        notify = self.get_notify()
        observers = self.get_observers()
        del self._notify
        del self._observers
        return notify, observers

    def _restore_internals(self, notify, observers):
        # Restore properties
        self.set_notify(notify)
        self.set_observers(observers)
