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


def mkdict(obj):
    if type(obj) is dict:
        return obj
    else:
        return {}


def mklist(obj):
    if type(obj) is list:
        return obj
    else:
        return []


def xdg_config_home(*args):
    config = os.getenv('XDG_CONFIG_HOME',
                       os.path.join(os.path.expanduser('~'), '.config'))
    return os.path.join(config, 'git-cola', *args)


class Settings(object):
    _file = xdg_config_home('settings')

    def __init__(self):
        """Load existing settings if they exist"""
        self.values = {}
        self.load()

    # properties
    def _get_bookmarks(self):
        try:
            bookmarks = mklist(self.values['bookmarks'])
        except KeyError:
            bookmarks = self.values['bookmarks'] = []
        return bookmarks

    def _get_gui_state(self):
        try:
            gui_state = mkdict(self.values['gui_state'])
        except KeyError:
            gui_state = self.values['gui_state'] = {}
        return gui_state

    def _get_recent(self):
        try:
            recent = mklist(self.values['recent'])
        except KeyError:
            recent = self.values['recent'] = []
        return recent

    bookmarks = property(_get_bookmarks)
    gui_state = property(_get_gui_state)
    recent = property(_get_recent)

    def add_bookmark(self, bookmark):
        """Adds a bookmark to the saved settings"""
        if bookmark not in self.bookmarks:
            self.bookmarks.append(bookmark)

    def remove_bookmark(self, bookmark):
        """Removes a bookmark from the saved settings"""
        if bookmark in self.bookmarks:
            self.bookmarks.remove(bookmark)

    def add_recent(self, entry):
        if entry in self.recent:
            self.recent.remove(entry)
        self.recent.insert(0, entry)
        if len(self.recent) > 8:
            self.recent.pop()

    def path(self):
        return self._file

    def save(self):
        path = self.path()
        try:
            parent = os.path.dirname(path)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            fp = open(path, 'wb')
            json.dump(self.values, fp, indent=4)
            fp.close()
        except:
            sys.stderr.write('git-cola: error writing "%s"\n' % path)

    def load(self):
        self.values = self._load()

    def _load(self):
        path = self.path()
        if not os.path.exists(path):
            return self.load_dot_cola(path)
        try:
            fp = open(path, 'rb')
            return mkdict(json.load(fp))
        except: # bad json
            return {}

    def reload_recent(self):
        values = self._load()
        try:
            self.values['recent'] = mklist(values['recent'])
        except KeyError:
            pass

    def load_dot_cola(self, path):
        values = {}
        path = os.path.join(os.path.expanduser('~'), '.cola')
        if not os.path.exists(path):
            return values
        try:
            fp = open(path, 'rb')
            values = json.load(fp)
            fp.close()
        except: # bad json
            return values
        for key in ('bookmarks', 'gui_state'):
            try:
                values[key] = values[key]
            except KeyError:
                pass
        return values

    def save_gui_state(self, gui):
        """Saves settings for a cola view"""
        name = gui.name()
        self.gui_state[name] = mkdict(gui.export_state())
        self.save()

    def get_gui_state(self, gui):
        """Returns the state for a gui"""
        try:
            state = mkdict(self.gui_state[gui.name()])
        except KeyError:
            state = self.gui_state[gui.name()] = {}
        return state
