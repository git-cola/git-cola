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
        self.gui_state = {}
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

    def set_gui_state(self, name, state):
        """Sets GUI state for a view"""
        self.gui_state[name] = state

    def get_gui_state(self, name):
        """Returns the state an gui"""
        return self.gui_state.get(name, {})

    def add_bookmark(self, bookmark):
        """Adds a bookmark to the saved settings"""
        if bookmark not in self.bookmarks:
            self.bookmarks.append(bookmark)

    def remove_bookmark(self, bookmark):
        """Removes a bookmark from the saved settings"""
        if bookmark in self.bookmarks:
            self.bookmarks.remove(bookmark)

class SettingsManager(object):
    """Manages a SettingsModel singleton
    """
    _settings = SettingsModel()

    @staticmethod
    def settings():
        """Returns the SettingsModel singleton"""
        return SettingsManager._settings

    @staticmethod
    def save_gui_state(gui):
        """Saves settings for a cola view"""
        name = gui.name()
        state = gui.export_state()
        model = SettingsManager.settings()
        model.set_gui_state(name, state)
        model.save()

    @staticmethod
    def get_gui_state(gui):
        """Returns the state for a gui"""
        return SettingsManager.settings().get_gui_state(gui.name())
