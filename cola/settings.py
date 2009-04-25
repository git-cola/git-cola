# Copyright (c) 2008 David Aguilar
"""This handles saving complex settings such as bookmarks, etc.
"""

import os
import user

from cola.model import Model
from cola import observable

class SettingsModel(Model, observable.Observable):
    def __init__(self):
        """Load existing settings if they exist"""
        Model.__init__(self)
        observable.Observable.__init__(self)
        self.bookmarks = []
        self.load()

    def path(self):
        """Path to the model's on-disk representation"""
        return os.path.join(user.home, '.cola')

    def load(self):
        """Loads settings if they exist"""
        settings = self.path()
        if os.path.exists(settings):
            Model.load(self, settings)

    def save(self):
        """Saves settings to the .cola file"""
        notify = self.get_notify()
        observers = self.get_observers()

        del self._notify
        del self._observers

        # Call the base method
        Model.save(self, self.path())

        # Restore properties
        self.set_notify(notify)
        self.set_observers(observers)
