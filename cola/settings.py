"""Save settings, bookmarks, etc."""
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
        with core.open_read(path) as f:
            return mkdict(json.load(f))
    except (ValueError, TypeError, OSError):  # bad path or json
        return {}


def write_json(values, path, sync=True):
    """Write the specified values dict to a JSON file at the specified path"""
    try:
        parent = os.path.dirname(path)
        if not core.isdir(parent):
            core.makedirs(parent)
        with core.open_write(path) as fp:
            json.dump(values, fp, indent=4)
            if sync:
                core.fsync(fp.fileno())
    except (ValueError, TypeError, OSError):
        sys.stderr.write('git-cola: error writing "%s"\n' % path)
        return False
    return True


def rename_path(old, new):
    """Rename a filename. Catch exceptions and return False on error."""
    try:
        core.rename(old, new)
    except OSError:
        sys.stderr.write(f'git-cola: error renaming "{old}" to "{new}"\n')
        return False
    return True


def remove_path(path):
    """Remove a filename. Report errors to stderr."""
    try:
        core.remove(path)
    except OSError:
        sys.stderr.write('git-cola: error removing "%s"\n' % path)


class Settings:
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

    def save(self, sync=True):
        """Write settings robustly to avoid losing data during a forced shutdown.

        To save robustly we take these steps:
          * Write the new settings to a .tmp file.
          * Rename the current settings to a .bak file.
          * Rename the new settings from .tmp to the settings file.
          * Flush the data to disk
          * Delete the .bak file.

        Cf. https://github.com/git-cola/git-cola/issues/1241
        """
        path = self.path()
        path_tmp = path + '.tmp'
        path_bak = path + '.bak'
        # Write the new settings to the .tmp file.
        if not write_json(self.values, path_tmp, sync=sync):
            return
        # Rename the current settings to a .bak file.
        if core.exists(path) and not rename_path(path, path_bak):
            return
        # Rename the new settings from .tmp to the settings file.
        if not rename_path(path_tmp, path):
            return
        # Delete the .bak file.
        if core.exists(path_bak):
            remove_path(path_bak)

    def load(self, path=None):
        """Load settings robustly.

        Attempt to load settings from the .bak file if it exists since it indicates
        that the program terminated before the data was flushed to disk. This can
        happen when a machine is force-shutdown, for example.

        This follows the strategy outlined in issue #1241. If the .bak file exists
        we use it, otherwise we fallback to the actual path or the .tmp path as a
        final last-ditch attempt to recover settings.

        """
        if path is None:
            path = self.path()
        path_bak = path + '.bak'
        path_tmp = path + '.tmp'

        if core.exists(path_bak):
            self.values.update(self.asdict(path=path_bak))
        elif core.exists(path):
            self.values.update(self.asdict(path=path))
        elif core.exists(path_tmp):
            # This is potentially dangerous, but it's guarded by the fact that the
            # file must be valid JSON in order otherwise the reader will return an
            # empty string, thus making this a no-op.
            self.values.update(self.asdict(path=path_tmp))
        else:
            # This is either a new installation or the settings were lost.
            pass
        # We could try to remove the .bak and .tmp files, but it's better to set save()
        # handle that the next time it succeeds.
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
                {'name': os.path.basename(path), 'path': normalize(path)}
                for path in self.bookmarks
            ]
            self.values['bookmarks'] = bookmarks

        if self.recent and not isinstance(self.recent[0], dict):
            recent = [
                {'name': os.path.basename(path), 'path': normalize(path)}
                for path in self.recent
            ]
            self.values['recent'] = recent

    def asdict(self, path=None):
        if not path:
            path = self.path()
        if core.exists(path):
            values = read_json(path)
        else:
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

    def save_gui_state(self, gui, sync=True):
        """Saves settings for a widget"""
        name = gui.name()
        self.gui_state[name] = mkdict(gui.export_state())
        self.save(sync=sync)

    def get_gui_state(self, gui):
        """Returns the saved state for a tool"""
        return self.get(gui.name())

    def get(self, gui_name):
        """Returns the saved state for a tool by name"""
        try:
            state = mkdict(self.gui_state[gui_name])
        except KeyError:
            state = self.gui_state[gui_name] = {}
        return state

    def get_value(self, name, key, default=None):
        """Return a specific setting value for the specified tool and setting key"""
        return self.get(name).get(key, default)

    def set_value(self, name, key, value, save=True, sync=True):
        """Store a specific setting value for the specified tool and setting key value"""
        values = self.get(name)
        values[key] = value
        if save:
            self.save(sync=sync)


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

    repo = property(lambda self: self.values['local'])

    def __init__(self, session_id, repo=None):
        Settings.__init__(self)
        self.session_id = session_id
        self.values.update({'local': repo})
        self.expired = False

    def session_path(self):
        """The session-specific session file"""
        return os.path.join(self._sessions_dir, self.session_id)

    def path(self):
        base_path = super().path()
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
        result = super().load(path=path)
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
        path = super().path()
        return super().load(path=path)
