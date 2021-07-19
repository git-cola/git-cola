"""Save settings, bookmarks, etc."""
from __future__ import absolute_import, division, print_function, unicode_literals
import json
import os
import sys

from . import core
from . import display
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

    def remove_missing_bookmarks(self):
        """Remove "favorites" bookmarks that no longer exist"""
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
        """Remove "recent" repositories that no longer exist"""
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
        bookmark = {'path': display.normalize_path(path), 'name': name}
        if bookmark not in self.bookmarks:
            self.bookmarks.append(bookmark)

    def remove_bookmark(self, path, name):
        """Remove a bookmark"""
        bookmark = {'path': display.normalize_path(path), 'name': name}
        try:
            self.bookmarks.remove(bookmark)
        except ValueError:
            pass

    def rename_bookmark(self, path, name, new_name):
        return rename_entry(self.bookmarks, path, name, new_name)

    def add_recent(self, path, max_recent):
        normalize = display.normalize_path
        path = normalize(path)
        try:
            index = [normalize(recent['path']) for recent in self.recent].index(path)
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
        normalize = display.normalize_path
        path = normalize(path)
        try:
            index = [normalize(recent.get('path', '')) for recent in self.recent].index(
                path
            )
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

    def load(self, path=None):
        self.values.update(self.asdict(path=path))
        self.upgrade_settings()
        return True

    @staticmethod
    def read(verify=git.is_git_worktree):
        """Load settings from disk"""
        settings = Settings(verify=verify)
        settings.load()
        return settings

    def upgrade_settings(self):
        """Upgrade git-cola settings"""
        # Upgrade bookmarks to the new dict-based bookmarks format.
        normalize = display.normalize_path
        if self.bookmarks and not isinstance(self.bookmarks[0], dict):
            bookmarks = [
                dict(name=os.path.basename(path), path=normalize(path))
                for path in self.bookmarks
            ]
            self.values['bookmarks'] = bookmarks

        if self.recent and not isinstance(self.recent[0], dict):
            recent = [
                dict(name=os.path.basename(path), path=normalize(path))
                for path in self.recent
            ]
            self.values['recent'] = recent

    def asdict(self, path=None):
        if not path:
            path = self.path()
        if core.exists(path):
            return read_json(path)
        # We couldn't find ~/.config/git-cola, try ~/.cola
        values = {}
        path = os.path.join(core.expanduser('~'), '.cola')
        if core.exists(path):
            json_values = read_json(path)
            for key in self.values:
                try:
                    values[key] = json_values[key]
                except KeyError:
                    pass
        # Ensure that all stored bookmarks use normalized paths ("/" only).
        normalize = display.normalize_path
        for entry in values.get('bookmarks', []):
            entry['path'] = normalize(entry['path'])
        for entry in values.get('recent', []):
            entry['path'] = normalize(entry['path'])
        return values

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
    normalize = display.normalize_path
    path = normalize(path)
    entry = {'name': name, 'path': path}
    try:
        index = entries.index(entry)
    except ValueError:
        return False

    if all(item['name'] != new_name for item in entries):
        entries[index]['name'] = new_name
        result = True
    else:
        result = False
    return result


class Session(Settings):
    """Store per-session settings

    XDG sessions are created by the QApplication::commitData() callback.
    These sessions are stored once, and loaded once.  They are deleted once
    loaded.  The behavior of path() is such that it forgets its session path()
    and behaves like a return Settings object after the session has been
    loaded once.

    Once the session is loaded, it is removed and further calls to save()
    will save to the usual $XDG_CONFIG_HOME/git-cola/settings location.

    """

    _sessions_dir = resources.config_home('sessions')

    repo = property(lambda self: self.values['repo'])

    def __init__(self, session_id, repo=None):
        Settings.__init__(self)
        self.session_id = session_id
        self.values.update({'repo': repo})
        self.expired = False

    def session_path(self):
        """The session-specific session file"""
        return os.path.join(self._sessions_dir, self.session_id)

    def path(self):
        base_path = super(Session, self).path()
        if self.expired:
            path = base_path
        else:
            path = self.session_path()
            if not os.path.exists(path):
                path = base_path
        return path

    def load(self, path=None):
        """Load the session and expire it for future loads

        The session should be loaded only once.  We remove the session file
        when it's loaded, and set the session to be expired.  This results in
        future calls to load() and save() using the default Settings path
        rather than the session-specific path.

        The use case for sessions is when the user logs out with apps running.
        We will restore their state, and if they then shutdown, it'll be just
        like a normal shutdown and settings will be stored to
        ~/.config/git-cola/settings instead of the session path.

        This is accomplished by "expiring" the session after it has
        been loaded initially.

        """
        result = super(Session, self).load(path=path)
        # This is the initial load, so expire the session and remove the
        # session state file.  Future calls will be equivalent to
        # Settings.load().
        if not self.expired:
            self.expired = True
            path = self.session_path()
            if core.exists(path):
                try:
                    os.unlink(path)
                except (OSError, ValueError):
                    pass
                return True
            return False

        return result

    def update(self):
        """Reload settings from the base settings path"""
        # This method does not expire the session.
        path = super(Session, self).path()
        return super(Session, self).load(path=path)
