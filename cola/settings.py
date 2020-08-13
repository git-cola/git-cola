"""Save settings, bookmarks, etc.
"""
from __future__ import division, absolute_import, unicode_literals
import json
import os
import sys

from . import core
from . import git
from . import resources


def mkdict(obj):
    """Transform None and non-dicts into dicts"""
    if isinstance(obj, dict):
        value = obj
    else:
        value = {}
    return value


def mklist(obj):
    """Transform None and non-lists into lists"""
    if isinstance(obj, list):
        value = obj
    elif isinstance(obj, tuple):
        value = list(obj)
    else:
        value = []
    return value


def read_json(path):
    try:
        with core.xopen(path, 'rt') as fp:
            return mkdict(json.load(fp))
    except (ValueError, TypeError, OSError, IOError):  # bad path or json
        return {}


def write_json(values, path):
    try:
        parent = os.path.dirname(path)
        if not core.isdir(parent):
            core.makedirs(parent)
        with core.xopen(path, 'wt') as fp:
            json.dump(values, fp, indent=4)
    except (ValueError, TypeError, OSError, IOError):
        sys.stderr.write('git-cola: error writing "%s"\n' % path)


class Settings(object):
    config_path = resources.config_home('settings')
    bookmarks = property(lambda self: mklist(self.values['bookmarks']))
    gui_state = property(lambda self: mkdict(self.values['gui_state']))
    recent = property(lambda self: mklist(self.values['recent']))
    copy_formats = property(lambda self: mklist(self.values['copy_formats']))

    def __init__(self, verify=git.is_git_worktree):
        """Load existing settings if they exist"""
        self.values = {
            'bookmarks': [],
            'gui_state': {},
            'recent': [],
            'copy_formats': [],
        }
        self.verify = verify

    def remove_missing(self):
        self.remove_missing_bookmarks()
        self.remove_missing_recent()

    def remove_missing_bookmarks(self):
        missing_bookmarks = []
        for bookmark in self.bookmarks:
            if not self.verify(bookmark['path']):
                missing_bookmarks.append(bookmark)

        for bookmark in missing_bookmarks:
            try:
                self.bookmarks.remove(bookmark)
            except ValueError:
                pass

    def remove_missing_recent(self):
        missing_recent = []
        for recent in self.recent:
            if not self.verify(recent['path']):
                missing_recent.append(recent)

        for recent in missing_recent:
            try:
                self.recent.remove(recent)
            except ValueError:
                pass

    def add_bookmark(self, path, name):
        """Adds a bookmark to the saved settings"""
        bookmark = {'path': path, 'name': name}
        if bookmark not in self.bookmarks:
            self.bookmarks.append(bookmark)

    def remove_bookmark(self, path, name):
        """Remove a bookmark"""
        bookmark = {'path': path, 'name': name}
        try:
            self.bookmarks.remove(bookmark)
        except ValueError:
            pass

    def rename_bookmark(self, path, name, new_name):
        return rename_entry(self.bookmarks, path, name, new_name)

    def add_recent(self, path, max_recent):
        try:
            index = [recent['path'] for recent in self.recent].index(path)
            entry = self.recent.pop(index)
        except (IndexError, ValueError):
            entry = {
                'name': os.path.basename(path),
                'path': path,
            }
        self.recent.insert(0, entry)
        if len(self.recent) > max_recent:
            self.recent.pop()

    def remove_recent(self, path):
        """Removes an item from the recent items list"""
        try:
            index = [recent.get('path', '') for recent in self.recent].index(path)
        except ValueError:
            return
        try:
            self.recent.pop(index)
        except IndexError:
            return

    def rename_recent(self, path, name, new_name):
        return rename_entry(self.recent, path, name, new_name)

    def path(self):
        return self.config_path

    def save(self):
        write_json(self.values, self.path())

    def load(self):
        self.values.update(self.asdict())
        self.upgrade_settings()

    def upgrade_settings(self):
        """Upgrade git-cola settings"""
        # Upgrade bookmarks to the new dict-based bookmarks format.
        if self.bookmarks and not isinstance(self.bookmarks[0], dict):
            bookmarks = [
                dict(name=os.path.basename(path), path=path) for path in self.bookmarks
            ]
            self.values['bookmarks'] = bookmarks

        if self.recent and not isinstance(self.recent[0], dict):
            recent = [
                dict(name=os.path.basename(path), path=path) for path in self.recent
            ]
            self.values['recent'] = recent

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


def rename_entry(entries, path, name, new_name):
    entry = {'name': name, 'path': path}
    try:
        index = entries.index(entry)
    except ValueError:
        return False

    if all([item['name'] != new_name for item in entries]):
        entries[index]['name'] = new_name
        return True

    return False


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
            except (OSError, ValueError):
                pass
            return True
        return False
