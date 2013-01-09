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

from cola import xdg


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


class Settings(object):
    _file = xdg.config_home('settings')

    def __init__(self):
        """Load existing settings if they exist"""
        self.values = {
                'bookmarks': [],
                'gui_state': {},
                'recent': [],
        }
        self.load()

    # properties
    def _get_bookmarks(self):
        return mklist(self.values['bookmarks'])

    def _get_gui_state(self):
        return mkdict(self.values['gui_state'])

    def _get_recent(self):
        return mklist(self.values['recent'])

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
        self.values.update(self._load())

    def _load(self):
        path = self.path()
        if not os.path.exists(path):
            return self._load_dot_cola()
        try:
            fp = open(path, 'rb')
            return mkdict(json.load(fp))
        except: # bad json
            return {}

    def reload_recent(self):
        values = self._load()
        self.values['recent'] = mklist(values.get('recent', []))

    def _load_dot_cola(self):
        values = {}
        path = os.path.join(os.path.expanduser('~'), '.cola')
        if not os.path.exists(path):
            return {}
        try:
            fp = open(path, 'rb')
            json_values = json.load(fp)
            fp.close()
        except: # bad json
            return {}

        # Keep only the entries we care about
        for key in self.values:
            try:
                values[key] = json_values[key]
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
