# Copyright (c) 2008 David Aguilar
"""This handles saving complex settings such as bookmarks, etc.
"""
from __future__ import division, absolute_import, unicode_literals

import os
import sys

from cola import core
from cola import git
from cola import resources
import json


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


def read_json(path):
    try:
        with core.xopen(path, 'rt') as fp:
            return mkdict(json.load(fp))
    except: # bad path or json
        return {}


def write_json(values, path):
    try:
        parent = os.path.dirname(path)
        if not core.isdir(parent):
            core.makedirs(parent)
        with core.xopen(path, 'wt') as fp:
            json.dump(values, fp, indent=4)
    except:
        sys.stderr.write('git-cola: error writing "%s"\n' % path)


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
        """Remove a bookmark"""
        if bookmark in self.bookmarks:
            self.bookmarks.remove(bookmark)

    def remove_recent(self, entry):
        """Removes an item from the recent items list"""
        if entry in self.recent:
            self.recent.remove(entry)

    def add_recent(self, entry):
        if entry in self.recent:
            self.recent.remove(entry)
        self.recent.insert(0, entry)
        if len(self.recent) >= 8:
            self.recent.pop()

    def path(self):
        return self._file

    def save(self):
        write_json(self.values, self.path())

    def load(self):
        self.values.update(self.asdict())
        self.remove_missing()

    def asdict(self):
        path = self.path()
        if core.exists(path):
            return read_json(path)
        # We couldn't find ~/.config/git-cola, try ~/.cola
        values = {}
        path = os.path.join(core.expanduser('~'), '.cola')
        if core.exists(path):
            json_values = read_json(path)
            # Keep only the entries we care about
            for key in self.values:
                try:
                    values[key] = json_values[key]
                except KeyError:
                    pass
        return values

    def reload_recent(self):
        values = self.asdict()
        self.values['recent'] = mklist(values.get('recent', []))

    def save_gui_state(self, gui):
        """Saves settings for a cola view"""
        name = gui.name()
        self.gui_state[name] = mkdict(gui.export_state())
        self.save()

    def get_gui_state(self, gui):
        """Returns the saved state for a gui"""
        try:
            state = mkdict(self.gui_state[gui.name()])
        except KeyError:
            state = self.gui_state[gui.name()] = {}
        return state


class Session(Settings):
    """Store per-session settings"""

    _sessions_dir = resources.config_home('sessions')

    repo = property(lambda self: self.values['repo'])

    def __init__(self, session_id, repo=None):
        Settings.__init__(self)
        self.session_id = session_id
        self.values.update({'repo': repo})

    def path(self):
        return os.path.join(self._sessions_dir, self.session_id)

    def load(self):
        path = self.path()
        if core.exists(path):
            self.values.update(read_json(path))
            try:
                os.unlink(path)
            except:
                pass
            return True
        return False
