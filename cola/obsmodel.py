from cola.observable import Observable
from cola.basemodel import BaseModel as Model


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
