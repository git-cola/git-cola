import copy

from cola.model import Model
from cola.observable import Observable

_unserializable_attributes = {
    'observers': set(),
    'message_observers': {},
    'notification_enabled': True,
}

class ObservableModel(Model, Observable):
    """Combines serialization from Model with the Observer pattern"""
    def __init__(self):
        Model.__init__(self)
        Observable.__init__(self)

    def save(self, path):
        """
        Saves state to a file.  Overrides the base method.

        Hides internal observable attributes when serializing.

        """
        attributes = self.remove_unserializable_attributes()
        Model.save(self, path)
        self.restore_unserializable_attributes(attributes)

    def clone(self):
        """Override Model.clone() to handle observers"""
        # Go in and out of jsonpickle to create a clone
        attributes = self.remove_unserializable_attributes()
        clone = Model.clone(self)
        unserializable_copy = copy.deepcopy(_unserializable_attributes)
        self.restore_unserializable_attributes(attributes)
        clone.restore_unserializable_attributes(unserializable_copy)
        clone.register_messages(messages=self.message_observers)
        return clone

    def set_param(self, param, value, notify=True):
        """Override Model.set_param() to handle notification"""
        Model.set_param(self, param, value)
        # Perform notifications
        if notify:
            self.notify_observers(param)

    def remove_unserializable_attributes(self):
        """Remove unserializable instance attributes."""
        attributes = {}
        for attribute in _unserializable_attributes:
            attributes[attribute] = self.__dict__.pop(attribute)
        return attributes

    def restore_unserializable_attributes(self, attributes):
        """Restores unserializable instance attributes."""
        # Restore properties
        self.__dict__.update(attributes)

    @staticmethod
    def instance(path):
        """Override Model.instance() to account for unserializable data."""
        obj = Model.instance(path)
        if isinstance(obj, ObservableModel):
            unserializable_copy = copy.deepcopy(_unserializable_attributes)
            obj.restore_unserializable_attributes(unserializable_copy)
            obj.register_messages()
        return obj
