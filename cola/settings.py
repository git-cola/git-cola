# Copyright (c) 2008 David Aguilar
"""This handles saving complex settings such as bookmarks, etc.
"""

import os
import sys

from cola import core
from cola import git
from cola import resources
from cola.compat import json


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
    _file = resources.config_home('settings')
    bookmarks = property(lambda self: mklist(self.values['bookmarks']))
    gui_state = property(lambda self: mkdict(self.values['gui_state']))
    recent = property(lambda self: mklist(self.values['recent']))

    def __init__(self, verify=git.is_git_worktree):
        """Load existing settings if they exist"""
        self.values = {
                'bookmarks': [],
                'gui_state': {},
                'recent': [],
        }
        self.verify = verify
        self.load()
        self.remove_missing()

    def remove_missing(self):
        missing_bookmarks = []
        missing_recent = []

        for bookmark in self.bookmarks:
            if not self.verify(bookmark):
                missing_bookmarks.append(bookmark)

        for bookmark in missing_bookmarks:
            try:
                self.bookmarks.remove(bookmark)
            except:
                pass

        for recent in self.recent:
            if not self.verify(recent):
                missing_recent.append(recent)

        for recent in missing_recent:
            try:
                self.recent.remove(recent)
            except:
                pass

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
            if not core.isdir(parent):
                core.makedirs(parent)
            with core.xopen(path, 'wb') as fp:
                json.dump(self.values, fp, indent=4)
        except:
            sys.stderr.write('git-cola: error writing "%s"\n' % path)

    def load(self):
        self.values.update(self._load())

    def _load(self):
        path = self.path()
        if not core.exists(path):
            return self._load_dot_cola()
        try:
            fp = core.xopen(path, 'rb')
            return mkdict(json.load(fp))
        except: # bad json
            return {}

    def reload_recent(self):
        values = self._load()
        self.values['recent'] = mklist(values.get('recent', []))

    def _load_dot_cola(self):
        values = {}
        path = os.path.join(core.expanduser('~'), '.cola')
        if not core.exists(path):
            return {}
        try:
            with core.xopen(path, 'r') as fp:
                json_values = json.load(fp)
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
