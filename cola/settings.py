# Copyright (c) 2008 David Aguilar
"""This handles saving complex settings such as bookmarks, etc.
"""

import os
import user
from cola.model import Model

class SettingsModel(Model):
    def __init__(self):
        """Load existing settings if they exist"""
        Model.__init__(self)
        self.bookmarks = []
        self.load_settings()

    def path(self):
        """Path to the model's on-disk representation"""
        return os.path.join(user.home, '.cola')

    def load_settings(self):
        """Loads settings if they exist"""
        settings = self.path()
        if os.path.exists(settings):
            self.load(settings)

    def save_settings(self):
        """Saves settings to the .cola file"""
        self.save(self.path())
