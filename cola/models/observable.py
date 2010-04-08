import copy

from cola import serializer
from cola.observable import Observable
from cola.models.base import BaseModel as Model
from cola.compat import set


class ObservableModel(Model, Observable):
    """Combines serialization from Model with the Observer pattern"""
    def __init__(self):
        Model.__init__(self)
        Observable.__init__(self)

    def set_param(self, param, value, notify=True):
        """Override Model.set_param() to handle notification"""
        Model.set_param(self, param, value)
        # Perform notifications
        if notify:
            self.notify_observers(param)


_unserializable_attributes = {
    'observers': set(),
    'message_observers': {},
    'notification_enabled': True,
}

class OMSerializer(object):
    """Hide the internal 'observers' fields from serialization"""
    def __init__(self, obj):
        self.obj = obj
        self.attributes = {}

    def pre_encode_hook(self):
        for attribute in _unserializable_attributes:
            self.attributes[attribute] = self.obj.__dict__.pop(attribute)

    def post_encode_hook(self):
        self.obj.__dict__.update(self.attributes)
        self.attributes = {}

    def post_decode_hook(self):
        self.obj.__dict__.update(copy.deepcopy(_unserializable_attributes))


# Add a hook for this object
serializer.handlers[ObservableModel] = OMSerializer
