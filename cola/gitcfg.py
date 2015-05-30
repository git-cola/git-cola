from __future__ import division, absolute_import, unicode_literals

import copy
import fnmatch
import os
import re
import struct
from binascii import unhexlify
from os.path import join

from cola import core
from cola import git
from cola import observable
from cola.decorators import memoize
from cola.git import STDOUT
from cola.compat import ustr

BUILTIN_READER = os.environ.get('GIT_COLA_BUILTIN_CONFIG_READER', False)

_USER_CONFIG = core.expanduser(join('~', '.gitconfig'))
_USER_XDG_CONFIG = core.expanduser(
        join(core.getenv('XDG_CONFIG_HOME', join('~', '.config')),
             'git', 'config'))

@memoize
def current():
    """Return the GitConfig singleton."""
    return GitConfig()


def _stat_info():
    # Try /etc/gitconfig as a fallback for the system config
    paths = (('system', '/etc/gitconfig'),
             ('user', _USER_XDG_CONFIG),
             ('user', _USER_CONFIG),
             ('repo', git.current().git_path('config')))
    statinfo = []
    for category, path in paths:
        try:
            statinfo.append((category, path, core.stat(path).st_mtime))
        except OSError:
            continue
    return statinfo


def _cache_key():
    # Try /etc/gitconfig as a fallback for the system config
    paths = ('/etc/gitconfig',
             _USER_XDG_CONFIG,
             _USER_CONFIG,
             git.current().git_path('config'))
    mtimes = []
    for path in paths:
        try:
            mtimes.append(core.stat(path).st_mtime)
        except OSError:
            continue
    return mtimes


def _config_to_python(v):
    """Convert a Git config string into a Python value"""

    if v in ('true', 'yes'):
        v = True
    elif v in ('false', 'no'):
        v = False
    else:
        try:
            v = int(v)
        except ValueError:
            pass
    return v


def _config_key_value(line, splitchar):
    """Split a config line into a (key, value) pair"""

    try:
        k, v = line.split(splitchar, 1)
    except ValueError:
        # the user has a emptyentry in their git config,
        # which Git interprets as meaning "true"
        k = line
        v = 'true'
    return k, _config_to_python(v)


class GitConfig(observable.Observable):
    """Encapsulate access to git-config values."""

    message_user_config_changed = 'user_config_changed'
    message_repo_config_changed = 'repo_config_changed'

    def __init__(self):
        observable.Observable.__init__(self)
        self.git = git.current()
        self._map = {}
        self._system = {}
        self._user = {}
        self._user_or_system = {}
        self._repo = {}
        self._all = {}
        self._cache_key = None
        self._configs = []
        self._config_files = {}
        self._value_cache = {}
        self._attr_cache = {}
        self._find_config_files()

    def reset(self):
        self._map.clear()
        self._system.clear()
        self._user.clear()
        self._user_or_system.clear()
        self._repo.clear()
        self._all.clear()
        self._cache_key = None
        self._configs = []
        self._config_files.clear()
        self._value_cache = {}
        self._attr_cache = {}
        self._find_config_files()

    def user(self):
        return copy.deepcopy(self._user)

    def repo(self):
        return copy.deepcopy(self._repo)

    def all(self):
        return copy.deepcopy(self._all)

    def _find_config_files(self):
        """
        Classify git config files into 'system', 'user', and 'repo'.

        Populates self._configs with a list of the files in
        reverse-precedence order.  self._config_files is populated with
        {category: path} where category is one of 'system', 'user', or 'repo'.

        """
        # Try the git config in git's installation prefix
        statinfo = _stat_info()
        self._configs = map(lambda x: x[1], statinfo)
        self._config_files = {}
        for (cat, path, mtime) in statinfo:
            self._config_files[cat] = path

    def update(self):
        """Read config values from git."""
        if self._cached():
            return
        self._read_configs()

    def _cached(self):
        """
        Return True when the cache matches.

        Updates the cache and returns False when the cache does not match.

        """
        cache_key = _cache_key()
        if self._cache_key is None or cache_key != self._cache_key:
            self._cache_key = cache_key
            return False
        return True

    def _read_configs(self):
        """Read git config value into the system, user and repo dicts."""
        self._map.clear()
        self._system.clear()
        self._user.clear()
        self._user_or_system.clear()
        self._repo.clear()
        self._all.clear()

        if 'system' in self._config_files:
            self._system.update(
                    self.read_config(self._config_files['system']))

        if 'user' in self._config_files:
            self._user.update(
                    self.read_config(self._config_files['user']))

        if 'repo' in self._config_files:
            self._repo.update(
                    self.read_config(self._config_files['repo']))

        for dct in (self._system, self._user):
            self._user_or_system.update(dct)

        for dct in (self._system, self._user, self._repo):
            self._all.update(dct)

    def read_config(self, path):
        """Return git config data from a path as a dictionary."""

        if BUILTIN_READER:
            return self._read_config_file(path)

        dest = {}
        args = ('--null', '--file', path, '--list')
        config_lines = self.git.config(*args)[STDOUT].split('\0')
        for line in config_lines:
            if not line:
                # the user has an invalid entry in their git config
                continue
            k, v = _config_key_value(line, '\n')
            self._map[k.lower()] = k
            dest[k] = v
        return dest

    def _read_config_file(self, path):
        """Read a .gitconfig file into a dict"""

        config = {}
        header_simple = re.compile(r'^\[(\s+)]$')
        header_subkey = re.compile(r'^\[(\s+) "(\s+)"\]$')

        with core.xopen(path, 'rt') as f:
            lines = filter(bool, [line.strip() for line in f.readlines()])

        prefix = ''
        for line in lines:
            if line.startswith('#'):
                continue

            match = header_simple.match(line)
            if match:
                prefix = match.group(1) + '.'
                continue
            match = header_subkey.match(line)
            if match:
                prefix = match.group(1) + '.' + match.group(2) + '.'
                continue

            k, v = _config_key_value(line, '=')
            k = prefix + k
            self._map[k.lower()] = k
            config[k] = v

        return config

    def _get(self, src, key, default):
        self.update()
        try:
            value = self._get_with_fallback(src, key)
        except KeyError:
            value = default
        return value

    def _get_with_fallback(self, src, key):
        try:
            return src[key]
        except KeyError:
            pass
        key = self._map.get(key.lower(), key)
        try:
            return src[key]
        except KeyError:
            pass
        # Allow the final KeyError to bubble up
        return src[key.lower()]

    def get(self, key, default=None):
        """Return the string value for a config key."""
        return self._get(self._all, key, default)

    def get_user(self, key, default=None):
        return self._get(self._user, key, default)

    def get_repo(self, key, default=None):
        return self._get(self._repo, key, default)

    def get_user_or_system(self, key, default=None):
        return self._get(self._user_or_system, key, default)

    def python_to_git(self, value):
        if type(value) is bool:
            if value:
                return 'true'
            else:
                return 'false'
        if type(value) is int:
            return ustr(value)
        return value

    def set_user(self, key, value):
        msg = self.message_user_config_changed
        self.git.config('--global', key, self.python_to_git(value))
        self.update()
        self.notify_observers(msg, key, value)

    def set_repo(self, key, value):
        msg = self.message_repo_config_changed
        self.git.config(key, self.python_to_git(value))
        self.update()
        self.notify_observers(msg, key, value)

    def find(self, pat):
        pat = pat.lower()
        match = fnmatch.fnmatch
        result = {}
        self.update()
        for key, val in self._all.items():
            if match(key.lower(), pat):
                result[key] = val
        return result

    def get_cached(self, key, default=None):
        cache = self._value_cache
        try:
            value = cache[key]
        except KeyError:
            value = cache[key] = self.get(key, default=default)
        return value

    def gui_encoding(self):
        return self.get_cached('gui.encoding', default='utf-8')

    def is_per_file_attrs_enabled(self):
        return self.get_cached('cola.fileattributes', default=False)

    def file_encoding(self, path):
        if not self.is_per_file_attrs_enabled():
            return self.gui_encoding()
        cache = self._attr_cache
        try:
            value = cache[path]
        except KeyError:
            value = cache[path] = (self._file_encoding(path) or
                                   self.gui_encoding())
        return value

    def _file_encoding(self, path):
        """Return the file encoding for a path"""
        status, out, err = self.git.check_attr('encoding', '--', path)
        if status != 0:
            return None
        header = '%s: encoding: ' % path
        if out.startswith(header):
            encoding = out[len(header):].strip()
            if (encoding != 'unspecified' and
                    encoding != 'unset' and
                    encoding != 'set'):
                return encoding
        return None

    def get_guitool_opts(self, name):
        """Return the guitool.<name> namespace as a dict

        The dict keys are simplified so that "guitool.$name.cmd" is accessible
        as `opts[cmd]`.

        """
        prefix = len('guitool.%s.' % name)
        guitools = self.find('guitool.%s.*' % name)
        return dict([(key[prefix:], value)
                        for (key, value) in guitools.items()])

    def get_guitool_names(self):
        guitools = self.find('guitool.*.cmd')
        prefix = len('guitool.')
        suffix = len('.cmd')
        return sorted([name[prefix:-suffix]
                        for (name, cmd) in guitools.items()])

    def get_guitool_names_and_shortcuts(self):
        """Return guitool names and their configured shortcut"""
        names = self.get_guitool_names()
        return [(name, self.get('guitool.%s.shortcut' % name)) for name in names]

    def terminal(self):
        term = self.get('cola.terminal', None)
        if not term:
            # find a suitable default terminal
            term = 'xterm -e' # for mac osx
            candidates = ('xfce4-terminal', 'konsole')
            for basename in candidates:
                if core.exists('/usr/bin/%s' % basename):
                    term = '%s -e' % basename
                    break
        return term

    def color(self, key, default):
        string = self.get('cola.color.%s' % key, default)
        string = core.encode(string)
        default = core.encode(default)
        struct_layout = core.encode('BBB')
        try:
            r, g, b = struct.unpack(struct_layout, unhexlify(string))
        except Exception:
            r, g, b = struct.unpack(struct_layout, unhexlify(default))
        return (r, g, b)
