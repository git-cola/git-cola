# Copyright (c) 2008 David Aguilar
"""This handles saving complex settings such as bookmarks, etc.
"""

import os
import user
from cola.model import Model

class SettingsModel(Model):
    def __init__(self):
        Model.__init__(self)
        self.bookmarks = []
        settings = self.path()
        if os.path.exists(settings):
            self.load(settings)

    def path(self):
        return os.path.join(user.home, '.cola')

    def save_all_settings(self):
        self.save(self.path())
