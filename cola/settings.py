# Copyright (c) 2008 David Aguilar
"""This handles saving complex settings such as bookmarks, etc.
"""

import os
import sys
try:
    import simplejson
    json = simplejson
except ImportError:
    import json

from cola import core
from cola import serializer
from cola.obsmodel import ObservableModel


class SettingsModel(ObservableModel):
    def __init__(self):
        """Load existing settings if they exist"""
        ObservableModel.__init__(self)
        self.bookmarks = []
        self.gui_state = {}

    def add_bookmark(self, bookmark):
        """Adds a bookmark to the saved settings"""
        if bookmark not in self.bookmarks:
            self.bookmarks.append(bookmark)

    def remove_bookmark(self, bookmark):
        """Removes a bookmark from the saved settings"""
        if bookmark in self.bookmarks:
            self.bookmarks.remove(bookmark)


class Settings(object):
    _file = '~/.config/git-cola/settings'

    def __init__(self):
        """Load existing settings if they exist"""
        self.values = {}
        self.load()

    def _get_bookmarks(self):
        try:
            bookmarks = self.values['bookmarks']
        except KeyError:
            bookmarks = self.values['bookmarks'] = []
        return bookmarks

    def _get_guistate(self):
        try:
            gui_state = self.values['gui_state']
        except KeyError:
            gui_state = self.values['gui_state'] = {}
        return gui_state

    bookmarks = property(_get_bookmarks)
    gui_state = property(_get_guistate)

    def add_bookmark(self, bookmark):
        """Adds a bookmark to the saved settings"""
        if bookmark not in self.bookmarks:
            self.bookmarks.append(bookmark)

    def remove_bookmark(self, bookmark):
        """Removes a bookmark from the saved settings"""
        if bookmark in self.bookmarks:
            self.bookmarks.remove(bookmark)

    def path(self):
        return os.path.expanduser(Settings._file)

    def save(self):
        path = self.path()
        try:
            parent = os.path.dirname(path)
            if not os.path.isdir(parent):
                os.makedirs(parent)

            fp = open(path, 'wb')
            json.dump(self.values, fp)
            fp.close()
        except:
            sys.stderr.write('git-cola: error writing "%s"\n' % path)

    def load(self):
        path = self.path()
        if not os.path.exists(path):
            self.load_dot_cola(path)
            return
        try:
            fp = open(path, 'rb')
            self.values = json.load(fp)
        except: # bad json
            pass

    def load_dot_cola(self, path):
        path = os.path.join(os.path.expanduser('~'), '.cola')
        if not os.path.exists(path):
            return
        try:
            fp = open(path, 'rb')
            values = json.load(fp)
            fp.close()
        except: # bad json
            return
        for key in ('bookmarks', 'gui_state'):
            try:
                self.values[key] = values[key]
            except KeyError:
                pass

    def save_gui_state(self, gui):
        """Saves settings for a cola view"""
        name = gui.name()
        state = gui.export_state()
        self.gui_state[name] = state
        self.save()

    def gui_state(self, gui):
        """Returns the state for a gui"""
        try:
            state = self.gui_state[gui.name()]
        except KeyError:
            state = self.gui_state[gui.name()] = {}
        return state


class SettingsManager(object):
    """Manages a SettingsModel singleton
    """
    _settings = None

    # Here we store settings
    _rcfile = os.path.join(core.decode(os.path.expanduser('~')), '.cola')

    @staticmethod
    def settings():
        """Returns the SettingsModel singleton"""
        if not SettingsManager._settings:
            if os.path.exists(SettingsManager._rcfile):
                try:
                    SettingsManager._settings = serializer.load(SettingsManager._rcfile)
                except: # bad json
                    SettingsManager._settings = SettingsModel()
            else:
                SettingsManager._settings = SettingsModel()
        return SettingsManager._settings

    @staticmethod
    def save_gui_state(gui):
        """Saves settings for a cola view"""
        name = gui.name()
        state = gui.export_state()
        model = SettingsManager.settings()
        model.gui_state[name] = state
        SettingsManager.save()

    @staticmethod
    def gui_state(gui):
        """Returns the state for a gui"""
        return SettingsManager.settings().gui_state.get(gui.name(), {})

    @staticmethod
    def save():
        model = SettingsManager.settings()
        serializer.save(model, SettingsManager._rcfile)
