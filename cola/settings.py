#!/usr/bin/env python
# Copyright (c) 2008 David Aguilar
"""This handles saving complex settings such as bookmarks, etc.
"""

HAS_SIMPLEJSON = False
try:
    import simplejson
    HAS_SIMPLEJSON = True
except ImportError:
    pass

import os
import user
from cola.model import Model

class SettingsModel(Model):
    def init(self):
        self.create( bookmarks = [] )
        if not HAS_SIMPLEJSON:
            return
        settings = self.path()
        if os.path.exists(settings):
            self.load(settings)

    def path(self):
        return os.path.join(user.home, '.cola')
    
    def save_all_settings(self):
        if not HAS_SIMPLEJSON:
            return
        self.save(self.path())
